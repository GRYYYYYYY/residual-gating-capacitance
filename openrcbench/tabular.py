from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

from .io import read_jsonl
from .masking import mask_indices
from .metrics import AGGREGATION_POLICY, grouped_regression_metrics, regression_metrics
from .schema import TARGET_NAMES
from .training import _base_features, _load_split, _target_scales


def fit_tabular_models(
    dataset: str | Path,
    split_path: str | Path,
    *,
    method: str,
    seed: int,
    fold: str | None = None,
) -> tuple:
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Tabular baselines require `pip install -e .[baseline]`") from exc

    split = _load_split(split_path, fold)
    ids = {name: set(value) for name, value in split.items()}
    tables = list(read_jsonl(dataset))
    train_tables = [table for table in tables if table.table_id in ids["train"]]
    scales = _target_scales(train_tables)
    models = []
    for target_index, (target, scale) in enumerate(zip(TARGET_NAMES, scales)):
        x_train = []
        y_train = []
        for table in train_tables:
            if not any(abs(row[target]) > 0 for row in table.rows):
                continue
            for row in table.rows:
                x_train.append(_base_features(table, row))
                y_train.append(math.log1p(row[target] / scale))
        if method == "xgboost":
            try:
                from xgboost import XGBRegressor
            except ImportError as exc:
                raise RuntimeError("XGBoost baseline requires the xgboost package") from exc
            model = XGBRegressor(
                n_estimators=500,
                max_depth=8,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                objective="reg:squarederror",
                random_state=seed,
                n_jobs=-1,
            )
        elif method == "mlp":
            try:
                from sklearn.neural_network import MLPRegressor
            except ImportError as exc:
                raise RuntimeError("MLP baseline requires scikit-learn") from exc
            model = MLPRegressor(
                hidden_layer_sizes=(128, 128),
                activation="relu",
                learning_rate_init=1e-3,
                max_iter=300,
                early_stopping=True,
                random_state=seed,
            )
        else:
            raise ValueError(f"Unknown tabular method {method}")
        model.fit(np.asarray(x_train, dtype=np.float32), np.asarray(y_train, dtype=np.float32))
        models.append(model)

    return models, scales


def evaluate_tabular_baseline(
    dataset: str | Path,
    split_path: str | Path,
    output: str | Path,
    *,
    method: str,
    protocol: str,
    ratio: float,
    seed: int,
    fold: str | None = None,
    fitted_models: tuple | None = None,
) -> dict:
    """Evaluate a fit from the same dataset, split, method, fold and seed."""
    import numpy as np

    models, scales = fitted_models if fitted_models is not None else fit_tabular_models(
        dataset, split_path, method=method, seed=seed, fold=fold
    )
    split = _load_split(split_path, fold)
    test_ids = set(split["test"])
    test_tables = [table for table in read_jsonl(dataset) if table.table_id in test_ids]

    grouped = defaultdict(lambda: {"truth": [], "prediction": []})
    records = []
    for table in test_tables:
        hidden = sorted(mask_indices(table, protocol, ratio, seed))
        features = np.asarray([_base_features(table, table.rows[i]) for i in hidden], dtype=np.float32)
        for target_index, (target, scale, model) in enumerate(zip(TARGET_NAMES, scales, models)):
            if not any(abs(row[target]) > 0 for row in table.rows):
                continue
            truth = [table.rows[i][target] for i in hidden]
            prediction = [max(0.0, math.expm1(float(x)) * scale) for x in model.predict(features)]
            metrics = regression_metrics(truth, prediction)
            records.append(
                {
                    "table_id": table.table_id,
                    "process_id": table.process_id,
                    "family": table.family,
                    "target": target,
                    "metrics": metrics,
                }
            )
            group = grouped[(table.process_id, target)]
            group["truth"].extend(truth)
            group["prediction"].extend(prediction)
    macro, zero_truth_groups = grouped_regression_metrics(grouped)
    payload = {
        "method": method,
        "protocol": protocol,
        "ratio": ratio,
        "seed": seed,
        "fold": fold,
        "macro_average": macro,
        "aggregation_policy": AGGREGATION_POLICY,
        "zero_truth_groups": zero_truth_groups,
        "records": records,
    }
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {key: value for key, value in payload.items() if key != "records"}
