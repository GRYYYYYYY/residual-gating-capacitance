"""Unified residual-gated capacitance estimator (SACE-R).

Bytecode writing is disabled so loading released artifacts does not create
cache files alongside read-only inputs.
"""
import sys

sys.dont_write_bytecode = True

__all__ = ['workspace', 'basis', 'model', 'episodes', 'train', 'predict', 'score', 'aggregate']
