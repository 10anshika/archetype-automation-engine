"""
run_diagnostic.py - Cross-channel threshold diagnostic runner
=============================================================
Runs NB09 (09_threshold_diagnostic.ipynb) across all channels.
Unlike run_pipeline.py, this notebook is NOT channel-specific:
it loads outputs from EC, TT, and MT simultaneously.

Usage:
    python run_diagnostic.py
"""

import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import papermill as pm

SCRIPT_DIR    = Path(__file__).parent.resolve()
NOTEBOOKS_DIR = SCRIPT_DIR.parent / "notebooks"
LOGS_DIR      = SCRIPT_DIR / "logs"
KERNEL_NAME   = "python3"
TIMEOUT       = 1800
NB_NAME       = "09_threshold_diagnostic.ipynb"


def main():
    nb_path  = NOTEBOOKS_DIR / NB_NAME
    out_path = NOTEBOOKS_DIR / "09_threshold_diagnostic_executed.ipynb"
    log_dir  = LOGS_DIR / "diagnostic"
    log_dir.mkdir(parents=True, exist_ok=True)
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"diag_{ts}.log"

    def log(msg):
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        print(line)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    log("=" * 65)
    log("Archetype Engine - Threshold Diagnostic (NB09)")
    log(f"Notebook : {nb_path}")
    log(f"Output   : {out_path}")
    log(f"Log      : {log_file}")
    log("=" * 65)

    if not nb_path.exists():
        log(f"ERROR: {nb_path} not found.")
        sys.exit(1)

    t0 = time.time()
    try:
        pm.execute_notebook(
            input_path  = str(nb_path),
            output_path = str(out_path),
            kernel_name = KERNEL_NAME,
            timeout     = TIMEOUT,
            cwd         = str(NOTEBOOKS_DIR),
        )
        elapsed = time.time() - t0
        log(f"DONE in {elapsed:.0f}s")
        log(f"Outputs: data/outputs/09_threshold_diagnostic*.csv")
        log(f"Charts:  data/outputs/09_threshold_diagnostic_charts/")
        log(f"Executed notebook: {out_path.name}")

    except pm.PapermillExecutionError as e:
        elapsed = time.time() - t0
        log(f"FAILED after {elapsed:.0f}s")
        log(f"  Cell {e.cell_index} - {e.ename}: {e.evalue}")
        log(f"  Inspect: {out_path.name}")
        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write(traceback.format_exc() + "\n")
        sys.exit(1)

    except Exception as e:
        elapsed = time.time() - t0
        log(f"UNEXPECTED ERROR after {elapsed:.0f}s: {e}")
        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write(traceback.format_exc() + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()