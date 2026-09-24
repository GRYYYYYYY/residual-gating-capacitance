"""Unified residual-gated capacitance estimator (SACE-R).

New work lives here. The frozen ``pdkcap-v0`` workspace is imported strictly
read-only: bytecode writing is disabled before any import so no ``__pycache__``
is ever created inside the archived workspace.
"""
import sys

sys.dont_write_bytecode = True

__all__ = ['workspace', 'basis', 'model', 'episodes', 'train', 'predict', 'score', 'aggregate']
