"""The residual-gating estimator: one network that reads a sparsely
characterized table and answers a query.

The whole model is one equation,

    y_hat_k(x) = max(0, b_k(x) + sum_e pi_{e,k}(x) * Delta_{e,k}(x))

    pi_{.,k}(x) = softmax_e ( ( <q_k(x), k_{e,k}(x)> / sqrt(d) + beta_e ) / tau(x) )

where

* ``b`` is the table's own multilinear anchor -- the skip path, whose correction
  is identically zero;
* ``{f_e}`` is a fixed dictionary of corrections, and ``Delta_e = f_e - b``;
* ``q_k(x)`` is a query vector produced from the trunk hidden state and the
  label-blind support geometry, one head per capacitance component;
* ``k_{e,k}(x)`` is a key produced from *that dictionary element's own
  proposal*: the correction it is asking for, how far that sits from the
  consensus of the other applicable elements (including a leave-one-out reading
  and an envelope-violation reading), and whether it applies at all;
* ``tau(x)`` is a temperature the network predicts from the same state, so the
  gate may be nearly hard where the dictionary agrees and stay soft where the
  evidence is ambiguous;
* ``beta_e`` is a per-element prior that starts the fixed classical corrections
  behind a negative logit gap.

The gate is attention over the correction dictionary: the query is the state of
the query point, the keys are what each candidate correction is proposing there,
and the attention weights are the mixture.  A query where the dictionary
disagrees with itself is exactly a query whose support is ambiguous, and the
leave-one-out and envelope channels are what let the gate identify *which*
element is the outlier rather than only that an outlier exists.
"""
import math

import torch
from torch import nn

from .basis import ANCHOR

#: descriptor channels: own proposal (signed-log), own proposal (linear,
#: clipped), consensus deviation, leave-one-out deviation, envelope violation,
#: applicability.
CHANNELS = 6


def inverse_softplus(target, floor=1e-3):
    """Parameter value whose ``softplus`` (plus floor) equals ``target``."""
    value = target - floor
    if value <= 0:
        raise ValueError('temperature must exceed the softplus floor')
    return math.log(math.expm1(value))


def make_prior(experts, anchor_logit_gap, neutral):
    """Initial per-element prior.

    The anchor and the learned corrections start neutral; the fixed classical
    corrections start behind a negative gap, because they are nonzero from the
    first step and an unearned weight on them would swamp the residual branch
    before it has fitted anything.
    """
    bias = torch.full((experts,), -float(anchor_logit_gap))
    bias[ANCHOR] = 0.
    for index in neutral:
        bias[index] = 0.
    return bias


def dictionary_descriptors(corrections, valid, baseline, lower=None, upper=None, inside=None):
    """``[B, T, E, K, CHANNELS]``: what the gate may know about each element.

    ``corrections`` holds ``Delta_e`` (zero where inapplicable) and ``valid``
    says where each element is defined.  The channels are

    1. the element's own correction, signed-log compressed,
    2. the same correction linearly (clipped), so the gate can compare
       magnitudes rather than only orders of magnitude,
    3. its deviation from the applicability-weighted consensus of the
       dictionary, in units of the dictionary spread,
    4. the same deviation computed leave-one-out, so that a lone outlier is not
       shrunk towards itself,
    5. how far the element's *value* leaves the envelope the observed support
       permits at this query -- inside the hull that is the envelope of the
       bracketing observations, beyond it the envelope degenerates to the
       nearest observation, and in both cases an element whose prediction
       leaves it is contradicting the table,
    6. an applicability flag.
    """
    weight = valid.unsqueeze(-1).to(corrections.dtype)
    total = weight.sum(dim=2, keepdim=True)
    weighted = corrections * weight
    center = weighted.sum(dim=2, keepdim=True) / total.clamp(min=1.)
    spread = torch.sqrt((((corrections - center) * weight) ** 2).sum(dim=2, keepdim=True)
                        / total.clamp(min=1.) + 1e-12)
    z = (corrections - center) / (spread + 1e-6)
    other = (total - weight).clamp(min=1.)
    loo_center = (weighted.sum(dim=2, keepdim=True) - weighted) / other
    loo_sq = ((((corrections - loo_center) * weight) ** 2).sum(dim=2, keepdim=True)
              - ((corrections - loo_center) * weight) ** 2)
    loo_spread = torch.sqrt(loo_sq.clamp(min=0.) / other + 1e-12)
    loo_z = (corrections - loo_center) / (loo_spread + 1e-6)

    value = baseline.unsqueeze(2) + corrections
    if lower is None:
        violation = torch.zeros_like(corrections)
    else:
        width = (upper - lower).clamp(min=1e-6)
        outside = (torch.relu(value - upper.unsqueeze(2)) + torch.relu(lower.unsqueeze(2) - value))
        violation = outside / width.unsqueeze(2)
    scaled = torch.sign(corrections) * torch.log1p(corrections.abs())
    channels = [scaled, corrections.clamp(-8., 8.), z, loo_z,
                torch.sign(violation) * torch.log1p(violation.abs()),
                valid.unsqueeze(-1).to(corrections.dtype).expand_as(corrections)]
    return torch.stack(channels, dim=-1)


#: The first generation of this gate used a narrower, inside-gated envelope
#: channel.  Checkpoints from it are still scoreable: the descriptor block is
#: reduced back to that layout instead of being re-described.
LEGACY_CHANNELS = 5


def restrict_descriptors(descriptor, valid, inside, channels):
    """Reduce the six descriptors to an older, narrower layout.

    Dropping the linear magnitude channel and confining the envelope violation
    to queries inside the hull reproduces the five-channel block that the first
    generation of this gate was trained with.
    """
    if channels != LEGACY_CHANNELS:
        raise ValueError(f'no descriptor reduction defined for {channels} channels')
    scaled, _, z, loo_z, violation, applicable = descriptor.unbind(dim=-1)
    if inside is not None:
        violation = violation * inside.unsqueeze(-1).unsqueeze(-1).to(violation.dtype)
    return torch.stack([scaled, z, loo_z, violation, applicable], dim=-1)


class ResidualGatingEstimator(nn.Module):
    """Trunk, residual head and dictionary-attention gate in one module."""

    version = 'rg-a4'

    def __init__(self, targets, features_in, gate_in, experts, width=64, layers=2,
                 gate_hidden=32, head_dim=16, anchor_logit_gap=8., dropout=.1,
                 neutral=None, agreement=True, gate_init=.01, temperature=1.,
                 channels=CHANNELS):
        if neutral is None:
            neutral = (experts - 2, experts - 1)      # the learned corrections
        super().__init__()
        if min(targets, features_in, gate_in, experts, width, layers, head_dim) < 1:
            raise ValueError('positive architecture sizes required')
        self.targets = targets
        self.experts = experts
        self.agreement = bool(agreement)
        self.head_dim = int(head_dim)
        self.anchor_logit_gap = float(anchor_logit_gap)
        self.input = nn.Linear(features_in, width)
        layer = nn.TransformerEncoderLayer(width, 4, dim_feedforward=width * 4,
                                           dropout=dropout, batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(layer, layers, enable_nested_tensor=False)
        self.residual = nn.Linear(width, targets)
        state_in = width + gate_in + (3 * targets if self.agreement else 0)
        self.query = nn.Sequential(nn.Linear(state_in, gate_hidden), nn.ReLU(),
                                   nn.Linear(gate_hidden, targets * self.head_dim))
        if channels < 1:
            raise ValueError('positive descriptor width required')
        self.channels = int(channels)
        self.key = nn.Linear(self.channels, self.head_dim)
        self.key_element = nn.Parameter(torch.zeros(experts, self.head_dim))
        self.key_target = nn.Parameter(torch.zeros(targets, self.head_dim))
        self.temperature_head = nn.Sequential(nn.Linear(state_in, gate_hidden), nn.ReLU(),
                                              nn.Linear(gate_hidden, 1))
        # The learned corrections are exactly zero at initialisation, so the
        # trunk starts as a pure anchor and has to earn every deviation.
        nn.init.zeros_(self.residual.weight)
        nn.init.zeros_(self.residual.bias)
        # Small but non-zero: the prior still dominates at step zero (it is a
        # logit gap of several units), while the query and key paths both
        # receive gradient from the first update.
        nn.init.normal_(self.query[-1].weight, std=gate_init)
        nn.init.zeros_(self.query[-1].bias)
        nn.init.zeros_(self.key.weight)
        nn.init.zeros_(self.key.bias)
        nn.init.zeros_(self.temperature_head[-1].weight)
        nn.init.zeros_(self.temperature_head[-1].bias)
        self.gate_bias = nn.Parameter(make_prior(experts, anchor_logit_gap, neutral))
        self.log_temperature = nn.Parameter(torch.full((1,), inverse_softplus(temperature)))

    @property
    def temperature(self):
        return torch.nn.functional.softplus(self.log_temperature) + 1e-3

    def forward(self, features, baseline, gate_features, delta, valid, padding=None,
                clamp_lower=None, clamp_upper=None, inside=None, return_gate=False):
        """All tensors are batched and padded on the token axis.

        features       [B, T, F]     token features, material tokens appended
        baseline       [B, T, K]     anchor, zero on material tokens
        gate_features  [B, T, G]     support geometry, zero on material tokens
        delta          [B, T, Ec, K] classical corrections, NaN where inapplicable
        valid          [B, T, Ec]    applicability
        padding        [B, T]        True on padding
        """
        hidden = self.encoder(self.input(features), src_key_padding_mask=padding)
        learned = self.residual(hidden)
        clamped = learned
        if clamp_lower is not None:
            if clamp_lower.shape != baseline.shape or clamp_upper.shape != baseline.shape \
                    or inside.shape != baseline.shape[:2]:
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
            weight = valid_full.unsqueeze(-1).to(corrections.dtype)
            count = weight.sum(dim=2).clamp(min=1.)
            center = (corrections * weight).sum(dim=2) / count
            variance = (((corrections - center.unsqueeze(2)) * weight) ** 2).sum(dim=2) / count
            floor = torch.full_like(corrections, -1e30)
            ceiling = torch.full_like(corrections, 1e30)
            span = (torch.where(weight > 0, corrections, floor).amax(dim=2)
                    - torch.where(weight > 0, corrections, ceiling).amin(dim=2))
            stat = [center, torch.sqrt(variance + 1e-12), span]
            inputs.append(torch.cat([torch.sign(value) * torch.log1p(value.abs())
                                     for value in stat], dim=-1))
        state = torch.cat(inputs, dim=-1)

        query = self.query(state).reshape(*hidden.shape[:2], self.targets, self.head_dim)
        descriptor = dictionary_descriptors(corrections, valid_full, baseline,
                                            clamp_lower, clamp_upper, inside)
        if self.channels != descriptor.shape[-1]:
            descriptor = restrict_descriptors(descriptor, valid_full, inside, self.channels)
        key = (self.key(descriptor)
               + self.key_element.view(1, 1, self.experts, 1, self.head_dim)
               + self.key_target.view(1, 1, 1, self.targets, self.head_dim))
        logits = (query.unsqueeze(2) * key).sum(dim=-1) / math.sqrt(self.head_dim)
        logits = logits + self.gate_bias.view(1, 1, self.experts, 1)
        logits = logits.masked_fill(~valid_full.unsqueeze(-1), -1e9)
        temperature = self.temperature * torch.exp(
            torch.clamp(self.temperature_head(state), -3., 3.))
        weights = torch.softmax(logits / temperature.unsqueeze(-1), dim=2)
        prediction = torch.clamp(baseline + (weights * corrections).sum(dim=2), min=0.)
        if return_gate:
            return prediction, dict(weights=weights, logits=logits, residual=learned,
                                    clamped=clamped, valid=valid_full, temperature=temperature)
        return prediction
