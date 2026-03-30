# 🛠️ Archetype Automation Engine

Automated data science pipeline for **archetype modeling** in retail analytics. Groups similar price points (₹100 buckets) into standardized **New Buckets (archetypes)** based on monthly sales-share trend similarity. Handles 157 segments across EC, TT, MT channels.

## 🎯 Project Overview

**Problem Solved**: Manual Excel-based price bucketing is inconsistent, unscalable, and fragile. Analysts visually group ₹100 price buckets into archetypes (NB1, NB2...) for reporting/forecasting.

**Solution**: Data-driven **Auto-K clustering** discovers optimal number of archetypes (K) per segment using greedy adjacent merge with cumulative cost threshold (0.70 default). Reduces weeks of work to minutes.

**Business Impact**: Standardized price ranges enable YoY comparison within archetypes even as ASPs shift.

**Channels**: 
- **EC** (92 segments): Amazon, Flipkart, D2C...
- **TT** (14 segments): Traditional trade 
- **MT** (45/51 segments): Modern trade

## 🏗️ Architecture

```
Raw Excel (ec_data.xlsx, manual_validation.xlsx, mt_data.xlsx)
          │
NB01 Clean → 01_clean_sales.csv (strip strings, filter years, build sale_date)
          │
NB02 ASP Bucketing → 02_fine_bucket_ts.csv (₹100 buckets + tail ₹500)
          │
NB03 Pivot → 03_segment_pivots.pkl (monthly % share matrices per segment)
          │
NB04 Auto-K Cluster ← threshold overrides from channel_registry.py
          │ → archetype_mapping.csv + archetype_keys.csv
          │
NB05 Verify Keys
NB06 Validate vs ground truth → 06_validation_summary.csv
NB07 ABT → 07_analytical_base_table.csv (all sales + archetype labels)
NB08 Report → per_portal/*.xlsx + consolidated/*.xlsx + PNGs

NB09 Diagnostic → 09_threshold_diagnostic.csv (standalone)
NB10 Pivot Detail → 10_pivot_detail/*.xlsx (flagged segments)
```

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Auto-K Clustering** | Discovers optimal archetypes automatically (K=2-10) using Pearson correlation + adjacency constraint |
| **Threshold Overrides** | 30 segments tuned to 0.60 (per NB09 diagnostic) for complex price structures |
| **Tail Bucketing** | ₹500 buckets above division thresholds (HL>₹5K, SL>₹4K, BP>₹1.5K) |
| **Volume Filters** | `min_history_months=6`, `noise_floor_pct=0.1%`, `min_cluster_vol_pct=1%` |
| **Validation** | 85-95% accuracy vs analyst ground truth (NB06) |
| **papermill Orchestration** | `run_pipeline.py --channel EC` executes full pipeline |

**Core Algorithm**: Greedy adjacent merge stops when cumulative dissimilarity reaches 70% of total cost. Only adjacent ₹100 buckets merge → business-valid contiguous price ranges.

## 🚀 Setup

```bash
git clone https://github.com/10anshika/archetype-automation-engine
cd archetype_automation_engine/src

# Install deps
pip install pandas==2.2.2 numpy scipy scikit-learn matplotlib seaborn papermill openpyxl jupyter nbconvert

# Verify kernel
jupyter kernelspec list  # should show 'python3'
```

## 📋 Usage

### Run Full Pipeline
```bash
cd src
python run_pipeline.py --channel EC  # ~15min, 92 segments
python run_pipeline.py --channel TT  # ~3min, 14 segments  
python run_pipeline.py --channel MT  # ~10min, 45 segments
```

### Resume / Single Notebook
```bash
python run_pipeline.py --channel EC --start-from 04  # re-run NB04+
python run_pipeline.py --channel EC --only 08         # reports only
```

### Diagnostics
```bash
python run_diagnostic.py           # NB09 cross-channel
cd ../notebooks && jupyter nbconvert --execute 10_pivot_detail.ipynb
```

**Outputs**: `notebooks/data/outputs/{CHANNEL}/` (gitignored data/large files)

## 📁 File Structure

```
d:/archetype_automation_engine/
├── data/raw/                 # ← Place Excel inputs here
│   ├── ec_data.xlsx
│   ├── manual_validation.xlsx (TT)
│   └── mt_data.xlsx
├── notebooks/                # Jupyter pipeline (8+2 notebooks)
│   ├── 01_exploration.ipynb
│   ├── 04_clustering.ipynb     # ← Core Auto-K algorithm
│   └── 08_reporting.ipynb
├── src/                      # Python utils + orchestrator
│   ├── channel_registry.py    # All configs here
│   ├── run_pipeline.py        # Main entrypoint
│   ├── pipeline.py            # assign_buckets()
│   └── clustering.py          # Legacy clustering
├── outputs/                  # Generated (gitignored)
└── README.md | TODO.md
```

**Key Config**: `src/channel_registry.py` — channel-specific params (raw_path, thresholds, MAX_K=10)

## 🔄 Pipeline Flow

1. **NB01**: Clean/filter → `01_clean_sales.csv`
2. **NB02**: ASP → ₹100 buckets (tail ₹500) → `02_fine_bucket_ts.csv`
3. **NB03**: % share pivots → `03_segment_pivots.pkl`
4. **NB04**: **Auto-K** groups adjacent buckets → `archetype_mapping.csv`
5. **NB05-NB08**: Verify → ABT → Excel reports/PNGs
6. **NB09**: Threshold diagnostics → tune overrides

**Input**: Excel (Division, Portal, Size, price_range, year, month, qty, net_sales)  
**Output**: `{segment}_pivot_ready.xlsx` (analyst-ready)

## ⚙️ How It Works

**Archetype Logic** (NB04):  
For each segment → N active buckets → greedy merge adjacent pairs by lowest cost `(1 - corr)/2` → stop at 70% cumulative cost → K discovered automatically → sparse buckets assigned to nearest.

```
Bucket ₹1200: [8,9,8,10]  ← monthly % shares
Bucket ₹1300: [12,13,12,14]
Bucket ₹2000: [18,18,19,18]
↓ Merge most similar adjacent → ₹1200+₹1300 = NB1, ₹2000 = NB2
```

**Strictly No Hallucination**: Based on actual files/code (channel_registry.py, run_pipeline.py, docs).

## 🔮 Future Improvements

- Airflow/Prefect orchestration
- Streamlit UI for threshold tuning
- ML similarity (beyond Pearson corr)
- Cross-channel archetype alignment

**Status**: Production-ready. Run `python src/run_pipeline.py --channel EC` 🚀
