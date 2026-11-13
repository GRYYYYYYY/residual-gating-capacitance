export DAC_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="$DAC_ROOT:/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/.venv-tabular/lib/python3.10/site-packages:/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/.venv-eda/lib/python3.10/site-packages"
export DAC_PYTHON=/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/.venv-eval/bin/python
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
cd "$DAC_ROOT"
