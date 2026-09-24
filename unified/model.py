"""One network: a shared trunk whose residual head *and* its gate come from the
same hidden state.

The whole estimator is a single equation

    y_hat_k(x) = max(0, b_k(x) + sum_e pi_{e,k}(x) * Delta_{e,k}(x))
    pi_{.,k}(x) = softmax_e ( a_{e,k}(x) / tau )   restricted to applicable e
    a_{.,k}(x)  = g_theta(h_x, u_x) + beta        (beta learned, anchor-dominant)

`b` is the classical anchor, `Delta` the corrective basis (`basis.py`), `u` the
label-blind support features and `h` the transformer hidden state.  The three
frozen SACE policies are all special cases of the gate:

* SACE-Select  -- `pi` is the one-hot validation-frozen region/component map.
* SACE-Risk    -- `pi` is one-hot at the arg-min predicted log risk.
* SACE-Mix     -- `pi` is supported on the two lowest risks with the closed-form
                  weight r1/(r1+r2), i.e. a two-sparse softmax in log-risk space.
* gated expert -- the gated model's `sigma(MLP)` scale is the two-element convex
                  weight (anchor, learned residual) of this same gate.

Here the gate is not looked up or hard-wired: it is a trained head of the same
network that produces the learned correction, and it is trained end to end on
the deployment objective instead of a surrogate.
"""
import torch
from torch import nn

from .basis import ANCHOR


def inverse_softplus(target, floor=1e-3):
    """Parameter value whose ``softplus`` (plus floor) equals ``target``."""
    value = target - floor
    if value <= 0:
        raise ValueError('temperature must exceed the softplus floor')
    import math
    return math.log(math.expm1(value))


def make_prior(experts, anchor_logit_gap, neutral):
    """Initial gate bias.

    The anchor and the learned branches start neutral: the learned corrections
    are exactly zero at initialisation, so a large weight on them is harmless,
    and it keeps the residual branch inside the well-conditioned part of the
    softmax instead of behind a vanishing weight.  Only the frozen classical
    corrections, which are non-zero from the first step, start suppressed.
    """
    bias = torch.full((experts,), -float(anchor_logit_gap))
    bias[ANCHOR] = 0.
    for index in neutral:
        bias[index] = 0.
    return bias


class ResidualGateNet(nn.Module):
    version = 'sace-r-v1'

    def __init__(self, targets, features_in, gate_in, experts, width=64, layers=2,
                 gate_hidden=32, anchor_logit_gap=8., dropout=.1, neutral=None, agreement=True):
        if neutral is None:
            # The two learned corrections materialise last in the basis.
            neutral = (experts - 2, experts - 1)
        super().__init__()
        if min(targets, features_in, gate_in, experts, width, layers) < 1:
            raise ValueError('positive architecture sizes required')
        self.targets = targets
        self.experts = experts
        self.agreement = bool(agreement)
        self.anchor_logit_gap = float(anchor_logit_gap)
        self.input = nn.Linear(features_in, width)
        layer = nn.TransformerEncoderLayer(width, 4, dim_feedforward=width * 4,
                                           dropout=dropout, batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(layer, layers, enable_nested_tensor=False)
        self.residual = nn.Linear(width, targets)
        # `gate_in` counts the *stored* support features only; the agreement
        # block is derived from the basis inside the forward pass.
        self.gate = nn.Sequential(nn.Linear(width + gate_in + (3 * targets if self.agreement else 0),
                                            gate_hidden), nn.ReLU(),
                                  nn.Linear(gate_hidden, experts * targets))
        # Residual-branch initialisation: zero correction, anchor-dominant gate.
        nn.init.zeros_(self.residual.weight)
        nn.init.zeros_(self.residual.bias)
        nn.init.zeros_(self.gate[-1].weight)
        nn.init.zeros_(self.gate[-1].bias)
        self.gate_bias = nn.Parameter(make_prior(experts, anchor_logit_gap, neutral))
        self.log_temperature = nn.Parameter(torch.zeros(1))

    @property
    def temperature(self):
        return torch.nn.functional.softplus(self.log_temperature) + 1e-3

    def forward(self, features, baseline, gate_features, delta, valid, padding=None,
                clamp_lower=None, clamp_upper=None, inside=None, return_gate=False):
        """All tensors are batched and padded on the token axis.

        features       [B, T, F]   token features, material tokens appended
        baseline       [B, T, K]   anchor, zero on material tokens
        gate_features  [B, T, G]   support features, zero on material tokens
        delta          [B, T, Ec, K] classical corrections (NaN where invalid)
        valid          [B, T, Ec]    applicability
        padding        [B, T]        True on padding
        """
        hidden = self.encoder(self.input(features), src_key_padding_mask=padding)
        learned = self.residual(hidden)                                   # [B, T, K]
        clamped = learned
        if clamp_lower is not None:
            if clamp_lower.shape != baseline.shape or clamp_upper.shape != baseline.shape or inside.shape != baseline.shape[:2]:
                raise ValueError('clamp envelope shape mismatch')
            envelope = torch.clamp(baseline + learned, min=clamp_lower, max=clamp_upper)
            clamped = torch.where(inside.unsqueeze(-1), envelope - baseline, learned)
        built = torch.cat([delta, learned.unsqueeze(2), clamped.unsqueeze(2)], dim=2)
        if built.shape[2] != self.experts:
            raise ValueError(f'expected {self.experts} basis elements, received {built.shape[2]}')
        valid_full = torch.cat([valid, torch.ones_like(valid[:, :, :1]).expand(-1, -1, 2)], dim=2)
        corrections = torch.nan_to_num(built, nan=0., posinf=0., neginf=0.)
        inputs = [hidden, gate_features]
        if self.agreement:
            # How much the corrective basis disagrees at this point.  Large
            # spread means the local evidence is ambiguous: exactly the
            # quantity a validation-frozen region map cannot see.  The anchor
            # is applicable everywhere, so every slice has at least one term.
            weight = valid_full.unsqueeze(-1).to(corrections.dtype)
            count = weight.sum(dim=2).clamp(min=1.)
            center = (corrections * weight).sum(dim=2) / count
            variance = (((corrections - center.unsqueeze(2)) * weight) ** 2).sum(dim=2) / count
            floor = torch.full_like(corrections, -1e30)
            ceiling = torch.full_like(corrections, 1e30)
            span = (torch.where(weight > 0, corrections, floor).amax(dim=2)
                    - torch.where(weight > 0, corrections, ceiling).amin(dim=2))
            # sqrt is not differentiable at zero, and degenerate tokens (padding
            # and material rows) have exactly zero spread; the floor keeps the
            # backward pass finite without moving the value.
            stat = [center, torch.sqrt(variance + 1e-12), span]
            inputs.append(torch.cat([torch.sign(value) * torch.log1p(value.abs()) for value in stat], dim=-1))
        logits = self.gate(torch.cat(inputs, dim=-1)).reshape(
            *hidden.shape[:2], self.experts, self.targets)
        logits = logits + self.gate_bias.view(1, 1, self.experts, 1)
        logits = logits.masked_fill(~valid_full.unsqueeze(-1), -1e9)
        weights = torch.softmax(logits / self.temperature, dim=2)
        prediction = baseline + (weights * corrections).sum(dim=2)
        prediction = torch.clamp(prediction, min=0.)
        if return_gate:
            return prediction, dict(weights=weights, logits=logits, residual=learned,
                                    clamped=clamped, valid=valid_full)
        return prediction


class SelectGate(ResidualGateNet):
    """The unified network with its gate frozen to a hard segment/component map.

    Everything else is identical to the trained network: same trunk, same
    corrective basis, same residual head, same assembly rule.  Only the gate is
    replaced by a lookup, which is what makes the frozen SACE-Select policy a
    member of the same estimator family.  With a large enough logit gap the
    softmax is exactly one-hot, so the assembled estimate reduces on the nose to
    "read the mapped expert's prediction, fall back to the anchor where that
    expert is inapplicable".
    """

    def __init__(self, selected, *args, logit_gap=60., **kwargs):
        super().__init__(*args, **kwargs)
        import numpy as np
        mapped = np.asarray(selected, int)
        if mapped.ndim != 2 or mapped.shape[1] != self.targets:
            raise ValueError('mapped expert table must be [regions, targets]')
        if (mapped < 0).any() or (mapped >= self.experts).any():
            raise ValueError('mapped expert index out of range')
        self.logit_gap = float(logit_gap)
        # Not persistent: the table is supplied, never learned, so it must not
        # enter the state dict the checkpoints were saved with.
        self.register_buffer('mapped', torch.as_tensor(mapped, dtype=torch.long), persistent=False)

    def forward(self, features, baseline, gate_features, delta, valid, padding=None,
                clamp_lower=None, clamp_upper=None, inside=None, return_gate=False):
        if clamp_lower is None:
            raise ValueError('clamp envelope required')
        from .basis import ANCHOR, segment_slice
        hidden = self.encoder(self.input(features), src_key_padding_mask=padding)
        learned = self.residual(hidden)
        envelope = torch.clamp(baseline + learned, min=clamp_lower, max=clamp_upper)
        clamped = torch.where(inside.unsqueeze(-1), envelope - baseline, learned)
        built = torch.cat([delta, learned.unsqueeze(2), clamped.unsqueeze(2)], dim=2)
        if built.shape[2] != self.experts:
            raise ValueError('correction basis does not match the gate table')
        valid_full = torch.cat([valid, torch.ones_like(valid[:, :, :1]).expand(-1, -1, 2)], dim=2)
        corrections = torch.nan_to_num(built, nan=0., posinf=0., neginf=0.)
        region = torch.argmax(gate_features[:, :, segment_slice(self.targets)], dim=-1)
        mapped = self.mapped[region]
        applicable = torch.gather(valid_full, 2, mapped)
        chosen = torch.where(applicable, mapped, torch.full_like(mapped, ANCHOR))
        logits = torch.full((*hidden.shape[:2], self.experts, self.targets), -self.logit_gap,
                            dtype=hidden.dtype)
        logits.scatter_(2, chosen.unsqueeze(2), self.logit_gap)
        weights = torch.softmax(logits, dim=2)
        prediction = torch.clamp(baseline + (weights * corrections).sum(dim=2), min=0.)
        if return_gate:
            return prediction, dict(weights=weights, valid=valid_full)
        return prediction
