"""Explicit five-percent per-cell acceptance; empty evidence is not success."""
import numpy as np


def compare_cell(truth, candidate, reference, training_scale, relative_limit=.05, absolute_floor=1e-4):
    truth,candidate,reference=(np.asarray(v,float) for v in (truth,candidate,reference))
    if truth.shape!=candidate.shape or truth.shape!=reference.shape or truth.ndim!=1:
        raise ValueError('one aligned component per acceptance cell required')
    if not all(np.isfinite(v).all() for v in (truth,candidate,reference)):
        raise ValueError('nonfinite acceptance data')
    if training_scale<=0 or not np.isfinite(training_scale):raise ValueError('training-only positive scale required')
    if not len(truth):return dict(passed=None,status='no_evidence',n=0)
    c=float(np.sqrt(np.mean((candidate-truth)**2)))
    r=float(np.sqrt(np.mean((reference-truth)**2)))
    truth_rms=float(np.sqrt(np.mean(truth**2)))
    near_zero=r/training_scale<=absolute_floor
    allowed=r+absolute_floor*training_scale if near_zero else r*(1+relative_limit)
    return dict(passed=c<=allowed,status='passed' if c<=allowed else 'failed',n=len(truth),
        candidate_rmse=c,reference_rmse=r,training_scale=training_scale,allowed_rmse=allowed,
        candidate_nrmse=c/truth_rms if truth_rms>0 else None,
        reference_nrmse=r/truth_rms if truth_rms>0 else None,
        relative_regression=(c-r)/r if r>0 else None,
        near_zero_reference=near_zero,gate='training-scale absolute delta' if near_zero else 'relative RMSE/NRMSE',
        interpretation='point-estimate gate on this cell, not a population guarantee')


def complete_acceptance(cells, expected_cells):
    """Caller supplies the predeclared population, not only favorable present rows."""
    if set(cells)!=set(expected_cells):
        return dict(passed=False,status='incomplete',missing=sorted(set(expected_cells)-set(cells)),unexpected=sorted(set(cells)-set(expected_cells)))
    failures=[key for key,value in cells.items() if value['passed'] is False]
    unavailable=[key for key,value in cells.items() if value['passed'] is None]
    return dict(passed=not failures and not unavailable and bool(cells),
        status='failed' if failures else 'incomplete' if unavailable or not cells else 'passed',
        failures=failures,no_evidence=unavailable)
