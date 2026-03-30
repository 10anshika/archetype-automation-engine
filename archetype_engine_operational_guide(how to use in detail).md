# Archetype Engine — Operational Guide

> **Who this is for:** Any technical user running, updating, or extending the Archetype Engine pipeline. No prior project exposure assumed.

---

## Table of Contents

1. [System Usage Overview](#1-system-usage-overview)
2. [Environment Setup](#2-environment-setup)
3. [Running the Existing Pipeline](#3-running-the-existing-pipeline)
4. [Input Data Requirements](#4-input-data-requirements)
5. [Using a New Dataset (Same Channel Structure)](#5-using-a-new-dataset-same-channel-structure)
6. [Adding a New Channel (Different Structure)](#6-adding-a-new-channel-different-structure)
7. [Threshold Tuning Guide](#7-threshold-tuning-guide)
8. [Output Interpretation](#8-output-interpretation)
9. [Debugging and Recovery](#9-debugging-and-recovery)
10. [Safe Modification Guidelines](#10-safe-modification-guidelines)
11. [Operational Checklists](#11-operational-checklists)
12. [Example Walkthroughs](#12-example-walkthroughs)

---

## 1. System Usage Overview

### What This Engine Expects as Input

The Archetype Engine reads raw sales Excel files. Each file must contain monthly aggregated sales data with at minimum these fields: a product division, a sales portal, a product size, a price range identifier, year, month, quantity sold, and net sales revenue.

Three channels are currently supported out of the box:

| Channel | File | Sheet |
|---------|------|-------|
| EC (E-Commerce) | `data/raw/ec_data.xlsx` | `Sheet1` |
| TT (Traditional Trade) | `data/raw/manual_validation.xlsx` | `raw` |
| MT (Modern Trade) | `data/raw/mt_data.xlsx` | `raw` |

Each channel has its own output folder and configuration. They are independent — running EC does not affect TT or MT outputs.

### What It Produces as Output

After a full pipeline run for one channel, you get the following under `notebooks/data/outputs/{CHANNEL}/`:

```
notebooks/data/outputs/EC/
├── 01_clean_sales.csv                  ← Cleaned, filtered raw data
├── 02_fine_bucket_ts.csv               ← Monthly sales per price bucket per segment
├── 03_segment_pivots.pkl               ← Trend matrices (binary, needed by NB04+)
├── archetype_mapping.csv               ← Every price bucket mapped to a New Bucket
├── archetype_keys.csv                  ← One row per archetype (price range, volume)
├── 06_validation_summary.csv           ← Per-segment accuracy vs ground truth
├── 06_validation_detail.csv            ← Row-level accuracy detail
├── 07_analytical_base_table.csv        ← All transactions enriched with archetype labels
├── 07_archetype_monthly.csv            ← Monthly rollup by archetype
├── per_portal/                         ← One file set per Division_Portal_Size
│   ├── HL_Amazon_LARGE_summary.csv
│   ├── HL_Amazon_LARGE_pivot_ready.xlsx
│   └── ... (summary, detail, trend_pivot, pivot_ready, PNG per segment)
└── consolidated/                       ← One file set per Division_Size (all portals merged)
    ├── HL_LARGE_pivot_ready.xlsx
    └── ...
```

Additionally:
- `notebooks/data/outputs/09_threshold_diagnostic.csv` — diagnostic output (after running NB09)
- `notebooks/data/outputs/10_pivot_detail/` — detailed pivot Excel files (after running NB10)
- `src/logs/{CHANNEL}/run_{YYYYMMDD_HHMMSS}.log` — execution log per run

### High-Level Flow of Execution

```
Raw Excel
  │
  NB01  →  Clean + filter rows, build sale_date, save 01_clean_sales.csv
  │
  NB02  →  Compute smoothed ASP, assign ₹100 buckets, save 02_fine_bucket_ts.csv
  │
  NB03  →  Build monthly % share pivot per segment, save 03_segment_pivots.pkl
  │
  NB04  →  Auto-K clustering: group similar adjacent buckets → archetype_mapping + keys
  │
  NB05  →  Verify archetype key format and completeness
  │
  NB06  →  Validate against ground truth Excel, report accuracy
  │
  NB07  →  Join archetypes back to all transactions → analytical base table
  │
  NB08  →  Generate analyst-ready Excel pivot files and PNGs
  │
  [NB09]  →  Threshold sensitivity diagnostic (run separately, cross-channel)
  [NB10]  →  Deep-dive pivot detail for flagged segments (run separately)
```

---

## 2. Environment Setup

### Python Version

The project was built and tested on **Python 3.14.3**. Python 3.10+ will work. Python 3.8 or lower is not supported (uses f-strings and `|=` dict syntax in places).

### Required Libraries

```
pandas
numpy
scipy
scikit-learn
matplotlib
seaborn
papermill
openpyxl
jupyter
nbconvert
pickle (standard library — no install needed)
```

### Installation Steps

```bash
# Option A — install into system Python (use this flag on Python 3.12+)
pip install pandas numpy scipy scikit-learn matplotlib seaborn papermill openpyxl jupyter nbconvert --break-system-packages

# Option B — virtual environment (recommended if managing multiple projects)
python -m venv .venv
source .venv/bin/activate           # Linux/Mac
# OR
.venv\Scripts\activate              # Windows PowerShell

pip install pandas numpy scipy scikit-learn matplotlib seaborn papermill openpyxl jupyter nbconvert
```

### Verify the Jupyter kernel is registered

papermill executes notebooks using a named kernel (`python3`). Confirm it exists:

```bash
jupyter kernelspec list
```

You should see `python3` in the list. If not, register it:

```bash
python -m ipykernel install --user --name python3 --display-name "Python 3"
```

### Required Folder Structure

The project must have this layout **before running anything**. If folders are missing, create them manually — the pipeline will create output subfolders itself, but it needs the source files in place.

```
archetype_engine - Copy_2 - Copy/       ← project root
├── data/
│   └── raw/
│       ├── ec_data.xlsx                 ← EC raw data (REQUIRED for EC runs)
│       ├── manual_validation.xlsx       ← TT raw data (REQUIRED for TT runs)
│       └── mt_data.xlsx                 ← MT raw data (REQUIRED for MT runs)
├── notebooks/
│   ├── 01_exploration (1).ipynb
│   ├── 02_asp_bucketing (1).ipynb
│   ├── 03_trend_pivot (1).ipynb
│   ├── 04_clustering (1).ipynb
│   ├── 05_archetype_keys (2).ipynb
│   ├── 06_validation (1) (1).ipynb
│   ├── 07_analytical_base_table (2) (2).ipynb
│   ├── 08_reporting.ipynb
│   ├── 09_threshold_diagnostic.ipynb
│   └── 10_pivot_detail.ipynb
└── src/
    ├── channel_registry.py
    ├── config.py
    ├── pipeline.py
    ├── clustering.py
    ├── run_pipeline.py
    ├── run_diagnostic.py
    ├── write_nb09.py
    └── write_nb10_pivot_detail.py
```

> **Critical path note:** Notebooks resolve file paths relative to the `notebooks/` directory as their working directory. `data/outputs/EC/` therefore means `notebooks/data/outputs/EC/`, not `project_root/data/outputs/EC/`. Raw Excel files are resolved one level up: `../data/raw/` = `project_root/data/raw/`. Do not move notebooks or src files — this resolution breaks if you do.

---

## 3. Running the Existing Pipeline

### Step 1 — Navigate to the `src/` directory

All pipeline commands must be run from inside the `src/` folder. If you run from elsewhere, papermill will not find the notebooks.

```bash
cd "D:\archetype_engine - Copy_2 - Copy\src"     # Windows
# OR
cd "/path/to/archetype_engine - Copy_2 - Copy/src"  # Linux/Mac
```

### Step 2 — Confirm raw data is in place

Before running any channel, verify the file exists:

```bash
# Check all three source files exist
ls ../data/raw/
# Expected output: ec_data.xlsx  manual_validation.xlsx  mt_data.xlsx
```

### Step 3 — Run a channel

```bash
# Run the full EC pipeline (all 8 notebooks, NB01 through NB08)
python run_pipeline.py --channel EC

# Run the full TT pipeline
python run_pipeline.py --channel TT

# Run the full MT pipeline
python run_pipeline.py --channel MT
```

Each command runs notebooks sequentially. If a notebook fails, execution stops and the error is printed. Previously completed notebooks are not re-run.

### Step 4 — Optional: partial run flags

```bash
# Resume from notebook 04 (useful after fixing a clustering error)
python run_pipeline.py --channel EC --start-from 04

# Run only notebook 08 (re-generate reports without re-running clustering)
python run_pipeline.py --channel EC --only 08

# Accepted values for --start-from and --only: 01, 02, 03, 04, 05, 06, 07, 08
```

### Step 5 — Run the cross-channel diagnostic (optional, after all three channels complete)

NB09 reads outputs from EC, TT, and MT simultaneously. All three channels must have been run at least through NB03 before this works.

```bash
python run_diagnostic.py
```

### Step 6 — Generate NB10 pivot detail files (optional)

After NB09 has run and `09_threshold_diagnostic.csv` exists:

```bash
cd ../notebooks
jupyter nbconvert --to notebook --execute 10_pivot_detail.ipynb --output 10_pivot_detail_executed.ipynb
```

### What Each Notebook Does and What It Produces

| Notebook | Runtime | Key Output Files |
|----------|---------|-----------------|
| NB01 — Exploration & Cleaning | ~30s | `01_clean_sales.csv` |
| NB02 — ASP Bucketing | ~60s | `02_fine_bucket_ts.csv`, `02_price_distributions.png` |
| NB03 — Trend Pivot | ~30s | `03_segment_pivots.pkl`, `03_hl_cabin_trend_pivot.png` |
| NB04 — Clustering | ~2–5 min | `archetype_mapping.csv`, `archetype_keys.csv` |
| NB05 — Key Verification | ~20s | `archetype_keys.csv` (verified, re-saved) |
| NB06 — Validation | ~30s | `06_validation_summary.csv`, `06_validation_detail.csv` |
| NB07 — Analytical Base Table | ~2 min | `07_analytical_base_table.csv`, `07_archetype_monthly.csv` |
| NB08 — Reporting | ~3–8 min | `per_portal/*`, `consolidated/*` (CSVs, XLSXs, PNGs) |
| NB09 — Diagnostic | ~5 min | `09_threshold_diagnostic.csv`, PNG charts |
| NB10 — Pivot Detail | ~3 min | `10_pivot_detail/*.xlsx`, `10_master_nb_summary.csv` |

### Checking the Run Log

Each run creates a timestamped log at `src/logs/{CHANNEL}/run_{YYYYMMDD_HHMMSS}.log`. Review it after any run to confirm all notebooks completed:

```
[08:02:01] PIPELINE COMPLETE  - channel: EC
[08:02:01]   Total elapsed      : 847s
[08:02:01]   Outputs in         : data/outputs/EC/
```

---

## 4. Input Data Requirements

### 4.1 Required Schema

Every raw file must contain the following columns. Column names differ by channel — the table shows the exact name expected in each:

| Logical Field | EC Column Name | TT Column Name | MT Column Name | Data Type | Notes |
|---------------|---------------|----------------|----------------|-----------|-------|
| Division | `Division` | `Division` | `Division` | string | See allowed values below |
| Portal | `Portal` | `Portal` | `Portal` | string (EC/MT) or integer (TT) | Exact match required |
| Size | `Size` | `Size` | `Size` | string | See allowed values below |
| Price range | `Range` | `Masked Range` | `Range_mask` | string | e.g. `"1200-1299"` or any label |
| Channel label | `Final Channel` | `Final Channel` | `Final Channel` | string | Must match `channel_filter` value |
| Year | `year` | `year` | `year` | integer | e.g. `2024` |
| Month | `month` | `month` | `month` | integer | 1–12 |
| Quantity | `qty` | `qty` | `qty` | integer or float | Units sold |
| Net Sales | `net_sales` | `net_sales` | `net_sales` | float | Revenue in ₹ |

**Currently used Division values:** `HL`, `SL`, `BP`, `BS`, `DF`

**Currently used Size values:** `CABIN`, `LARGE`, `MEDIUM`, `SO2`, `SO3`, `Single`, `DF`, `DFT`

**Currently used Portal values:**
- EC: `Amazon`, `Flipkart`, `D2C`, `Myntra`, `Blinkit`, `MP`, `Others`
- TT: `1` (integer)
- MT: `Dmart`, `Others`, `Reliance`, `Vishal`

> **Important:** The `Division`, `Size`, and `Final Channel` columns are stripped of leading/trailing whitespace by NB01. But the `Portal` column is **not** stripped. A portal value of `"Amazon "` (trailing space) will create a different segment from `"Amazon"` and will silently produce incorrect outputs. Ensure portal values are clean before importing.

### Data Types in Detail

**`year`** — Must be a plain integer (e.g., `2024`, not `"2024"` as a string, not `2024.0` as a float). If stored as float in Excel, pandas may read it correctly but pass the dtype check only if values are whole numbers. Add a safety cast in NB01 if needed: `df['year'] = df['year'].astype(int)`.

**`month`** — Integer 1–12. Not a date string. Not a month name. Not `"Jan"`.

**`qty`** — Numeric. Zero or negative rows are not filtered by the pipeline — they are included in aggregations and can distort ASP. Clean these before import if they represent returns or cancellations.

**`net_sales`** — Numeric in ₹. Used to compute ASP = `net_sales / qty`. A row with `qty = 0` and `net_sales > 0` produces a division-by-zero ASP and will map to `bucket_min = 0`. Clean these rows before import.

**Price range column** (`Range`, `Masked Range`, `Range_mask`) — Used only for grouping before ASP computation. The actual string value does not matter — it is only used as a groupby key. Any label format works (e.g., `"1000-1499"`, `"MID"`, `"Tier2"`) as long as ranges that should share an ASP are consistently labeled the same way per month.

**`Final Channel`** — Must exactly match the `channel_filter` value in `channel_registry.py`. For EC data it must be `"EC"`, for TT it must be `"TT"`, for MT it must be `"MT"`. Rows not matching are silently dropped by NB01.

### 4.2 Data Quality Rules

**Missing values:** Nulls in `Division`, `Portal`, `Size`, `year`, `month`, `qty`, or `net_sales` will cause groupby errors or silent NaN propagation. The pipeline does not explicitly handle them — clean nulls before import.

**Minimum data requirements:**
- A segment (Division × Portal × Size) needs at least `min_history_months` months of data for any of its buckets to qualify as "active". For EC/MT this is 6 months; for TT it is 3. Segments below this threshold will have no active buckets and will produce trivial single-archetype outputs.
- A segment needs total volume above `min_segment_qty` to be included at all. For EC/MT this is 5,000 units; for TT it is 0 (all segments included).
- A segment with fewer than 2 active buckets cannot be clustered — it will be assigned a single archetype covering all price points.

**Edge cases that break the pipeline:**

| Scenario | Effect | Prevention |
|----------|--------|------------|
| `qty = 0` on a row with `net_sales > 0` | Division by zero → `ASP = inf` → `bucket_min = NaN` or wrong bucket | Remove or correct such rows before import |
| Portal value with trailing space (e.g., `"Amazon "`) | Creates phantom segment `HL_Amazon _LARGE` distinct from `HL_Amazon_LARGE` | Strip portal column in your data prep |
| Year column stored as float (`2024.0`) | May work or may cause groupby issues; not guaranteed | Cast to int before import |
| Two rows with identical (Division, Portal, Size, sale_date, Range) | Summed in NB02 groupby — usually fine, but confirms no double-counting in source data | Dedup your raw export if in doubt |
| New Division or Size value not previously seen | Pipeline will process it without error, but NB06 validation may fail if ground truth doesn't have it | Expected if intentionally adding new categories |
| Segment with all sales in one month | Only one active month → 0-variance time series → Pearson correlation = undefined → `merge_cost = 1.0` for all pairs → all buckets end up in K=2 groups | Acceptable behavior; no crash |

---

## 5. Using a New Dataset (Same Channel Structure)

**Scenario:** You have updated sales data for EC (or TT or MT) with the same column structure. You want to re-run the full pipeline against the new data.

### Step 1 — Prepare the new file

Your new file must match the schema for its channel exactly (Section 4.1). The sheet name must also match — `Sheet1` for EC, `raw` for TT and MT.

If your file has an additional validation sheet (e.g., `Bucket_mapped` for EC with analyst-verified New Bucket assignments), include it. If you do not have a validation sheet, NB06 will fail — see the note below on skipping validation.

### Step 2 — Back up the existing raw file (recommended)

```bash
# In project root
cp data/raw/ec_data.xlsx data/raw/ec_data_backup_YYYYMMDD.xlsx
```

This is not required but protects you if the new file has problems.

### Step 3 — Replace the raw file

Copy your new file into `data/raw/` with the exact filename the channel expects:

```bash
# For EC:
cp /path/to/your/new_ec_data.xlsx data/raw/ec_data.xlsx

# For TT:
cp /path/to/your/new_tt_data.xlsx data/raw/manual_validation.xlsx

# For MT:
cp /path/to/your/new_mt_data.xlsx data/raw/mt_data.xlsx
```

> **Why the exact filename?** The filename is hardcoded in `channel_registry.py` under `raw_path`. If you use a different name, update `raw_path` in the registry too (see Section 6.2).

### Step 4 — Clear old outputs for that channel

Old outputs from the previous run are still in `notebooks/data/outputs/{CHANNEL}/`. The pipeline will overwrite them, but stale intermediate files (especially `03_segment_pivots.pkl`) from a previous data run can cause incorrect results if the pipeline fails partway through. Clearing ensures a clean start:

```bash
rm -rf "notebooks/data/outputs/EC/"    # or TT or MT
```

### Step 5 — Validate the new file's schema before running

Open the file in Python and confirm the column names and key distributions match expectations:

```python
import pandas as pd

# Replace with your channel's file and sheet
df = pd.read_excel("data/raw/ec_data.xlsx", sheet_name="Sheet1")

# 1. Check required columns are present
required = ["Division", "Portal", "Size", "Range", "Final Channel",
            "year", "month", "qty", "net_sales"]
missing = [c for c in required if c not in df.columns]
print("Missing columns:", missing)  # Should be empty

# 2. Check Final Channel values
print("Final Channel values:", df["Final Channel"].unique())
# Should contain "EC" (or "TT" / "MT" depending on channel)

# 3. Check for nulls in critical columns
print(df[required].isnull().sum())

# 4. Check year range
print("Years:", sorted(df["year"].unique()))

# 5. Check segment inventory
seg = df.groupby(["Division", "Portal", "Size"]).size().reset_index(name="rows")
print(seg.to_string())
```

Fix any issues found before proceeding.

### Step 6 — Run the pipeline

```bash
cd src
python run_pipeline.py --channel EC
```

### Step 7 — Verify the outputs

After the run completes, check these three things:

**A. Segment count in archetype_mapping.csv:**
```python
import pandas as pd
df = pd.read_csv("notebooks/data/outputs/EC/archetype_mapping.csv")
print(df.groupby(["Division","Portal","Size"])["New_Bucket"].nunique())
```
Compare the segment list to what you saw in Step 5. Any segment from your new data should appear here.

**B. NB06 validation summary:**
```python
val = pd.read_csv("notebooks/data/outputs/EC/06_validation_summary.csv")
print(val[["Division","Portal","Size","pct_correct","qty_correct_pct"]])
```
A healthy run shows `pct_correct` above 85% for most segments. If you have no validation sheet (new data with no ground truth), NB06 will fail — see below.

**C. Check for sparse segments:**
```python
keys = pd.read_csv("notebooks/data/outputs/EC/archetype_keys.csv")
one_bucket = keys.groupby(["Division","Portal","Size"])["New_Bucket"].nunique()
print("Segments with K=1 (suspicious):", one_bucket[one_bucket == 1])
```
A K=1 segment means all price activity collapsed into one archetype, typically because the segment has very few months of data or very low volume.

### What Can Go Wrong

**Column name mismatch:** NB02 will raise `ValueError: Range column 'Range' not found` if your new file uses a different column name for the price range (e.g., `Price_Range` instead of `Range`). Fix: either rename the column in your file, or update `range_col` in `channel_registry.py` for that channel.

**New portal names:** If your new data contains a portal like `"Meesho"` that wasn't in the old data, the pipeline will process it without error, but any `segment_threshold_overrides` for old portals will still apply, and the new portal will run at the default threshold (0.70). This is correct behavior.

**Segment sparsity with new data:** If your new file covers a shorter time period (e.g., only 4 months), EC segments will fail the `min_history_months = 6` filter. Most buckets will be classified as sparse and assigned to the nearest active bucket's archetype. The result is valid but less granular.

**No validation sheet:** If your new Excel file does not have a `Bucket_mapped` sheet (EC/MT) or `Bucket_map` sheet (TT), NB06 will crash. To skip validation for a run with no ground truth, run `--start-from 07` (skip NB06) or `--only 07` then `--only 08`.

### Validation Checklist — New Dataset

- [ ] File placed at correct path with correct filename
- [ ] All required columns present with correct names
- [ ] `Final Channel` values match `channel_filter` in registry
- [ ] No nulls in Division, Portal, Size, year, month, qty, net_sales
- [ ] `year` is integer type
- [ ] Portal values have no leading/trailing spaces
- [ ] `qty > 0` on all rows (or negatives are intentional returns and acceptable)
- [ ] Old outputs cleared from `notebooks/data/outputs/{CHANNEL}/`
- [ ] Pipeline ran to completion (check log file)
- [ ] `archetype_keys.csv` shows expected number of segments
- [ ] No K=1 segments in unexpected places

---

## 6. Adding a New Channel (Different Structure)

**Scenario:** You have data from a new sales channel — for example, "Wholesale" (WS) — with its own portals, segment structure, and Excel file. You want to run the full pipeline for this new channel.

This is the most involved change in the system. Follow every step in order.

### 6.1 What Defines a Channel

A channel is defined by five things:

1. **A raw Excel file** at a known path with a known sheet name
2. **A channel filter value** — the string in the `Final Channel` column that identifies this channel's rows
3. **A segment definition** — the columns that together identify a unique segment (always `["Division", "Portal", "Size"]` in existing channels)
4. **Portal mappings** — whether portals are integers (TT-style) or strings (EC/MT-style), and what abbreviations to use
5. **Clustering parameters** — MAX_K, thresholds, minimum volume, bucket widths

### 6.2 Required Changes

#### A. Add the new channel to `channel_registry.py`

Open `src/channel_registry.py`. Add a new entry to `CHANNEL_REGISTRY`. Below is a complete template for a new "WS" (Wholesale) channel — replace every value with your actual data:

```python
"WS": {
    # ── File location ──────────────────────────────────────────────
    "raw_path"   : "data/raw/ws_data.xlsx",    # path relative to project root
    "raw_sheet"  : "Sheet1",                   # exact sheet name in Excel file

    # ── Column names (must match exact column names in your Excel file) ──
    "range_col"  : "Price_Range",    # column containing price range labels
    "portal_col" : "Portal",         # column containing portal name

    # ── Portal type ────────────────────────────────────────────────
    # True  → portals are integers (like TT uses portal=1)
    # False → portals are strings (like EC uses "Amazon", "Flipkart")
    "portal_is_int" : False,

    # ── Channel filter ─────────────────────────────────────────────
    # NB01 filters rows where df["Final Channel"] == channel_filter
    # This must exactly match the value in your data's Final Channel column
    "channel_filter" : "WS",

    # ── Bucketing configuration ────────────────────────────────────
    "bucket_width"      : 100,    # standard ₹100 buckets
    "bucket_width_tail" : 500,    # wider ₹500 buckets for high-price items
                                   # Set to None to disable tail bucketing

    # ── Tail bucketing thresholds per division ─────────────────────
    # Price at or above which a division uses bucket_width_tail instead of bucket_width
    # If tail bucketing disabled (bucket_width_tail=None), set this to {}
    "tail_switch_price" : {
        "BP": 1500,
        "BS": 1500,
        "DF": 1500,
        "HL": 5000,
        "SL": 4000,
    },

    # ── Segment definition ─────────────────────────────────────────
    # Columns that together identify a unique segment
    # Do not change this unless your channel uses different segment dimensions
    "segment_dims" : ["Division", "Portal", "Size"],

    # ── Time filtering ─────────────────────────────────────────────
    # Years to completely exclude from analysis
    "ignore_years" : [2023],

    # ── Clustering parameters ──────────────────────────────────────
    "rolling_median_months"    : 3,      # ASP smoothing window
    "min_history_months"       : 6,      # months active before a bucket qualifies
    "noise_floor_pct"          : 0.001,  # min volume share to be active (0.1%)
    "max_k"                    : 10,     # max archetypes per segment
    "min_cluster_vol_pct"      : 0.01,   # min volume per archetype (1%)
    "trend_similarity_threshold": 0.70,  # global clustering threshold
    "min_segment_qty"          : 5000,   # segments below this total qty are skipped

    # ── Output path ────────────────────────────────────────────────
    # Relative to notebooks/ directory (CWD during execution)
    # This folder will be created automatically
    "out_path" : "data/outputs/WS/",

    # ── Validation configuration ───────────────────────────────────
    # Set these to point to a sheet in your raw file that has analyst-verified
    # New Bucket assignments. If you have no ground truth, these will be unused
    # only if you skip NB06 (--start-from 07).
    "validation_file"  : "data/raw/ws_data.xlsx",   # same file as raw_path is fine
    "validation_sheet" : "Bucket_mapped",            # sheet with ground truth
    "validation_gt_col": "New Bucket",               # column with analyst's bucket number
    "validation_min_col": "ASP_bucket",              # column with price range string
    "validation_join"  : "parse_string",             # "floor_100" or "parse_string"
                                                     # floor_100: validation_min_col is an integer
                                                     # parse_string: validation_min_col is "1200-1299"

    # ── Portal abbreviations ───────────────────────────────────────
    # Only needed when portal_is_int = True (i.e., TT-style integer portals)
    # Map integer portal ID to string abbreviation for archetype key construction
    # Example for TT: {1: "TT"}
    # Leave empty for string-portal channels
    "portal_abbrev" : {},

    # ── Ground truth key column ────────────────────────────────────
    # Column in the validation sheet that contains the analyst's archetype key string
    "gt_key_col" : "key",

    # ── Segment-specific threshold overrides ──────────────────────
    # Leave empty initially — add overrides after running NB09
    "segment_threshold_overrides": {},
},
```

> **Why each parameter matters:** `min_history_months = 6` means a price bucket must appear in at least 6 months to be included in clustering. Too low and you cluster on noise; too high and you discard real segments with seasonal data. For a new channel start with 6 and adjust after reviewing NB09 output. `min_segment_qty = 5000` filters out segments too sparse to cluster meaningfully. Set lower (e.g., 1000) if your channel has low overall volumes.

#### B. Register the new channel name in `run_pipeline.py`

Open `src/run_pipeline.py`. Find this line:

```python
parser.add_argument("--channel", required=True, choices=["EC", "TT", "MT"])
```

Change it to:

```python
parser.add_argument("--channel", required=True, choices=["EC", "TT", "MT", "WS"])
```

> **Why this is required:** argparse validates the `--channel` value against this list. If you omit this change, `python run_pipeline.py --channel WS` will immediately fail with an error before any notebook runs.

#### C. Place your raw data file

Copy your Excel file to the path specified in `raw_path`:

```bash
cp /path/to/your/ws_data.xlsx "data/raw/ws_data.xlsx"
```

### 6.3 Ensuring NB01 Can Read Your Schema

NB01 expects these exact column names in the raw file: `Division`, `Portal`, `Size`, `Final Channel`, `year`, `month`, `qty`, `net_sales`, and whatever you specified as `range_col`.

**If your file uses different column names**, you have two options:

**Option A (preferred) — rename columns in your file** before placing it in `data/raw/`. This requires no code changes.

**Option B — add a column rename step to NB01**. Open `notebooks/01_exploration (1).ipynb`. After the `pd.read_excel(...)` cell, add a new cell:

```python
# Rename columns to match pipeline expectations
df = df.rename(columns={
    "product_category": "Division",
    "channel_name":     "Portal",
    "sku_size":         "Size",
    "sale_year":        "year",
    "sale_month":       "month",
    "units_sold":       "qty",
    "revenue":          "net_sales",
    "price_band":       "Price_Range",   # this must match range_col in registry
    "sales_channel":    "Final Channel",
})
```

**Only use Option B if the new channel is permanent and you own the notebook**. Do not use Option B as a temporary workaround if you intend to revert — it will break all existing channel runs.

### 6.4 Ensuring NB02–NB04 Compatibility

NB02, NB03, and NB04 rely entirely on `config.py` constants (loaded via `from config import *`). Because `config.py` reads from `channel_registry.py` using the `CHANNEL` environment variable, these notebooks automatically pick up your new channel's parameters without any modification — as long as:

- The `range_col` value in your registry entry exactly matches a column in `01_clean_sales.csv`
- The `Division` values in your data match the division names used in `tail_switch_price` (if tail bucketing is enabled)

**Check the range column is present:**
After NB01 runs, verify `01_clean_sales.csv` has your range column:

```python
import pandas as pd
df = pd.read_csv("notebooks/data/outputs/WS/01_clean_sales.csv")
print(df.columns.tolist())
# Your range_col value (e.g., "Price_Range") must appear here
```

### 6.5 Testing the New Channel

Run only NB01 first to catch data problems early:

```bash
python run_pipeline.py --channel WS --only 01
```

Check the output:

```bash
# Confirm the output file was created
ls notebooks/data/outputs/WS/
# Should show: 01_clean_sales.csv

# Check segment inventory
python3 -c "
import pandas as pd
df = pd.read_csv('notebooks/data/outputs/WS/01_clean_sales.csv')
print(df.groupby(['Division','Portal','Size']).size().reset_index(name='rows').to_string())
"
```

Confirm the segment list matches your expectations. If you see unexpected segments (e.g., phantom `'SO3 '` vs `'SO3'`), fix the data before continuing.

Then run NB02:

```bash
python run_pipeline.py --channel WS --only 02
```

Check bucket counts per segment:

```python
bts = pd.read_csv("notebooks/data/outputs/WS/02_fine_bucket_ts.csv")
print(bts.groupby(["Division","Portal","Size"])["bucket_min"].nunique())
```

Expect 15–80 buckets per segment. More than 100 suggests data spread across too wide a price range or tail bucketing is not engaged. Fewer than 5 suggests very sparse data.

After NB02 passes, run the full pipeline:

```bash
python run_pipeline.py --channel WS
```

**Validate clustering output (NB04):**

```python
keys = pd.read_csv("notebooks/data/outputs/WS/archetype_keys.csv")
print(keys.groupby(["Division","Portal","Size"])["New_Bucket"].nunique().rename("K"))
```

Expect K between 2 and `max_k` (10) for healthy segments. K=1 everywhere is a sign that `min_history_months` or `min_segment_qty` is too high for your data volume.

### 6.6 Common Failure Points for New Channels

**"Channel 'WS' nahi mila" / ValueError:**
You added the registry entry but did not add `"WS"` to the `choices` list in `run_pipeline.py`. Fix: add it (Section 6.2B).

**NB01 fails with `KeyError: 'Final Channel'`:**
Your Excel file does not have a `Final Channel` column. Either add it to your file, or add a rename in NB01 as described in Section 6.3.

**NB02 fails with `ValueError: Range column 'X' not found`:**
The `range_col` in your registry entry does not match any column in the cleaned CSV. The error message will print available columns. Fix: update `range_col` to the correct column name.

**All segments produce K=1:**
Either `min_history_months` is higher than the data's date span (e.g., you have 4 months but require 6), or `noise_floor_pct` filters out all buckets. Start by setting `min_history_months: 3` and `noise_floor_pct: 0.0001`, then tune upward.

**NB06 fails with `FileNotFoundError` on validation sheet:**
Your Excel file does not have the sheet named in `validation_sheet`. Either add a `Bucket_mapped` sheet with ground truth data, or skip NB06 using `--start-from 07`.

**Incorrect segment keys in `archetype_keys.csv`:**
Segment keys are constructed as `"{portal}{div}{size}{nb}"` (string portals) or `"{div}{abbrev}{portal}{nb}{size}"` (integer portals). If your portals are integers but you set `portal_is_int: False`, the keys will be malformed. Check the `portal_is_int` setting matches your actual data.

**Segment threshold overrides have no effect:**
Overrides use the segment key format `"{Division}_{Portal}_{Size}"` (e.g., `"HL_Reliance_LARGE"`). For TT with integer portals the key format is `"HL_1_CABIN"`. Verify the key format for your channel by printing `list(all_final_maps.keys())` inside NB04 after the clustering loop.

---

## 7. Threshold Tuning Guide

### When to Adjust Thresholds

You need to tune thresholds when:

- A segment produces too few archetypes (e.g., K=3 when business expects 6 distinct price tiers)
- A segment produces one very wide archetype spanning a huge price range while most volume sits in a narrow sub-range
- NB06 validation shows low accuracy for specific segments

**Do not tune thresholds speculatively.** Run NB09 first and let the diagnostic tell you which segments actually need adjustment.

### Step 1 — Run NB09

Ensure all three channels have been run through at least NB03, then:

```bash
cd src
python run_diagnostic.py
```

Output: `notebooks/data/outputs/09_threshold_diagnostic.csv`

### Step 2 — Read the diagnostic CSV

```python
import pandas as pd
diag = pd.read_csv("notebooks/data/outputs/09_threshold_diagnostic.csv")

# Find segments that need tuning
candidates = diag[
    (diag["k_diff_60"] >= 2) &
    (diag["total_vol"] > 10000)
].sort_values("k_diff_60", ascending=False)

print(candidates[["channel","seg_key","k_at_070","k_at_060","k_diff_60","total_vol"]])
```

Column definitions:
- `k_at_070` — archetypes produced at the default threshold (0.70)
- `k_at_060` — archetypes produced at the lower threshold (0.60)
- `k_diff_60` — how many extra archetypes you get by lowering to 0.60
- `total_vol` — total historical units sold in this segment
- `needs_tuning` — True if the segment has a wide archetype with concentrated volume

### Step 3 — Apply overrides

For each segment where `k_diff_60 >= 2 AND total_vol > 10,000`, add an entry to `segment_threshold_overrides` in `channel_registry.py`:

```python
"segment_threshold_overrides": {
    "HL_MP_CABIN"     : 0.60,   # k_diff_60 = 3, vol = 45,000
    "HL_Flipkart_LARGE": 0.60,  # k_diff_60 = 2, vol = 28,000
    # ... etc
},
```

The key format must match the segment key used in your channel's data: `"{Division}_{Portal}_{Size}"`. For TT, portals are integers: `"HL_1_CABIN"`.

> **Why 0.60 specifically?** The diagnostic tests 0.70, 0.60, and 0.50. Going to 0.50 typically over-fragments segments. Going to 0.60 captures genuinely distinct sub-groups without excessive splitting. If 0.60 still doesn't help a segment (k_diff_60 is 0 even at 0.60), the issue is MAX_K — the segment already hits the cap at the current threshold.

### Step 4 — Re-run clustering

After updating the overrides, re-run from NB04 only (no need to re-run NB01–NB03):

```bash
python run_pipeline.py --channel EC --start-from 04
```

### Step 5 — Review NB10 pivot files before finalizing

Before committing the overrides as permanent, generate NB10 pivot detail files and have an analyst verify the new archetypes make business sense:

```bash
cd ../notebooks
jupyter nbconvert --to notebook --execute 10_pivot_detail.ipynb --output 10_pivot_detail_executed.ipynb
```

Open `notebooks/data/outputs/10_pivot_detail/{seg_key}_pivot_detail.xlsx`. The file shows quantity by New Bucket × year × month. Confirm each archetype covers a coherent, distinct price range with meaningful volume.

### Impact of Threshold Changes

| Change | Effect |
|--------|--------|
| Lower threshold (0.60) for a segment | More archetypes, finer-grained price segmentation |
| Raise threshold (0.80) for a segment | Fewer archetypes, broader price bands |
| Raise MAX_K | Allows more archetypes but doesn't force them — only affects the cap |
| Raise min_history_months | Fewer buckets qualify as active → fewer archetypes overall |
| Raise noise_floor_pct | Rare buckets filtered out → cleaner clusters |

---

## 8. Output Interpretation

### archetype_mapping.csv

The master join table. One row per price bucket per segment. When you want to label a transaction with its archetype, join on `(Division, Portal, Size, bucket_min)`.

Key columns:
- `bucket_min` — lower bound of the ₹100 bucket (e.g., `1200` means ₹1,200–₹1,299)
- `New_Bucket` — integer 1..K, lowest price bucket = NB1, highest = NBK
- `archetype_key` — human-readable string identifier for the archetype

### archetype_keys.csv

Summary table. One row per archetype. Use this to look up what price range a given New Bucket covers.

Key columns:
- `price_range_min` / `price_range_max` — the full price range covered by this archetype
- `total_qty` — historical volume in this archetype
- `fine_bucket_count` — number of ₹100 buckets grouped into this archetype

### What NB1, NB2, NB3... Represent

`NB1` is always the **cheapest** archetype in a segment. `NBK` is always the **most expensive**. The numbering is purely ordinal by price — NB2 does not mean "second most popular." It means "second cheapest price band."

Example for `HL_Flipkart_LARGE`:
- `NB1` → ₹1,200–₹1,999 (entry-level hardluggage)
- `NB2` → ₹2,000–₹2,999 (mid-range)
- `NB3` → ₹3,000–₹3,999 (premium mid)
- `NB4` → ₹4,000–₹4,999 (premium)
- `NB5` → ₹5,000+ (luxury)

These ranges are data-driven — the algorithm decided these boundaries based on which adjacent ₹100 buckets showed the most similar monthly sales share trends.

### pivot_ready.xlsx

The primary analyst file. Rows = archetypes, columns = YYYY-MM date strings. Values = units sold. Additional columns: `archetype_key` (for labeling), `TOTAL_QTY`, `VOL_PCT`.

How analysts use it:
1. Open in Excel → Insert → PivotTable / PivotChart
2. Plot `archetype_key` vs monthly qty to see how each price band's share changes over time
3. Compare `VOL_PCT` across archetypes to identify which price band dominates the segment
4. Use `TOTAL_QTY` across years to assess growth per archetype

### 06_validation_summary.csv

Tells you how accurately the Auto-K algorithm reproduced the manually-assigned archetypes. The key column is `qty_correct_pct` — the fraction of sales volume that was assigned to the correct archetype. A value above 90% means the algorithm is performing very close to human-level quality for that segment.

Low validation accuracy (below 70%) for a segment does not necessarily mean the algorithm is wrong — it may mean the ground truth itself changed (e.g., the analyst revised the bucket boundaries for the new data period). Investigate the mismatch detail in `06_validation_detail.csv` before assuming a bug.

---

## 9. Debugging and Recovery

### Common Errors and Fixes

**Error:** `PermissionError: [Errno 13] Permission denied: '...archetype_mapping.csv'`

**Cause:** The file is open in Excel. Excel locks the file on Windows.

**Fix:** Close Excel, then re-run: `python run_pipeline.py --channel EC --only 04`

---

**Error:** `argument --only: expected one argument` or `argument --start-from: expected one argument`

**Cause:** You ran `--only` or `--start-from` without providing the notebook number.

**Fix:** Always include the two-digit prefix: `--only 08`, not `--only`.

---

**Error:** `NameError: name 'null' is not defined` when executing NB09 or NB10

**Cause:** The notebook JSON file has been corrupted — Python `None` was saved as JSON `null` which is not valid Python syntax.

**Fix:**
```bash
cd src
python write_nb09.py        # regenerates NB09
python write_nb10_pivot_detail.py  # regenerates NB10
```
Then re-run.

---

**Error:** `FileNotFoundError: [Errno 2] No such file or directory: 'data/outputs/EC/03_segment_pivots.pkl'`

**Cause:** NB03 has not been run yet, or was run for a different channel.

**Fix:** Run from NB03: `python run_pipeline.py --channel EC --start-from 03`

---

**Error:** `ValueError: Channel 'XX' nahi mila. Available channels: ['EC', 'TT', 'MT']`

**Cause:** You passed a channel name that isn't in `CHANNEL_REGISTRY` (e.g., wrong case `--channel ec` instead of `--channel EC`), or you added a new channel to the registry but didn't add it to `run_pipeline.py`'s choices list.

**Fix:** Check spelling and case. Add to `choices` in `run_pipeline.py` if adding a new channel.

---

**Error:** `ValueError: Range column 'Range' not found. Available: ['Division', 'Portal', 'Size', 'Price_Band', ...]`

**Cause:** The `range_col` in `channel_registry.py` for this channel (`"Range"`) does not match the actual column name in the data (`"Price_Band"`).

**Fix:** Update `range_col` in `channel_registry.py` to the correct column name. Then re-run from NB01.

---

**Error:** Pipeline runs but `archetype_keys.csv` shows K=1 for all segments

**Cause A:** `min_history_months` is higher than the number of months in your data.
**Fix:** Lower `min_history_months` in the channel registry (e.g., from 6 to 3).

**Cause B:** `min_segment_qty` is too high, filtering out all segments.
**Fix:** Lower `min_segment_qty` (e.g., from 5000 to 1000).

**Cause C:** `noise_floor_pct` is too high, filtering all buckets as noise.
**Fix:** Lower to 0.0001.

---

**Error:** NB04 runs but produces the wrong K for known segments (validation fails badly)

**Cause:** The `trend_similarity_threshold` is misconfigured, or `segment_threshold_overrides` has wrong segment key spellings.

**Fix:** Open `09_threshold_diagnostic.csv` and find the segment. Check `k_at_070` vs expected K. If the segment key format in `segment_threshold_overrides` uses the wrong separator or wrong portal format, the override is silently ignored and the default threshold is used. Print the actual segment keys from the data:
```python
import pandas as pd
keys = pd.read_csv("notebooks/data/outputs/EC/archetype_keys.csv")
print(keys[["Division","Portal","Size"]].drop_duplicates().assign(
    seg_key=lambda d: d["Division"]+"_"+d["Portal"].astype(str)+"_"+d["Size"]
)["seg_key"].tolist())
```

---

### How to Resume After a Failure

The pipeline saves outputs after each notebook. If NB06 fails, NB01–NB05 outputs are intact. Resume from the failing notebook:

```bash
# NB06 failed → resume from NB06
python run_pipeline.py --channel EC --start-from 06

# NB04 failed → resume from NB04 (NB01-03 outputs are preserved)
python run_pipeline.py --channel EC --start-from 04
```

The executed notebook file (e.g., `04_clustering (1)_executed.ipynb`) is saved up to the failing cell. Open it in Jupyter to read the exact error traceback.

### Finding the Error in a Failed Notebook

```bash
# Open the executed notebook in Jupyter for debugging
jupyter notebook "notebooks/04_clustering (1)_executed.ipynb"
```

Scroll to the last cell with output — it will show the full Python traceback. The log file (`src/logs/EC/run_YYYYMMDD_HHMMSS.log`) also records the cell index and error type.

---

## 10. Safe Modification Guidelines

### What Can Be Changed Safely

The following changes are safe and will not break the pipeline for other channels:

**In `channel_registry.py`:**
- Adding new entries for new channels
- Modifying `segment_threshold_overrides` for any channel (only affects NB04 for that channel)
- Adjusting `min_history_months`, `noise_floor_pct`, `max_k`, `min_cluster_vol_pct`, `trend_similarity_threshold` for a channel
- Changing `ignore_years` to exclude or include additional years
- Changing `out_path` (creates a new output folder — old outputs remain)

**In `run_pipeline.py`:**
- Adding new channel names to the `choices` list
- Changing `TIMEOUT` (default 3600 seconds per notebook)

**In `clustering.py`:**
- The `post_merge_cleanup` function (only called in the legacy algorithm path, not Auto-K)

### What Must NOT Be Changed

**Never rename or move notebook files.** The NOTEBOOKS list in `run_pipeline.py` maps two-digit prefixes to exact filenames. Renaming a notebook breaks `--only NN` and `--start-from NN`.

**Never change `config.py`** except to add new constant exports for new keys you've added to the registry. The existing constants (`CHANNEL`, `RAW_PATH`, `OUT_PATH`, etc.) are imported by every notebook — removing or renaming one breaks all notebooks.

**Never change the CWD assumption.** Notebooks resolve all paths relative to the `notebooks/` directory. Do not add `os.chdir()` calls in notebooks or papermill invocations without updating all path references.

**Never change the segment key format** in `segment_threshold_overrides` without also updating all existing override entries. The key is `"{Division}_{Portal}_{Size}"` with underscores — any deviation means the override is silently ignored.

**Never modify `01_clean_sales.csv` manually** between notebook runs. It is regenerated by NB01 and treated as the authoritative cleaned source by NB02 onward. Any manual edits will be overwritten on the next NB01 run.

**Never add `Portal` to the string-stripping loop in NB01 without testing** all channels first. TT uses integer portals — stripping them as strings would convert `1` to `"1"` and break downstream integer comparisons.

### Versioning Strategy

Before any structural change (new channel, threshold overrides, parameter adjustment):

1. **Copy the current `channel_registry.py`** to `channel_registry_backup_YYYYMMDD.py`. Keep it alongside the original.
2. **Save the current outputs** for the affected channel: `cp -r notebooks/data/outputs/EC/ notebooks/data/outputs/EC_backup_YYYYMMDD/`
3. Make the change and run the pipeline.
4. If the change produces worse results, restore from backup.

For new channel additions: keeping the backup is optional since new channels don't affect existing ones.

---

## 11. Operational Checklists

### Checklist: Running the Pipeline (Existing Channel, Existing Data)

```
Pre-run:
  [ ] Raw file exists at: data/raw/ec_data.xlsx (or mt / manual_validation)
  [ ] Jupyter kernel "python3" is registered (run: jupyter kernelspec list)
  [ ] Terminal CWD is src/

Execution:
  [ ] Run: python run_pipeline.py --channel EC
  [ ] Monitor terminal output for any FAIL messages

Post-run:
  [ ] Log file shows "PIPELINE COMPLETE"
  [ ] notebooks/data/outputs/EC/archetype_keys.csv exists
  [ ] notebooks/data/outputs/EC/per_portal/ contains xlsx files
  [ ] NB06 validation summary shows pct_correct > 80% for key segments
  [ ] No K=1 segments in archetype_keys for segments with >5,000 units
```

### Checklist: Adding New Data to an Existing Channel

```
Data prep:
  [ ] New file has all required columns with exact expected names
  [ ] Portal values have no leading/trailing spaces
  [ ] Final Channel column contains correct value (EC / TT / MT)
  [ ] year column is integer type
  [ ] No nulls in Division, Portal, Size, year, month, qty, net_sales
  [ ] Validation sheet (Bucket_mapped / Bucket_map) present (or plan to skip NB06)

File placement:
  [ ] File placed at: data/raw/{correct_filename}.xlsx
  [ ] Old outputs cleared: rm -rf notebooks/data/outputs/{CHANNEL}/

Execution:
  [ ] Run: python run_pipeline.py --channel {CHANNEL}
  [ ] Pipeline completes without error

Verification:
  [ ] Segment count matches expectations (check archetype_keys.csv)
  [ ] No unexpected K=1 segments
  [ ] NB06 accuracy is acceptable (if validation sheet was provided)
  [ ] Analyst reviews at least one pivot_ready.xlsx
```

### Checklist: Adding a New Channel

```
Registry:
  [ ] New channel entry added to CHANNEL_REGISTRY in channel_registry.py
  [ ] All required keys present (see Section 6.2A for complete list)
  [ ] channel_filter exactly matches Final Channel value in data
  [ ] range_col exactly matches column name in Excel file
  [ ] portal_is_int set correctly (True only for integer portals)
  [ ] out_path set to: "data/outputs/{CHANNEL}/"
  [ ] segment_threshold_overrides set to {} (empty for initial run)

run_pipeline.py:
  [ ] New channel name added to choices list in parse_args()

Data:
  [ ] Excel file placed at path specified in raw_path
  [ ] Sheet name matches raw_sheet
  [ ] All required columns present

Testing:
  [ ] NB01 only: python run_pipeline.py --channel WS --only 01
  [ ] Segment inventory looks correct
  [ ] NB02 only: python run_pipeline.py --channel WS --only 02
  [ ] Bucket counts per segment are reasonable (15–80)
  [ ] Full run: python run_pipeline.py --channel WS
  [ ] No K=1 segments for healthy-volume segments
  [ ] archetype_keys.csv K values are in range 2–max_k

Post-stabilization:
  [ ] Run python run_diagnostic.py (requires all channels at NB03+)
  [ ] Apply threshold overrides as needed per NB09 output
  [ ] Re-run from NB04 with overrides: python run_pipeline.py --channel WS --start-from 04
  [ ] Analyst sign-off on one segment's pivot_ready.xlsx
```

---

## 12. Example Walkthroughs

### Example 1: Running EC with a New Dataset

**Situation:** The analytics team has exported fresh EC data for 2024–2025. The file is at `Downloads/ec_sales_Q4.xlsx` with sheet `Sheet1` and all required columns present. You need to update the EC archetypes.

**Step 1 — Validate the file before touching the project:**

```python
import pandas as pd

df = pd.read_excel("~/Downloads/ec_sales_Q4.xlsx", sheet_name="Sheet1")

# Check columns
print(df.columns.tolist())
# Expected: includes Division, Portal, Size, Range, Final Channel, year, month, qty, net_sales

# Check Final Channel
print(df["Final Channel"].value_counts())
# Must include "EC"

# Check portal values — look for trailing spaces
portals = df["Portal"].unique().tolist()
print(repr(portals))  # repr() shows trailing spaces if any

# Check year range
print(sorted(df["year"].unique()))
# Expected: [2024, 2025]  (2023 excluded by pipeline)

# Check for nulls
print(df[["Division","Portal","Size","year","month","qty","net_sales"]].isnull().sum())
```

Output shows all clean. Portal values: `['Amazon', 'Flipkart', 'D2C', 'Myntra', 'Blinkit', 'MP', 'Others']` — no trailing spaces.

**Step 2 — Back up existing outputs and raw file:**

```bash
cd "D:\archetype_engine - Copy_2 - Copy"
cp data/raw/ec_data.xlsx data/raw/ec_data_backup_20250328.xlsx
```

**Step 3 — Replace the file:**

```bash
cp ~/Downloads/ec_sales_Q4.xlsx data/raw/ec_data.xlsx
```

**Step 4 — Clear old EC outputs:**

```bash
rm -rf notebooks/data/outputs/EC/
```

**Step 5 — Run the pipeline:**

```bash
cd src
python run_pipeline.py --channel EC
```

You see:

```
[08:02:01] ============================================================
[08:02:01] Archetype Engine  - channel : EC
[08:02:01] [01] 01_exploration (1).ipynb
[08:02:32] OK Done in 31s
[08:02:32] [02] 02_asp_bucketing (1).ipynb
[08:03:48] OK Done in 76s
...
[08:16:22] PIPELINE COMPLETE  - channel: EC
[08:16:22]   Total elapsed      : 861s
```

**Step 6 — Verify outputs:**

```bash
python3 -c "
import pandas as pd
keys = pd.read_csv('notebooks/data/outputs/EC/archetype_keys.csv')
k_per_seg = keys.groupby(['Division','Portal','Size'])['New_Bucket'].nunique().rename('K')
print(k_per_seg)
print()
print('Total archetypes:', len(keys))
print('K=1 segments:', (k_per_seg==1).sum())
"
```

```bash
# Check validation
python3 -c "
import pandas as pd
val = pd.read_csv('notebooks/data/outputs/EC/06_validation_summary.csv')
print(val[['Division','Portal','Size','pct_correct','qty_correct_pct']].to_string())
"
```

Results look good: no K=1 segments for high-volume portals, validation above 88% across all segments.

**Done.** The EC archetypes have been updated.

---

### Example 2: Adding a New Wholesale Channel

**Situation:** The business has started tracking Wholesale (WS) sales separately. The data team has provided `ws_sales_2024_2025.xlsx` with sheet `Sheet1`. It has the same column structure as EC except the price range column is called `Price_Band` instead of `Range`, and portals are string names: `"Distributor_A"`, `"Distributor_B"`, `"Direct"`.

**Step 1 — Examine the file:**

```python
import pandas as pd

df = pd.read_excel("ws_sales_2024_2025.xlsx", sheet_name="Sheet1")
print(df.columns.tolist())
# ['Division', 'Portal', 'Size', 'Price_Band', 'Final Channel', 'year', 'month', 'qty', 'net_sales']

print(df["Final Channel"].unique())
# ['WS']

print(df["Portal"].unique())
# ['Distributor_A', 'Distributor_B', 'Direct']

print(df["Division"].unique())
# ['HL', 'SL', 'BP']

print(sorted(df["year"].unique()))
# [2024, 2025]

print(df.groupby(["Division","Portal","Size"]).size().reset_index(name="rows"))
```

The file looks clean. Note: `range_col` must be `"Price_Band"`.

**Step 2 — Copy the file to the project:**

```bash
cp ws_sales_2024_2025.xlsx "data/raw/ws_data.xlsx"
```

**Step 3 — Add the WS channel to `channel_registry.py`:**

Open `src/channel_registry.py` and add the following block inside `CHANNEL_REGISTRY` (after the `"MT"` entry, before the closing `}`):

```python
"WS": {
    "raw_path"                 : "data/raw/ws_data.xlsx",
    "raw_sheet"                : "Sheet1",
    "range_col"                : "Price_Band",       # ← different from EC
    "portal_col"               : "Portal",
    "portal_is_int"            : False,
    "channel_filter"           : "WS",
    "bucket_width"             : 100,
    "bucket_width_tail"        : 500,
    "tail_switch_price"        : {
        "BP": 1500,
        "HL": 5000,
        "SL": 4000,
    },
    "segment_dims"             : ["Division", "Portal", "Size"],
    "ignore_years"             : [2023],
    "rolling_median_months"    : 3,
    "min_history_months"       : 6,
    "noise_floor_pct"          : 0.001,
    "max_k"                    : 10,
    "min_cluster_vol_pct"      : 0.01,
    "trend_similarity_threshold": 0.70,
    "min_segment_qty"          : 3000,   # ← lower than EC because WS volumes are smaller
    "out_path"                 : "data/outputs/WS/",
    "validation_file"          : "data/raw/ws_data.xlsx",
    "validation_sheet"         : "Bucket_mapped",    # must exist in ws_data.xlsx
    "validation_gt_col"        : "New Bucket",
    "validation_min_col"       : "ASP_bucket",
    "validation_join"          : "parse_string",
    "portal_abbrev"            : {},
    "gt_key_col"               : "key",
    "segment_threshold_overrides": {},
},
```

**Step 4 — Add "WS" to run_pipeline.py:**

Open `src/run_pipeline.py`. Find:

```python
parser.add_argument("--channel", required=True, choices=["EC", "TT", "MT"])
```

Change to:

```python
parser.add_argument("--channel", required=True, choices=["EC", "TT", "MT", "WS"])
```

**Step 5 — Note: WS data has no validation sheet yet.**

The file does not have a `Bucket_mapped` sheet. Plan: skip NB06 on first run using `--start-from 07`. You can add ground truth later after analysts review the outputs.

**Step 6 — Run NB01 only to test data loading:**

```bash
cd src
python run_pipeline.py --channel WS --only 01
```

Check output:

```bash
python3 -c "
import pandas as pd
df = pd.read_csv('notebooks/data/outputs/WS/01_clean_sales.csv')
print('Rows:', len(df))
print('Columns:', df.columns.tolist())
print(df.groupby(['Division','Portal','Size']).size().reset_index(name='rows').to_string())
"
```

Output shows 9 segments (3 divisions × 3 portals). No phantom segments.

**Step 7 — Run NB02 to check bucket counts:**

```bash
python run_pipeline.py --channel WS --only 02
```

```bash
python3 -c "
import pandas as pd
bts = pd.read_csv('notebooks/data/outputs/WS/02_fine_bucket_ts.csv')
print(bts.groupby(['Division','Portal','Size'])['bucket_min'].nunique().rename('buckets'))
"
```

Output shows 18–42 buckets per segment — healthy range.

**Step 8 — Run full pipeline, skipping NB06:**

```bash
python run_pipeline.py --channel WS --only 01   # already done, skip
python run_pipeline.py --channel WS --start-from 02   # runs NB02–NB08
```

Wait. Actually NB01 already ran. Resume from 03 to avoid re-running what's done:

```bash
python run_pipeline.py --channel WS --start-from 03
```

But NB06 will crash because there is no validation sheet. To handle this, run in two parts:

```bash
# Run NB03 through NB05
python run_pipeline.py --channel WS --only 03
python run_pipeline.py --channel WS --only 04
python run_pipeline.py --channel WS --only 05

# Skip NB06 — jump straight to NB07 and NB08
python run_pipeline.py --channel WS --only 07
python run_pipeline.py --channel WS --only 08
```

**Step 9 — Verify clustering output:**

```bash
python3 -c "
import pandas as pd
keys = pd.read_csv('notebooks/data/outputs/WS/archetype_keys.csv')
k = keys.groupby(['Division','Portal','Size'])['New_Bucket'].nunique().rename('K')
print(k)
# Expect K between 3 and 8 for healthy segments
print()
print('K=1 segments:', (k == 1).sum())
"
```

All 9 segments show K=4–7. No K=1. 

**Step 10 — Run cross-channel diagnostic after all channels have run:**

After EC, TT, MT, and WS have all been run through at least NB03:

```bash
python run_diagnostic.py
```

Check `09_threshold_diagnostic.csv` for WS segments. In this case no WS segments meet the `k_diff_60 >= 2 AND vol > 10,000` threshold criteria, so no overrides are needed for the initial run.

**Step 11 — Share results with analyst:**

```
notebooks/data/outputs/WS/per_portal/HL_Distributor_A_CABIN_pivot_ready.xlsx
```

Analyst confirms the archetype boundaries look correct for the WS business context. WS channel is now operational.

---

*End of Operational Guide*
