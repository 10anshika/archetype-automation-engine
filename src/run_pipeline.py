"""
run_pipeline.py - Archetype Engine Orchestrator (papermill edition)
===================================================================
Usage:
    python run_pipeline.py --channel EC
    python run_pipeline.py --channel TT
    python run_pipeline.py --channel EC --start-from 03
    python run_pipeline.py --channel EC --only 06
"""

import argparse
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import papermill as pm

# ── Configuration ──────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).parent.resolve()
NOTEBOOKS_DIR = SCRIPT_DIR.parent / "notebooks"
LOGS_DIR      = SCRIPT_DIR / "logs"

NOTEBOOKS = [
    ("01", "01_exploration (1).ipynb"),
    ("02", "02_asp_bucketing (1).ipynb"),
    ("03", "03_trend_pivot (1).ipynb"),
    ("04", "04_clustering (1).ipynb"),
    ("05", "05_archetype_keys (2).ipynb"),
    ("06", "06_validation (1) (1).ipynb"),
    ("07", "07_analytical_base_table (2) (2).ipynb"),
    ("08", "08_reporting.ipynb"),
]
KERNEL_NAME = "python3"
TIMEOUT     = 3600  # seconds per notebook


# ── Helpers ────────────────────────────────────────────────────────────────

def setup_logging(channel: str) -> Path:
    log_dir = LOGS_DIR / channel
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return log_dir / f"run_{ts}.log"


def log(message: str, log_file: Path, also_print: bool = True):
    ts   = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {message}"
    if also_print:
        print(line)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_notebook(nb_path: Path, channel: str, log_file: Path) -> bool:
    out_path = nb_path.with_name(nb_path.stem + "_executed.ipynb")
    log(f"  Running : {nb_path.name}", log_file)
    t0 = time.time()

    try:
        pm.execute_notebook(
            input_path            = str(nb_path),
            output_path           = str(out_path),
            kernel_name           = KERNEL_NAME,
            timeout               = TIMEOUT,
            environment_variables = {"CHANNEL": channel},
            cwd                   = str(nb_path.parent),
        )
        elapsed = time.time() - t0
        log(f"  OK Done in {elapsed:.0f}s", log_file)
        log(f"  Output  : {out_path.name}", log_file)
        return True

    except pm.PapermillExecutionError as e:
        elapsed = time.time() - t0
        log(f"  FAIL after {elapsed:.0f}s", log_file)
        log(f"    Cell {e.cell_index} - {e.ename}: {e.evalue}", log_file)
        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write(traceback.format_exc() + "\n")
        log(f"  Inspect : {out_path.name}  (outputs saved up to failing cell)", log_file)
        return False

    except Exception as e:
        elapsed = time.time() - t0
        log(f"  UNEXPECTED ERROR after {elapsed:.0f}s: {e}", log_file)
        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write(traceback.format_exc() + "\n")
        return False


# ── Main ───────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the Archetype Engine pipeline for a given channel."
    )
    parser.add_argument("--channel", required=True, choices=["EC", "TT", "MT"])
    parser.add_argument("--start-from", dest="start_from", default=None, metavar="NN")
    parser.add_argument("--only", default=None, metavar="NN")
    parser.add_argument("--notebooks-dir", dest="notebooks_dir", default=None)
    return parser.parse_args()


def main():
    args     = parse_args()
    channel  = args.channel
    nb_dir   = Path(args.notebooks_dir) if args.notebooks_dir else NOTEBOOKS_DIR
    log_file = setup_logging(channel)

    os.environ["CHANNEL"] = channel

    log("=" * 60, log_file)
    log(f"Archetype Engine  - channel : {channel}", log_file)
    log(f"Notebooks dir     : {nb_dir}", log_file)
    log(f"Log file          : {log_file}", log_file)
    log("=" * 60, log_file)

    to_run = list(NOTEBOOKS)

    if args.only:
        to_run = [(p, n) for p, n in NOTEBOOKS if p == args.only]
        if not to_run:
            print(f"ERROR: No notebook with prefix '{args.only}'.")
            sys.exit(1)

    elif args.start_from:
        prefixes = [p for p, _ in NOTEBOOKS]
        if args.start_from not in prefixes:
            print(f"ERROR: --start-from '{args.start_from}' not found.")
            sys.exit(1)
        idx    = prefixes.index(args.start_from)
        to_run = NOTEBOOKS[idx:]

    log(f"Notebooks to run  : {[n for _,n in to_run]}", log_file)
    log("", log_file)

    total_t0 = time.time()
    failed   = None

    for prefix, nb_name in to_run:
        nb_path = nb_dir / nb_name
        if not nb_path.exists():
            log(f"NOT FOUND: {nb_path}", log_file)
            log(f"  Files in notebooks dir:", log_file)
            for f in sorted(nb_dir.glob("*.ipynb")):
                log(f"    {f.name}", log_file)
            failed = nb_name
            break

        log(f"[{prefix}] {nb_name}", log_file)
        ok = run_notebook(nb_path, channel, log_file)

        if not ok:
            failed = nb_name
            break

        log("", log_file)

    total_elapsed = time.time() - total_t0
    log("=" * 60, log_file)

    if failed:
        log(f"PIPELINE FAILED at : {failed}", log_file)
        log(f"  Total elapsed      : {total_elapsed:.0f}s", log_file)
        log(f"  Full log           : {log_file}", log_file)
        sys.exit(1)
    else:
        log(f"PIPELINE COMPLETE  - channel: {channel}", log_file)
        log(f"  Total elapsed      : {total_elapsed:.0f}s", log_file)
        log(f"  Outputs in         : data/outputs/{channel}/", log_file)
        log("=" * 60, log_file)


if __name__ == "__main__":
    main()
