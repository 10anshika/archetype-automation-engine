# 🎬 Archetype Automation Engine
## *The Algorithm That Left No Crumbs* 🍽️

> **Watch 295K sales records transform into the sickest price archetypes ever** 👀

---

## 🎯 The Instant Pitch

You have **295,000+ sales transactions** scattered across channels, seasons, and price points. Traditional forecasting breaks because price points dance independently. 

**This engine doesn't dance alone.** It discovers which price points **move together** over time—patterns humans miss in Excel.

### The Magic 🪄
- **Input:** Raw chaotic sales data from 7 portals, 3 channels, 5 divisions
- **Process:** AI-driven clustering + demand similarity analysis
- **Output:** Stable, interpretable price archetypes for forecasting that actually works

**Result?** Demand forecasts jump from guesswork to data-backed precision. 📈

---

## 🚀 Why Recruiters Should Care

This isn't a homework project. This is:

| 🎯 | What Makes It Production-Grade |
|----|-------------------------------|
| **Real Scale** | 295K+ records, not toy data |
| **Multi-channel** | E-Commerce, Traditional Trade, Multi-channel handling |
| **Reproducible** | From raw Excel → validation → outputs, fully documented |
| **Validated** | Built-in comparison against business reference mappings |
| **Reusable** | Modular pipeline; swap channels/parameters without rebuilding |
| **Battle-tested** | Covers 5 divisions, 8 size categories, 3 years of history |

**This solves a real billion-dollar problem:** How do you forecast when your product portfolio is constantly repricing and seasonality is chaotic?

---

## 💡 The Core Insight

**Traditional approach:** "Price point $49 usually sells Y units."  
❌ *Breaks when $49 reprices or seasonality shifts*

**This approach:** "Price points $48-$52 *move as a cluster* with similar monthly share patterns."  
✅ *Stable through repricing, seasonality, channels, and time*

**How it works in 3 steps:**
1. 📊 **Smooth out noise** → Rolling median on ASP to kill promotions
2. 🔗 **Find demand twins** → Cluster adjacent prices by monthly behavior similarity
3. 🎯 **Build archetypes** → Create stable price bands that forecast together

---

## 📊 The Numbers

### Dataset Snapshot
```
E-Commerce:        127K records  |  7 portals   |  93 segment combos
Traditional Trade:  61K records  |  1 portal    |  14 segment combos  
Multi-channel:     106K records  |  4 portals   |  51 segment combos
─────────────────────────────────────────────────────────────────
Total:            295K records  | 12 portals   | 158 segments
Coverage:         2023-2025 (3 years of history)
```

### Divisions Covered
```
HL (Hard Luggage)  |  SL (Soft Luggage)  |  BP (Backpack)
BS (Bags/Scroll)   |  DF (Day Packs & Frames)
```

### Output Power
The engine delivers **9 critical outputs** ready for:
- 📈 Demand forecasting models
- 📊 Executive dashboards
- 💼 Revenue optimization
- 🎯 Inventory planning

---

## 🏗️ The Pipeline (7 Steps)

```
Step 1: 🔍 EXPLORE
└─ Ingest messy Excel, standardize dates, filter channels

        ↓

Step 2: 💰 ASP BUCKETING  
└─ Calculate Average Selling Price, smooth with rolling median,
   create fine-grained price buckets (±100 units)

        ↓

Step 3: 📈 TREND PIVOT
└─ Build monthly sales-share matrices
   (Who bought what, when? By segment.)

        ↓

Step 4: 🤖 CLUSTERING
└─ Find adjacent price buckets with similar demand patterns
   (Price twins that move together)

        ↓

Step 5: 🏷️ ARCHETYPE KEYS
└─ Build human-readable archetype definitions
   (Budget, Mid-range, Premium, etc.)

        ↓

Step 6: ✅ VALIDATION
└─ Compare AI archetypes vs. human-mapped reference data
   (Proof it works, not just theory)

        ↓

Step 7: 📊 ANALYTICAL BASE TABLE
└─ Tag all 295K transactions with archetypes + create rollups
   (Ready for BI dashboards, forecasting models, SQL queries)
```

---

## 🧠 The Techniques That Impress

| Technique | Why It Matters |
|-----------|----------------|
| **Rolling Median Smoothing** | Strips promotion noise while preserving real trends |
| **Adjacent-Only Clustering** | Clusters $48-$52 together, not $12 and $199 (keeps it sane) |
| **Monthly Share Encoding** | Captures *behavior*, not just price; $100 in Jan ≠ $100 in Dec |
| **Volume Cleanup** | Kills tiny edge-case clusters that break real forecasting |
| **Cross-validation** | Compares to manual business mappings (proves it's right) |

---

## 📦 Repository Structure

```
archetype-automation-engine/
├── 📂 data/raw/                    ← 295K sales records (3 Excel files)
│   ├── ec_data.xlsx                (127K rows, 7 portals)
│   ├── manual_validation.xlsx      (61K rows, 1 portal)
│   └── mt_data.xlsx                (106K rows, 4 portals)
│
├── 📂 notebooks/                   ← The 7-step pipeline (Jupyter)
│   ├── 01_exploration.ipynb
│   ├── 02_asp_bucketing.ipynb
│   ├── 03_trend_pivot.ipynb
│   ├── 04_clustering.ipynb
│   ├── 05_archetype_keys.ipynb
│   ├── 06_validation.ipynb
│   └── 07_analytical_base_table.ipynb
│
├── 📂 src/                         ← Reusable pipeline logic
│   ├── pipeline.py                 (ASP & bucketing helpers)
│   ├── clustering.py               (Adjacent clustering algorithm)
│   ├── channel_registry.py         (Channel configs)
│   └── config.py                   (Runtime configuration)
│
└── 📚 Documentation
    ├── archetype_engine_docs.md    (Deep technical dive)
    ├── archetype_engine_operational_guide.md
    └── Archetype_Engine_Project_Report.docx
```

---

## 🎯 What You Get

### 9 Production Outputs

| Output | Use Case |
|--------|----------|
| `01_clean_sales.csv` | 🏁 Your clean dataset (baseline) |
| `02_fine_bucket_ts.csv` | 📈 Price bucket trends over time |
| `03_segment_pivots.pkl` | 🔗 Behavior matrices (clustering input) |
| `archetype_mapping.csv` | 🎫 The core mapping: *Price → Archetype* |
| `archetype_keys.csv` | 🏷️ Archetype definitions (Budget, Mid, Premium, etc.) |
| `06_validation_summary.csv` | ✅ How well archetypes match business reality |
| `06_validation_detail.csv` | 🔍 Segment-by-segment accuracy breakdown |
| `07_analytical_base_table.csv` | 💾 All 295K transactions + archetype labels (ready for analysis) |
| `07_archetype_monthly.csv` | 📊 Monthly rollup by archetype (dashboard-ready) |

---

## 🚀 Quick Start

### 1️⃣ Setup (2 min)
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install pandas numpy scipy scikit-learn matplotlib seaborn openpyxl jupyter
```

### 2️⃣ Run (5 min per notebook)
```python
# In notebook 01_exploration.ipynb:
os.environ["CHANNEL"] = "EC"  # or "TT"
# Then run all 7 notebooks in order
```

### 3️⃣ Outputs appear in:
```
notebooks/data/outputs/EC/   # (or TT/)
```

---

## 💪 Why This Project Stands Out

✅ **Not theoretical.** Solves a real forecasting problem at scale.  
✅ **Not toy code.** Real data, real validation, real outputs.  
✅ **Not one-off.** Modular design lets you add channels/years/segments.  
✅ **Not a black box.** Every step is logged, documented, and debuggable.  
✅ **Not overfitted.** Validated against business reference mappings.  

---

## 📚 Deep Dives

Want to understand the algorithm, architecture, or operations?

- **[Technical Deep Dive](archetype_engine_docs.md)** — How clustering & archetypes work
- **[Operational Guide](archetype_engine_operational_guide%28how%20to%20use%20in%20detail%29.md)** — How to run & extend it
- **[Project Report](Archetype_Engine_Project_Report.docx)** — Full MBA-style writeup

---

## 🔥 The Bottom Line

**Most price forecasting fails because it treats price points independently.**

This engine treats them as *networks*—discovering which prices move together, why, and how to predict them as stable groups.

**For a $100M+ luggage/backpack business:** This is the difference between inventory stockouts (lost sales) and overstock (dead margin). 📊💰

---

<div align="center">

**Built with precision and passion.**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange?style=for-the-badge&logo=jupyter&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-Data-green?style=for-the-badge&logo=pandas&logoColor=white)
![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-ML-brightgreen?style=for-the-badge&logo=scikit-learn&logoColor=white)

</div>

---

*Archetype Automation Engine © 2024 | [Anshika](https://github.com/10anshika)*
