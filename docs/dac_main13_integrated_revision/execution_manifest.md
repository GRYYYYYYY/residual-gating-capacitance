# Execution manifest

Task: first integrated main13 revision, not a continuation patch.
Repository/workspace: `/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/workspaces/test-v1/opensource_release/dac-capacitance-20261114`.
Branch: `revision/dac-cap-main13-integrated`.
Starting HEAD: `b97f90b7d2acd2f06dd7dd9a5f8032001faea422`.
Original PDF SHA256: `20b073e049a403093e4a3c89f61f1c1f7fa6d51dee2566da91de3064aa1422e7` (exact supplied main13 match).
Original TeX SHA256: `cd4bdfbf813c56bf4006ba2a1de2024e111108ef73a9b199f41b47e98d4b23e1`.
Read-only snapshot: `/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/workspaces/test-v1/opensource_release/dac-main13-snapshot-20261117T131318Z`. The original dirty status, binary diff,
current paper, experiment/config sources, archived results and 27 frozen
Full/Binary/Ungated checkpoints are preserved there. The original result and
model paths remain read-only inputs; new outputs have experiment ID main13_20261117.

Single formal paper: `/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/workspaces/test-v1/opensource_release/dac-capacitance-20261114/paper/dac_layout_query_revision/main.tex` and `main.pdf`.
No SOURCE_OF_TRUTH.md existed in this paper directory. Parent project instructions
were inspected; this user's explicit workspace and paper scope supersede historical
handoff suggestions to use other projects. No FPGA migration or Vivado action was
performed. No remote push or unrelated process termination is authorized or used.

Python: /inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/.venv-eval/bin/python,
with existing env.sh dependency paths; NumPy/SciPy/PyTorch versions are recorded in
the runtime environment receipt. OpenROAD original pinned source is 0b54bb3203;
existing release/trace compute-table binaries are reused, not rebuilt or modified.
No new GPU allocation. Three single-thread bounded training workers plus one
native worker; 300s native and 10800s per-member training timeouts; no automatic
performance-based retries. Existing unrelated CPU and Vivado jobs are untouched.

Current model/session remains the originating Codex reasoning session. The
long-run-supervision skill was read; no authorized interface to switch this
session to luna was exposed. Existing exec handles supervise the actual queue.
All performance and completion decisions require artifact verification.
