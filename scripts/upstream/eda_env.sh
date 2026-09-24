# Source from Bash before invoking the pinned ORFS runner.
eda_project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export OPENROAD_EXE="$eda_project_root/tools/openroad-install-20260909/bin/openroad"
export OPENSTA_EXE="$eda_project_root/tools/openroad-install-20260909/bin/sta"
export YOSYS_EXE="$eda_project_root/tools/yosys-install-20260909/bin/yosys"
export PYTHON_EXE="$eda_project_root/.venv-eda/bin/python"
export PATH="$eda_project_root/tools/openroad-deps-20260908/bin:$eda_project_root/tools/openroad-install-20260909/bin:$eda_project_root/tools/yosys-install-20260909/bin:$PATH"
export LD_LIBRARY_PATH="$eda_project_root/tools/openroad-deps-20260908/lib64:$eda_project_root/tools/openroad-deps-20260908/lib:${LD_LIBRARY_PATH:-}"
export NUM_CORES=16
export QT_QPA_PLATFORM=offscreen
unset eda_project_root
