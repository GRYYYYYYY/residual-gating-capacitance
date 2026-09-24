"""Inference adapter for frozen OOF risk checkpoints and lazy expert execution."""
import numpy as np
import torch
from .common import file_hash
from .round3_router import RiskRouter, infer


class RoutedPredictor:
    def __init__(self, experts, checkpoints, checkpoint_hashes, mixture=False):
        if not checkpoints:
            raise ValueError('no router checkpoints')
        self.experts = experts
        self.mixture = mixture
        self.models = []
        self.names = None
        self.targets = None
        for path in checkpoints:
            if file_hash(path) != checkpoint_hashes[str(path)]:
                raise ValueError('router checkpoint drift')
            state = torch.load(path, map_location='cpu', weights_only=True)
            if state['version'] != 'round3-risk-router-v1':
                raise ValueError('unknown router version')
            names = tuple(state['expert_names'])
            if self.names is not None and (names != self.names or state['targets'] != self.targets):
                raise ValueError('unaligned router ensemble')
            self.names, self.targets = names, state['targets']
            mean, scale = np.asarray(state['mean']), np.asarray(state['scale'])
            if mean.shape != (state['features'],) or scale.shape != mean.shape:
                raise ValueError('invalid feature normalization shape')
            if not np.isfinite(mean).all() or not np.isfinite(scale).all() or (scale <= 0).any():
                raise ValueError('invalid feature normalization')
            if len(names) != state['experts'] or len(set(names)) != len(names):
                raise ValueError('invalid expert names')
            model = RiskRouter(state['features'], state['experts'], state['targets'])
            model.load_state_dict(state['state_dict'])
            model.eval()
            self.models.append((model, mean, scale))

    def risks(self, prepared):
        # This is exactly the OOF builder's feature layout, with no query labels.
        features = np.c_[prepared['support']['features'], prepared['features'][:prepared['n'], 3:14]]
        return self.risks_from_features(features)

    def risks_from_features(self, features):
        """Reuse frozen validation features without running expert inference again."""
        features = np.asarray(features, float)
        if features.ndim != 2:
            raise ValueError('query by feature matrix required')
        if not np.isfinite(features).all():
            raise ValueError('nonfinite routing features')
        predictions = []
        with torch.inference_mode():
            for model, mean, scale in self.models:
                if features.shape[1] != len(mean):
                    raise ValueError('router feature layout mismatch')
                normalized = torch.as_tensor((features - mean) / scale, dtype=torch.float32)
                log_risk = model(normalized).numpy()
                if not np.isfinite(log_risk).all():
                    raise ValueError('nonfinite predicted log risk')
                predictions.append(np.exp(np.clip(log_risk.astype(float), -30, 30)))
        # Aggregate predicted risks, not the outputs of every expensive expert.
        return np.mean(predictions, axis=0)

    def predict(self, table, observed, values, diagnostics=False):
        if np.asarray(values).ndim != 2 or np.asarray(values).shape[1] != self.targets:
            raise ValueError('router target dimension mismatch')
        prepared = self.experts.support(table, observed, values)
        return infer(self.experts, table, observed, values, self.risks(prepared), self.names,
            mixture=self.mixture, diagnostics=diagnostics)
