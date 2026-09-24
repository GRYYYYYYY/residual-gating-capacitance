from __future__ import annotations

try:
    import torch
    from torch import nn
except ImportError as exc:  # pragma: no cover - exercised by CLI error handling
    raise ImportError("Training requires `pip install -e .[train]`") from exc


class MaskedRCTransformer(nn.Module):
    def __init__(
        self,
        input_dim: int = 16,
        d_model: int = 128,
        nhead: int = 8,
        layers: int = 4,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.input = nn.Sequential(nn.Linear(input_dim, d_model), nn.GELU(), nn.LayerNorm(d_model))
        block = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=4 * d_model,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(block, num_layers=layers)
        self.output = nn.Sequential(
            nn.LayerNorm(d_model), nn.Linear(d_model, d_model), nn.GELU(), nn.Linear(d_model, 3)
        )

    def forward(self, features: "torch.Tensor", padding_mask: "torch.Tensor") -> "torch.Tensor":
        hidden = self.input(features)
        hidden = self.encoder(hidden, src_key_padding_mask=padding_mask)
        # Labels are log1p-transformed and therefore non-negative.
        return torch.nn.functional.softplus(self.output(hidden))

