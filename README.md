# Archetype Automation Engine

A production-oriented analytics pipeline for converting raw luggage, backpack, and accessories sales data into stable price archetypes for demand forecasting.

The engine takes real multi-channel sales workbooks, cleans and buckets Average Selling Price (ASP), learns adjacent price bands with similar monthly sales-share behavior, validates the generated bands against mapped business references, and exports analyst-ready tables for downstream planning and forecasting.

## Why This Project Matters

Demand planning for backpacks and suitcases is difficult because sales are affected by seasonality, travel cycles, promotions, short product lifecycles, channel behavior, and frequent price movement. A raw SKU or price point is often too granular for reliable forecasting.

This project solves that by creating **archetypes**: standardized price ranges that group nearby price buckets with similar demand patterns. These archetypes can then be used as a more stable forecasting level for existing products, new SKUs, and channel-level demand planning.

Instead of manually grouping price bands in Excel, the pipeline produces reproducible, data-driven archetype mappings across divisions, portals, sizes, and channels.

## Dataset

The repository includes a complete real-world-style dataset under [`data/raw`](data/raw):

| Channel | File | Rows | Portals | Segment combinations | Years |
| --- | --- | ---: | ---: | ---: | --- |
| EC | `ec_data.xlsx` | 127,319 | 7 | 93 | 2023-2025 |
| TT | `manual_validation.xlsx` | 61,390 | 1 | 14 | 2023-2025 |
| MT | `mt_data.xlsx` | 106,235 | 4 | 51 | 2023-2025 |

Across the raw files, the data covers five divisions: `HL`, `SL`, `BP`, `BS`, and `DF`, with sizes such as `CABIN`, `LARGE`, `MEDIUM`, `SO2`, `SO3`, `Single`, `DF`, and `DFT`.

The pipeline currently has executable channel configuration for `EC` and `TT` in [`src/channel_registry.py`](src/channel_registry.py). MT data is present in the repo and documented, but should be added to the registry before running it through the same automated path.

## What The Engine Produces

For each configured channel, the notebooks generate:

- Cleaned channel-specific sales data
- Smoothed ASP buckets
- Monthly price-bucket trend pivots
- Auto-generated archetype mappings
- Archetype keys and price ranges
- Validation summaries against mapped reference buckets
- Analytical base tables enriched with archetype labels
- Monthly archetype rollups for Excel pivots, dashboards, or forecasting models
- Diagnostic charts and CSVs for reviewing segment behavior

Example generated outputs live under [`notebooks/data/outputs`](notebooks/data/outputs).

## Pipeline Overview

```text
Raw Excel data
  -> 01_exploration.ipynb
     Clean strings, filter years/channel, create sale_date

  -> 02_asp_bucketing.ipynb
     Aggregate sales, calculate ASP, smooth ASP, assign fine price buckets

  -> 03_trend_pivot.ipynb
     Build monthly sales-share matrices per Division x Portal x Size segment

  -> 04_clustering.ipynb
     Cluster adjacent price buckets by demand-trend similarity

  -> 05_archetype_keys.ipynb
     Build and verify business-readable archetype keys

  -> 06_validation.ipynb
     Compare generated archetypes with mapped validation buckets

  -> 07_analytical_base_table.ipynb
     Join archetypes back to transaction-level data and monthly rollups
```

## Core Methodology

The engine is built around a practical demand-planning idea: nearby price points should belong together only when they behave similarly over time.

Key techniques:

- **ASP smoothing:** uses a rolling median to reduce promotion and month-level pricing noise.
- **Fine bucketing:** maps ASP into standard price buckets, usually in 100-unit intervals.
- **Tail bucketing:** uses wider 500-unit buckets for sparse high-price ranges in EC.
- **Monthly share pivots:** represents each price bucket by its monthly percentage contribution to segment volume.
- **Adjacent clustering:** groups only neighboring price buckets, preserving interpretable price ranges.
- **Volume cleanup:** prevents tiny low-volume clusters from becoming noisy standalone archetypes.
- **Validation layer:** compares generated buckets to mapped business references where available.

The shared implementation helpers are in [`src/pipeline.py`](src/pipeline.py) and [`src/clustering.py`](src/clustering.py).

## Repository Structure

```text
.
+-- data/
|   +-- raw/                 # Source Excel workbooks
|   +-- outputs/             # Diagnostics and supporting outputs
+-- notebooks/               # End-to-end notebook pipeline
|   +-- data/outputs/        # Generated channel outputs
+-- src/
|   +-- channel_registry.py  # Channel-specific configuration
|   +-- config.py            # Notebook-facing config exports
|   +-- pipeline.py          # ASP bucket helper
|   +-- clustering.py        # Adjacent clustering helpers
+-- archetype_engine_docs.md
+-- archetype_engine_operational_guide(how to use in detail).md
+-- README.md
```

## Setup

Use Python 3.10 or newer.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install pandas numpy scipy scikit-learn matplotlib seaborn openpyxl jupyter nbconvert
```

On macOS or Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install pandas numpy scipy scikit-learn matplotlib seaborn openpyxl jupyter nbconvert
```

## Running The Pipeline

Open the notebooks from the [`notebooks`](notebooks) directory and run them in order:

1. `01_exploration.ipynb`
2. `02_asp_bucketing.ipynb`
3. `03_trend_pivot.ipynb`
4. `04_clustering.ipynb`
5. `05_archetype_keys (1).ipynb`
6. `06_validation.ipynb`
7. `07_analytical_base_table (2).ipynb`

The notebooks currently set:

```python
os.environ["CHANNEL"] = "EC"
```

Change this to `TT` before importing `config` if you want to run the Traditional Trade pipeline.

Outputs are written to:

```text
notebooks/data/outputs/{CHANNEL}/
```

## Important Outputs

| Output | Purpose |
| --- | --- |
| `01_clean_sales.csv` | Cleaned and filtered channel sales |
| `02_fine_bucket_ts.csv` | Monthly quantity by segment and ASP bucket |
| `03_segment_pivots.pkl` | Trend matrices used for clustering |
| `archetype_mapping.csv` | Fine bucket to New Bucket mapping |
| `archetype_keys.csv` | One row per archetype with price range and volume |
| `06_validation_summary.csv` | Segment-level validation results |
| `06_validation_detail.csv` | Bucket-level validation detail |
| `07_analytical_base_table.csv` | Sales data enriched with archetype labels |
| `07_archetype_monthly.csv` | Monthly rollup by archetype |

## Documentation

For a deeper technical explanation, see:

- [`archetype_engine_docs.md`](archetype_engine_docs.md) for algorithm and architecture details
- [`archetype_engine_operational_guide(how to use in detail).md`](archetype_engine_operational_guide%28how%20to%20use%20in%20detail%29.md) for operational usage notes
- [`Archetype_Engine_Project_Report.docx`](Archetype_Engine_Project_Report.docx) for project-report format documentation

## Current Status

This is a strong notebook-first analytics project with real data, reproducible intermediate outputs, validation artifacts, and reusable source modules. The most useful next engineering step would be to package the notebook flow behind a single CLI runner and add MT to `channel_registry.py`, so all three included channels can be executed consistently from one command.
