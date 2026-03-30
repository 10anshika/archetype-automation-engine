# Archetype Engine — Complete Technical Documentation

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [End-to-End Pipeline Architecture](#2-end-to-end-pipeline-architecture)
3. [Data Layer](#3-data-layer)
4. [Feature Engineering](#4-feature-engineering)
5. [Segment Pivot Construction (NB03)](#5-segment-pivot-construction-nb03)
6. [Core Algorithm — Auto-K Clustering (NB04 + clustering.py)](#6-core-algorithm--auto-k-clustering-nb04--clusteringpy)
7. [Threshold Override System](#7-threshold-override-system)
8. [Archetype Mapping and Keys (NB05)](#8-archetype-mapping-and-keys-nb05)
9. [Validation Layer (NB06)](#9-validation-layer-nb06)
10. [Analytical Base Table (NB07)](#10-analytical-base-table-nb07)
11. [Reporting Layer (NB08)](#11-reporting-layer-nb08)
12. [Diagnostic and Debug Layer](#12-diagnostic-and-debug-layer)
13. [Source Code Breakdown (src/)](#13-source-code-breakdown-src)
14. [Configuration System](#14-configuration-system)
15. [Execution Guide](#15-execution-guide)
16. [Failure Modes and Debugging](#16-failure-modes-and-debugging)
17. [Design Decisions and Tradeoffs](#17-design-decisions-and-tradeoffs)
18. [Extension Opportunities](#18-extension-opportunities)
19. [Glossary](#19-glossary)

---

## 1. System Overview

### What Problem It Solves

Retail analysts working in the luggage and accessories business needed to group similar price points into standard "archetypes" — clusters of ₹100 price buckets that exhibit similar monthly sales-share trends over time. These archetypes define the price range taxonomy used across all downstream reporting, forecasting, and commercial analysis.

Before this system existed, analysts manually assigned products to these archetypes in Excel. This involved visually inspecting month-over-month sales distributions, drawing grouping lines, and recording results in spreadsheets. The manual process suffered from three systemic failures:

**Inconsistency**: Different analysts produced different groupings for the same segment depending on judgment and experience. No two runs of the same data produced the same output, making year-over-year comparison meaningless.

**Inability to scale**: With 157 segments across three channels (TT, EC, MT) and each segment requiring hours of manual effort, the full analysis took weeks and still left many segments under-analyzed.

**Fragility**: Any change in the underlying sales data — a new price point, a new portal, a new fiscal year — required the entire analysis to be re-run from scratch manually.

The Archetype Engine automates the entire workflow using data-driven clustering, reducing the full pipeline from weeks of manual work to a single command that runs in minutes.

### Business Impact of Automation

The system generates standardized archetype definitions (called New Buckets, labeled NB1, NB2, NB3, etc.) for every segment, which are then used as the standard price range labels in all downstream analysis. Once the engine runs, every sales data point in the system is enriched with its New Bucket label. This enables direct year-over-year comparison within the same price range, even as actual prices shift.

### Key Definitions

**Segment**: The fundamental unit of analysis. A segment is the unique combination of Division × Portal × Size. Examples: `HL_Flipkart_LARGE` (Hardluggage, Flipkart portal, Large size), `BP_Others_Single` (Backpack, Others portal, Single SKU). There are 157 segments total across the three channels: 14 in TT, 92 in EC, and 51 in MT (45 of which pass the minimum volume threshold for analysis).

**Price Bucket (Fine Bucket)**: A ₹100-wide price interval defined by its lower boundary. A product with Average Selling Price of ₹1,847 maps to bucket 1800 (floor(1847/100)×100). For high-price divisions, buckets widen to ₹500 above a division-specific threshold (e.g., ₹5,000 for HL). Fine buckets are the input to clustering.

**Archetype / New Bucket**: A group of adjacent fine buckets that share similar monthly sales-share trend patterns. The output of clustering. Labeled NB1, NB2, ..., NBK in ascending price order. Each New Bucket gets an `archetype_key` string identifier (format varies by channel, e.g., `AmazonHL_LARGE3` for EC, `HLTT18_CABIN` for TT). New Buckets are the standard price range definitions used in all downstream reporting.

---

## 2. End-to-End Pipeline Architecture

### Pipeline Flow

```
Raw Excel Files (ec_data.xlsx / mt_data.xlsx / manual_validation.xlsx)
        │
        ▼
NB01 — Exploration & Cleaning
        │  01_clean_sales.csv
        ▼
NB02 — ASP Bucketing
        │  02_fine_bucket_ts.csv
        ▼
NB03 — Trend Pivot Construction
        │  03_segment_pivots.pkl
        ▼
NB04 — Auto-K Clustering        ← reads segment_threshold_overrides from channel_registry.py
        │  archetype_mapping.csv
        │  archetype_keys.csv
        ▼
NB05 — Archetype Keys Verification
        │  archetype_keys.csv (verified)
        ▼
NB06 — Validation
        │  06_validation_summary.csv
        │  06_validation_detail.csv
        ▼
NB07 — Analytical Base Table
        │  07_analytical_base_table.csv
        │  07_archetype_monthly.csv
        ▼
NB08 — Reporting
        │  per_portal/{segment}_pivot_ready.xlsx
        │  consolidated/{Division}_{Size}_pivot_ready.xlsx

(Standalone — run separately)
NB09 — Threshold Diagnostic  →  09_threshold_diagnostic.csv + charts
NB10 — Pivot Detail          →  10_pivot_detail/{segment}_pivot_detail.xlsx
```

### Input → Output Mapping

| Notebook | Primary Inputs | Primary Outputs |
|----------|---------------|-----------------|
| NB01 | Raw Excel (channel-specific) | `01_clean_sales.csv` |
| NB02 | `01_clean_sales.csv` | `02_fine_bucket_ts.csv` |
| NB03 | `02_fine_bucket_ts.csv` | `03_segment_pivots.pkl` |
| NB04 | `03_segment_pivots.pkl`, `02_fine_bucket_ts.csv`, `channel_registry.py` | `archetype_mapping.csv`, `archetype_keys.csv` |
| NB05 | `archetype_mapping.csv`, `archetype_keys.csv` | `archetype_keys.csv` (verified) |
| NB06 | `archetype_mapping.csv`, raw Excel (validation sheet) | `06_validation_summary.csv`, `06_validation_detail.csv` |
| NB07 | `01_clean_sales.csv`, `archetype_mapping.csv`, `03_segment_pivots.pkl` | `07_analytical_base_table.csv`, `07_archetype_monthly.csv` |
| NB08 | `07_analytical_base_table.csv`, `07_archetype_monthly.csv` | `per_portal/*`, `consolidated/*` |
| NB09 | `03_segment_pivots.pkl`, `02_fine_bucket_ts.csv` (all channels) | `09_threshold_diagnostic.csv`, PNG charts |
| NB10 | `09_threshold_diagnostic.csv`, `03_segment_pivots.pkl`, `07_analytical_base_table.csv` | `10_pivot_detail/{seg}_pivot_detail.xlsx`, `10_master_nb_summary.csv` |

### Channel Configuration

| Channel | Full Name | Portals | Raw File | Sheet | Segments |
|---------|-----------|---------|----------|-------|----------|
| TT | Traditional Trade | Integer IDs (1, 2, 3...) | `manual_validation.xlsx` | `raw` | 14 |
| EC | E-Commerce | Amazon, Flipkart, D2C, Myntra, Blinkit, MP, Others | `ec_data.xlsx` | `Sheet1` | 92 |
| MT | Modern Trade | Dmart, Others, Reliance, Vishal | `mt_data.xlsx` | `raw` | 51 (45 pass min volume) |

---

## 3. Data Layer

### 3.1 Raw Data

#### TT Channel — `manual_validation.xlsx` (sheet: `raw`)

Contains transaction-level or aggregated sales data for Traditional Trade. Key columns include:

- `Division` — product division (HL, SL, BP, BS, DF)
- `Portal` — integer portal identifier (1 = TT)
- `Size` — product size category (CABIN, LARGE, MEDIUM, SO2, SO3, Single, DF, DFT)
- `Masked Range` — the range column used for ASP computation (renamed via `RANGE_COL` config)
- `Final Channel` — channel label used to filter rows to TT only
- `year`, `month` — time period
- `qty` — units sold
- `net_sales` — revenue in ₹

Also contains a second sheet `Bucket_map` used as ground truth for NB06 validation, with columns `New Bucket`, `min`, `key_2`.

#### EC Channel — `ec_data.xlsx` (sheet: `Sheet1`)

Structured similarly to TT but with string portal identifiers. The range column here is named `Range`. Also contains a `Bucket_mapped` sheet for validation with columns `New Bucket`, `ASP_bucket`, `key`.

#### MT Channel — `mt_data.xlsx` (sheet: `raw`)

Same structure as EC but the range column is `Range_mask`. Validation sheet is `Bucket_mapped`.

#### Common columns present in all raw files

`Division`, `Portal`, `Size`, `year`, `month`, `qty`, `net_sales`, the channel-specific range column, and `Final Channel`.

**Known data quality issues handled by the pipeline:**

- Trailing whitespace in string columns like `Size` creates phantom segments. For example, `'SO3 '` and `'SO3'` appear as two different values. NB01 strips all string columns.
- The year 2023 is excluded from all analysis via `ignore_years` configuration. This is a business decision — 2023 data is treated as pre-baseline.
- Rows with `qty <= 0` or `net_sales <= 0` may exist and are implicitly excluded during aggregation.

### 3.2 Cleaning Logic (NB01)

NB01 performs the following transformations in sequence:

**Step 1 — Load raw file.** Reads the Excel file at `RAW_PATH` using the sheet name `RAW_SHEET` from config. Uses `pd.read_excel`.

**Step 2 — Strip string columns.** Every string column (`Division`, `Size`, `Final Channel`, and the `RANGE_COL`) is stripped of whitespace using `.str.strip()`. This eliminates phantom segments caused by trailing spaces.

**Step 3 — Apply year filter.** Rows where `year` is in `IGNORE_YEARS` (default: [2023]) are dropped.

**Step 4 — Apply channel filter.** Rows where `Final Channel != CHANNEL` are dropped. This keeps only the rows relevant to the current run (EC, TT, or MT).

**Step 5 — Build `sale_date`.** A proper datetime column is constructed from `year`, `month`, `day=1` using `pd.to_datetime(dict(year=..., month=..., day=1))`. This standardizes all records to the first day of their month.

**Step 6 — Save.** The cleaned dataframe is written to `{OUT_PATH}/01_clean_sales.csv`.

Output columns: `Division`, `Portal`, `Size`, `sale_date`, `year`, `month`, `qty`, `net_sales`, plus `Final Channel` and the range column. Row count is typically 40,000–80,000 depending on channel.

---

## 4. Feature Engineering

### 4.1 ASP Bucketing (NB02)

NB02 takes the cleaned sales data and produces a time series of quantities at the ₹100 price-bucket level per segment per month.

**Step 1 — Aggregate to range-month level.** The raw data (which has one row per transaction or sub-period) is grouped by `Division`, `Portal`, `Size`, `sale_date`, and `RANGE_COL`. Within each group, `qty` and `net_sales` are summed. This collapses all transactions within a price range in a given month to a single row.

**Step 2 — Compute raw ASP.** Average Selling Price = `net_sales / qty` at the range-month level.

**Step 3 — Smooth ASP.** A rolling 3-month median ASP (`ROLLING_MEDIAN_MONTHS = 3`) is computed per unique `Division × Portal × Size × RANGE_COL` group. This uses `min_periods=1` so early months use whatever data is available. Smoothing reduces month-to-month noise in price positioning caused by promotions or mix shifts.

**Step 4 — Assign to buckets.** The `assign_buckets()` function in `pipeline.py` maps each smoothed ASP to a bucket:

```python
def assign_buckets(asp, division, cfg_dict):
    tail_switch = cfg_dict.get('tail_switch_price', {})
    bucket_width_tail = cfg_dict.get('bucket_width_tail', None)
    bucket_width = cfg_dict.get('bucket_width', 100)  # default ₹100

    if (bucket_width_tail is not None
            and division in tail_switch
            and asp >= tail_switch[division]):
        width = bucket_width_tail  # ₹500 for high-price tail
    else:
        width = bucket_width       # ₹100 standard

    return int((asp // width) * width)
```

For EC and MT channels, once ASP exceeds the `tail_switch_price` for a division (e.g., ₹5,000 for HL, ₹4,000 for SL, ₹1,500 for BP/BS/DF), the bucket width expands to ₹500. This prevents the creation of dozens of sparsely-populated ₹100 buckets in the luxury price segment where sales volumes are thin.

**Why ₹100 buckets?** The business uses ₹100 as the natural pricing granularity — products are typically priced at round hundreds (₹999 rounds to ₹900, ₹2,499 rounds to ₹2,400, etc.). At this granularity there are typically 20–80 distinct price buckets per segment, enough resolution to detect meaningful price clusters without excessive sparsity.

**Step 5 — Aggregate to segment × month × bucket.** Group by `Division`, `Portal`, `Size`, `sale_date`, `bucket_min`, `ASP_bucket`. Sum `qty`. The result is the "fine bucket time series": one row per segment per month per price bucket.

Output `02_fine_bucket_ts.csv` columns: `Division`, `Portal`, `Size`, `sale_date`, `bucket_min`, `ASP_bucket`, `qty`.

### 4.2 Time Series Construction

From the fine bucket time series, each segment can be represented as a matrix where rows are price buckets and columns are months. The value at position (bucket, month) is the number of units sold at that price bucket in that month.

NB03 creates this as a Cartesian product — every combination of bucket × month that exists in the data — and fills any missing combinations with zero. This ensures the matrix is rectangular and has no gaps, which is required for correlation-based similarity computation.

**Handling missing months:** The Cartesian product uses only months that actually appear in the data for that segment. If a segment has no sales in a given month, that month simply doesn't exist in the data, so the pivot has fewer columns. The algorithm handles segments with varying numbers of months through the `min_history_months` filter.

---

## 5. Segment Pivot Construction (NB03)

NB03 takes the fine bucket time series and builds a per-segment pivot matrix representing each price bucket's monthly share of total segment sales.

**Step 1 — Build Cartesian grid.** For each segment (Division × Portal × Size combination), create all combinations of `bucket_min × sale_date`. Fill any missing (bucket, month) combination with `qty = 0`.

**Step 2 — Compute monthly share.** For each month, compute the total qty sold across all buckets in the segment. Then divide each bucket's qty by that month's total. Multiply by 100 to get percentage.

```python
grid['pct_share'] = np.where(
    grid['month_total'] > 0,
    (grid['qty'] / grid['month_total'] * 100).round(4),
    0
)
```

**Step 3 — Pivot.** Reshape the data so that rows = `bucket_min` (ascending price), columns = `sale_date` (chronological months), values = `pct_share`.

**Why share instead of raw values?** Volume trends in absolute terms reflect both category growth and price-point popularity. By converting to share, the algorithm captures the relative importance of a price bucket within its segment, normalized for overall sales growth. Two buckets that both grew 20% year-over-year but whose share of monthly sales follows the same seasonal pattern are correctly identified as similar, even though their absolute volumes differ. This is the correct signal for archetype definition — archetypes represent structural price segments, not absolute volume levels.

**Example pivot matrix** (illustrative, HL/CABIN segment, 3 buckets, 4 months):

| bucket_min | 2024-01 | 2024-02 | 2024-03 | 2024-04 |
|------------|---------|---------|---------|---------|
| 1200 | 8.3 | 9.1 | 7.8 | 10.2 |
| 1300 | 12.4 | 13.0 | 11.9 | 14.1 |
| 1500 | 6.7 | 5.8 | 7.2 | 6.1 |
| 2000 | 18.2 | 17.6 | 19.4 | 17.8 |
| 2100 | 19.0 | 18.2 | 20.1 | 18.5 |

Columns sum to approximately 100% (the segment total). Buckets ₹2000 and ₹2100 show very similar month-to-month movement — they are good candidates to merge into a single archetype.

**Step 4 — Save.** The dictionary of pivot matrices (one per segment) is serialized to `03_segment_pivots.pkl` using Python `pickle`. Each entry stores the pivot DataFrame plus segment metadata (`div`, `portal`, `size`).

---

## 6. Core Algorithm — Auto-K Clustering (NB04 + clustering.py)

This is the most important section. The Auto-K algorithm determines how many archetypes (K) to create for each segment, and which fine buckets belong to each archetype.

### 6.1 Mathematical Problem Definition

Given a segment with N active price buckets, each with a T-length time series of monthly percentage shares, find a partition of the N buckets into K contiguous groups such that:

1. **Adjacency**: Only adjacent buckets (in price order) may be grouped together. NB4 must equal {₹2000–₹2200} or {₹1800–₹2200}, never {₹1800, ₹2200} with ₹2000 in a different group.

2. **Similarity**: Buckets within a group should have similar time series trends (high Pearson correlation between their monthly share vectors).

3. **Minimum volume**: No archetype may contain less than `min_cluster_vol_pct` (1–3%) of total segment volume.

4. **K bound**: The number of groups K must be at least 2 and at most `MAX_K` (8 for TT, 10 for EC/MT).

5. **Interpretability**: K is determined automatically from the data — no manual input required.

### 6.2 What Is Being Clustered

Each price bucket is represented as a vector of T values, where T is the number of months in the data. The value at position t is the bucket's percentage share of total segment sales in month t. Two buckets with identical share patterns across all months have Pearson correlation = 1.0. Two buckets whose share patterns are perfectly anticorrelated (one goes up when the other goes down) have Pearson correlation = −1.0.

**Why adjacency constraint?** Retail price archetypes must be contiguous price ranges. A customer segment buying ₹1,000–₹1,200 luggage is a conceptually different customer from one buying ₹2,000+ luggage. Mixing non-adjacent buckets into one archetype would create nonsensical price ranges like "₹800–₹900 and ₹1,500–₹1,600" that analysts cannot use. The constraint also prevents the algorithm from jumping over price points to match distant but correlated buckets.

**Why Pearson correlation?** Pearson measures the similarity of trend shapes, not absolute levels. Two buckets that both spike in October (festival season) and dip in June are highly correlated regardless of whether one is 3× larger than the other. This is the correct similarity measure for defining archetypes — the question is whether they behave seasonally the same way, not whether they have the same absolute volume.

### 6.3 Step-by-Step Algorithm

The production algorithm is the `cluster_segment_auto` function defined in NB04 (Cell 26) and mirrors the logic in `clustering.py`. Here is the complete step-by-step breakdown:

**Step 1 — Active bucket filtering.**

Not all price buckets that ever appeared in the data are useful for clustering. Two filters are applied:

- `min_history_months`: A bucket must have at least this many months with non-zero sales to be considered active. Default is 3 for TT, 6 for EC/MT. Buckets appearing in fewer months are considered too sparse to establish a reliable trend.
- `noise_floor_pct`: A bucket's total historical volume must represent at least `NOISE_FLOOR_PCT` (0.1%) of the segment's total volume. This eliminates single-unit outliers from distorting trend calculations.

Any bucket that passes both filters is called an "active bucket". All others are "sparse" or "noise" buckets and will be assigned to the nearest active bucket's archetype after clustering is complete.

**Step 2 — Full greedy adjacent merge (N down to 1).**

Starting with every active bucket as its own group, the algorithm runs the complete merge sequence from K=N groups down to K=1 group. At each step:

a. Compute the merge cost (dissimilarity) between every pair of adjacent groups.
b. Find the pair with the minimum cost (i.e., the most similar adjacent pair).
c. Merge that pair into a single group.
d. Record the cost of this merge in `cost_seq`, and record the current K in `k_seq`.

The merge cost function (`_merge_cost` in NB09 / `merge_cost` in NB04) is:

```python
def merge_cost(pivot, g1, g2):
    s1 = mean_series(pivot, g1)   # mean share vector of group g1
    s2 = mean_series(pivot, g2)   # mean share vector of group g2
    if s1.std() < 1e-9 or s2.std() < 1e-9:
        return 1.0  # flat series → treat as maximally dissimilar
    return (1.0 - float(np.corrcoef(s1, s2)[0, 1])) / 2.0
```

Cost ranges from 0.0 (identical trends, merge freely) to 1.0 (perfectly opposite trends, never merge). The denominator of 2 normalizes the range from [−1, 1] correlation to [0, 1] cost. At each step the cheapest (most similar) adjacent pair is merged first — this is the "greedy" nature of the algorithm.

The result of this phase is two arrays: `cost_seq` (the cost of each merge, in the order they were performed) and `k_seq` (the K value after each merge, in decreasing order from N−1 to 1).

**Step 3 — Threshold-based K selection.**

The key insight of Auto-K: the cumulative sum of merge costs tracks how much "information" has been destroyed by merging. When the cumulative cost crosses a threshold fraction of the total cost, we have merged enough — the remaining un-merged groups are distinctly different from each other.

```python
costs_arr  = np.array(cost_seq)
total_cost = costs_arr.sum()
chosen_k   = 1
if total_cost > 0:
    for i, cs in enumerate(np.cumsum(costs_arr)):
        if cs / total_cost >= seg_threshold:
            chosen_k = k_seq[i + 1]
            break
```

`seg_threshold` defaults to `TREND_SIMILARITY_THRESHOLD = 0.70`. This means: keep merging until 70% of the total merge cost budget has been spent. Stop there — the remaining groups differ enough that merging them would cost more than the 30% budget remaining.

Concretely: if the total cost across all merges is 1.0, stop when the sum of merge costs so far reaches 0.70. The K at that point is `chosen_k`.

**Step 4 — K caps enforcement.**

```python
chosen_k = max(2, min(chosen_k, MAX_K, len(active)))
```

- Minimum of 2: Every segment must have at least 2 archetypes. A single archetype for an entire segment means "all prices are equivalent," which is never useful for business analysis.
- Maximum of `MAX_K`: Caps at 8 for TT, 10 for EC/MT. More archetypes than this creates too many price bands for analysts to track.
- Maximum of `len(active)`: Can't create more groups than there are active buckets.

**Step 5 — Re-run merge stopping at chosen_k.**

With `chosen_k` determined, run the greedy adjacent merge again from scratch, stopping exactly when K groups remain. This produces the actual group assignments.

**Step 6 — Full price coverage.**

The cluster map from Step 5 only covers active buckets. Sparse and noise buckets (those filtered out in Step 1) must still be assigned to an archetype for complete coverage. Each unassigned bucket is assigned to the archetype of its nearest active bucket (by price distance).

```python
for b in range(0, max_b + 100, 100):
    final[b] = nb_map[b] if b in nb_map \
               else nb_map[min(a_sorted, key=lambda x: abs(x - b))]
```

**Step 7 — Renumber.**

Final archetypes are renumbered 1..K in ascending price order. NB1 = cheapest archetype, NBK = most expensive.

### 6.4 Pseudo-Code

```
function cluster_segment_auto(pivot, bucket_ts, seg_threshold):
    
    # Active bucket filter
    seg_vol = sum_volume_per_bucket(bucket_ts)
    active = [b for b in pivot.index
              if active_months(b) >= MIN_HISTORY_MONTHS
              and seg_vol[b] / total_vol >= NOISE_FLOOR_PCT]
    
    if len(active) == 1: return {all_buckets: 1}
    
    # Phase 1: Full merge N→1, record costs
    working = [[b] for b in active]    # N singleton groups
    cost_seq = []
    k_seq = [N]
    
    while len(working) > 1:
        costs = [merge_cost(working[i], working[i+1])
                 for i in range(len(working)-1)]
        best = argmin(costs)           # most similar adjacent pair
        cost_seq.append(costs[best])
        working[best] = working[best] + working[best+1]
        del working[best+1]
        k_seq.append(len(working))
    
    # Phase 2: Find K by cumulative cost threshold
    total_cost = sum(cost_seq)
    chosen_k = 1
    for i, cumcost in enumerate(cumsum(cost_seq)):
        if cumcost / total_cost >= seg_threshold:
            chosen_k = k_seq[i+1]
            break
    chosen_k = clip(chosen_k, 2, min(MAX_K, len(active)))
    
    # Phase 3: Re-merge stopping at chosen_k
    groups = [[b] for b in active]
    while len(groups) > chosen_k:
        costs = [merge_cost(groups[i], groups[i+1])
                 for i in range(len(groups)-1)]
        best = argmin(costs)
        groups[best] = groups[best] + groups[best+1]
        del groups[best+1]
    
    # Phase 4: Assign all price slots (including sparse)
    nb_map = {b: nb for nb, g in enumerate(groups, 1) for b in g}
    for b in range(0, max_bucket+100, 100):
        final[b] = nb_map.get(b) or nb_map[nearest_active(b)]
    
    # Phase 5: Renumber 1..K by ascending price
    return renumber(final)
```

### 6.5 Why Greedy Works Here

The greedy adjacent merge is computationally efficient (O(N²) per merge step) and provably optimal for a specific class of problems. Since only adjacent buckets may merge, the search space at each step is O(N) rather than O(N²/2) for unrestricted clustering. The algorithm mimics exactly what a skilled analyst does when grouping prices by hand: start with the finest granularity, find the two adjacent prices that "look the most similar," and collapse them. Repeat until the result feels right.

**Comparison to K-Means:** K-Means would allow non-adjacent buckets to cluster together, violating the business constraint. K-Means also requires specifying K in advance, while Auto-K discovers K automatically. K-Means is also sensitive to initialization and may converge to different solutions on repeated runs.

**Comparison to Hierarchical Clustering (full linkage):** Standard hierarchical clustering also violates adjacency. A dendrogram-based approach was prototyped in NB04 (Cells 1–15, including the elbow method and silhouette score variants) but was abandoned because it could not reliably enforce contiguity while also passing volume checks. The greedy adjacent merge was the fourth major algorithm iteration and the one that passed all validation checks.

---

## 7. Threshold Override System

### Why the Global Threshold Fails for Some Segments

The default threshold of 0.70 means "stop merging when 70% of total merge cost has been spent." For most segments this produces sensible archetypes. However, some segments have very complex price structures where many similar-but-distinct price clusters exist. For these, the 0.70 threshold stops too early — it leaves too many separate archetypes — or too late — it merges genuinely distinct groups.

The specific failure mode observed: a segment at threshold 0.70 produces K=4 archetypes, but one archetype spans a ₹2,000 price range while 80% of its volume is concentrated in a ₹400 sub-range. This is a sign that the single archetype is actually masking two distinct buying behaviors.

### Diagnostic Logic (NB09)

NB09 runs a stress test across all segments, computing K at three thresholds (0.70, 0.60, 0.50) and flagging segments where a lower threshold would produce meaningfully more archetypes AND where the segment has sufficient volume for the additional detail to matter.

The `peak_concentration` function in NB09 checks, for each archetype produced at threshold 0.70, whether the bucket's volume is unusually concentrated in a narrow sub-range:

```python
def peak_concentration(blist, seg_vol):
    # Find the minimum window of buckets containing 60%+ of archetype volume
    # If that window is < 40% of the total archetype price span,
    # the archetype is "flagged" as potentially under-segmented
```

A segment is flagged (`needs_tuning = True`) if any archetype at threshold 0.70 has a volume concentration where 60%+ of its units fall in less than 40% of its price span.

The flag criterion for override is: `k_diff_60 >= 2 AND total_vol > 10,000`. This means: lowering the threshold to 0.60 would produce at least 2 more archetypes, AND the segment has at least 10,000 units of historical volume (ensuring the additional detail is statistically meaningful).

### How Overrides Alter Clustering Behavior

Overrides are stored in `channel_registry.py` under `segment_threshold_overrides`:

```python
"segment_threshold_overrides": {
    "HL_MP_CABIN": 0.60,
    "HL_Flipkart_LARGE": 0.60,
    ...
}
```

In NB04, before clustering each segment, the override is checked:

```python
seg_thr = cfg.get('segment_threshold_overrides', {}).get(seg_key, None)
fmap = cluster_segment_auto(seg_key, segment_pivots, bucket_ts,
                             threshold_override=seg_thr)
```

If an override exists (0.60), the threshold used in the cumulative cost stopping criterion is 0.60 instead of 0.70. A lower threshold means less total merge cost is tolerated before stopping, resulting in more archetypes (higher K).

### Current Override Summary

| Channel | Segments Overridden | Example Segments |
|---------|--------------------|--------------------|
| TT | 4 | HL_1_SO2, SL_1_SO2, BP_1_Single, SL_1_CABIN |
| EC | 14 | HL_MP_CABIN, HL_Flipkart_LARGE, BP_D2C_Single, SL_MP_Large |
| MT | 12 | HL_Reliance_CABIN, SL_Others_CABIN, BP_Others_Single |
| **Total** | **30** | |

---

## 8. Archetype Mapping and Keys (NB05)

After NB04 runs clustering, two output files are produced and then verified by NB05:

### `archetype_mapping.csv`

Row grain: one row per (Division, Portal, Size, bucket_min). Every fine price bucket in every segment is listed exactly once.

Columns: `Division`, `Portal`, `Size`, `bucket_min`, `bucket_max`, `ASP_bucket` (string like "1200-1299"), `New_Bucket` (integer 1..K), `archetype_key` (string identifier), `total_qty` (total units ever sold in this bucket for this segment).

This file is the join key used by all downstream notebooks to enrich sales data with archetype labels.

### `archetype_keys.csv`

Row grain: one row per (Division, Portal, Size, New_Bucket). Exactly K rows per segment.

Columns: `archetype_key`, `Division`, `Portal`, `Size`, `New_Bucket`, `price_range_min`, `price_range_max`, `total_qty`, `fine_bucket_count`.

This file is the "index" of archetypes — it maps each archetype to its price range, volume, and identifier.

### Why Both Files Are Needed

`archetype_mapping.csv` is needed for data joins (linking individual fine buckets back to archetypes). `archetype_keys.csv` is needed for reporting (one-row-per-archetype summaries, price range lookups). They serve different computational purposes and keeping them separate avoids costly GROUP BY operations on the larger mapping table.

### NB05 Verification Logic

NB05 re-reads both files and performs six checks:

1. **Key format validation**: Reconstructs the expected `archetype_key` from (`Division`, `Portal`, `Size`, `New_Bucket`) using the same `build_key()` function as NB04, and verifies it matches the stored key. Format differs by channel: for TT (integer portals) it's `{div}{abbrev}{portal}{nb}{size}`, for EC/MT (string portals) it's `{portal}{div}{size}{nb}`.

2. **Duplicate key check**: Verifies no two rows in `archetype_keys.csv` share the same `archetype_key`.

3. **Duplicate mapping check**: Verifies no (key, bucket_min) pair appears more than once in `archetype_mapping.csv`.

4. **Segment completeness**: Counts New Buckets per segment and flags any segment with only 1 bucket (sign of clustering failure).

5. **Null check**: Verifies no null values in critical columns.

6. **Save**: Drops the temporary `expected_key` column and re-saves the verified `archetype_keys.csv`.

---

## 9. Validation Layer (NB06)

NB06 compares the engine's archetype assignments against analyst-curated ground truth stored in the raw Excel files.

### Ground Truth Loading

The ground truth sheet (e.g., `Bucket_map` for TT, `Bucket_mapped` for EC/MT) contains the manually-verified New Bucket assignments. The join strategy differs by channel:

- **TT** (`validation_join = 'floor_100'`): Ground truth stores the raw minimum price in `min` column. To align with our `bucket_min`, apply `floor(min/100)*100`.
- **EC/MT** (`validation_join = 'parse_string'`): Ground truth stores `ASP_bucket` as a string like `"1200-1299"`. Extract the left side: `int(str.split('-')[0])`.

Rows with year 2023 are excluded from ground truth (same business rule as the pipeline).

### Checks Performed

After joining our mapping to ground truth on (Division, Portal, Size, bucket_min):

**Row-level accuracy**: For each matched bucket row, check whether `our New_Bucket == gt_New_Bucket`. Report total rows correct and percentage.

**Volume-weighted accuracy**: For matched rows, report what fraction of total historical qty is correctly assigned. A mismatch on a high-volume bucket is more serious than one on a rare bucket.

**Per-segment accuracy**: Break down accuracy by (Division, Portal, Size), reporting `buckets_evaluated`, `buckets_correct`, `pct_correct`, and `qty_correct_pct`.

**Mismatch detail**: For any incorrect assignment, show the segment, bucket_min, our assignment, the ground truth assignment, both archetype keys, and the volume involved.

### Failure Scenarios

**High mismatch count**: Usually caused by a threshold that is too aggressive (over-merges, creating fewer archetypes than ground truth) or too permissive (creates more). The fix is to adjust `segment_threshold_overrides` in `channel_registry.py`.

**Unmatched rows**: Rows where `gt_New_Bucket` is NaN are expected — these are price buckets that appear in our mapping but not in the ground truth (typically low-volume extrapolated buckets at the extreme high end of the price range). The note "extrapolated buckets beyond GT range — expected" applies here.

Outputs: `06_validation_summary.csv` (one row per segment), `06_validation_detail.csv` (one row per matched bucket).

---

## 10. Analytical Base Table (NB07)

NB07 is the enrichment step that joins archetype labels back to all original transaction data, producing a single wide table used by all reporting.

### Join Logic

NB07 reads `01_clean_sales.csv`, `archetype_mapping.csv`, and `03_segment_pivots.pkl`.

**Step 1 — Compute bucket_min for raw sales.** The raw sales data has `net_sales` and `qty`. Compute raw ASP = `net_sales / qty`. Then `bucket_min = floor(ASP / 100) * 100`. This is the same bucketing logic as NB02.

**Step 2 — Join archetype mapping.** Left-join the raw sales to `archetype_mapping` on (`Division`, `Portal`, `Size`, `bucket_min`). This enriches each row with `New_Bucket` and `archetype_key`.

**Step 3 — Handle outliers.** Some raw transactions may have prices higher than any bucket in the mapping (e.g., an extreme ₹8,000 ASP when the mapping only goes to ₹7,000). The `fix_outliers()` function assigns these to the segment's highest-mapped bucket:

```python
def fix_outliers(df, arch, seg_max_bucket):
    unmatched = df['archetype_key'].isna()
    fix = df[unmatched].merge(seg_max_bucket, ...)  # get max bucket per segment
    fix['bucket_min'] = fix['max_bucket_min']
    fix = fix.merge(arch, ...)  # rejoin with corrected bucket
    return concat(df[~unmatched], fix)
```

**Step 4 — Join pct_share.** The NB03 pivot matrices are unpacked into a lookup table of (Division, Portal, Size, bucket_min, sale_date, pct_share). This is left-joined to the ABT, adding each row's `pct_share` (its bucket's monthly share of segment sales).

**Step 5 — Add derived columns.** Year, month, `ASP = net_sales / qty`, `bucket_max = bucket_min + BUCKET_WIDTH - 1`, `row_qty_share = qty / segment_total_qty`.

**Step 6 — Segment monthly totals.** Group by (Division, Portal, Size, sale_date), sum `qty` and `net_sales` to get `segment_total_qty` and `segment_total_sales`. Left-join back to ABT.

### Grain and Column Set

The ABT has one row per original raw transaction (same grain as `01_clean_sales.csv`). Final columns: `Division`, `Portal`, `Size`, `sale_date`, `year`, `month`, RANGE_COL, `bucket_min`, `bucket_max`, `ASP`, `New_Bucket`, `archetype_key`, `pct_share`, `row_qty_share`, `qty`, `net_sales`, `segment_total_qty`, `segment_total_sales`.

NB07 also produces a secondary output `07_archetype_monthly.csv` — an aggregation of the ABT to (Division, Portal, Size, year, month, bucket_min, New_Bucket, archetype_key) grain, summing qty, net_sales, and computing ASP. This is the preferred input for the reporting layer.

### Why the ABT Is Critical

The ABT is the single source of truth for all downstream analysis. By enriching every transaction with its archetype label, it enables any aggregation at the archetype level. The reporting layer (NB08) consumes the ABT without needing to re-derive any labels or joins.

---

## 11. Reporting Layer (NB08)

NB08 reads the ABT and generates structured Excel and CSV reports for analyst consumption.

### Pivot Structure

NB08 produces four types of outputs per segment:

**Summary (`{segment}_summary.csv`)**: One row per New Bucket, containing archetype_key, price_range_min, price_range_max, total_qty, net_sales, ASP, vol_pct, plus per-year breakdowns (`qty_2024`, `qty_2025`, etc.).

**Detail (`{segment}_detail.csv`)**: One row per (New_Bucket, archetype_key, bucket_min, year, month). Granular breakdown showing exactly which fine buckets contribute to each archetype in each period.

**Trend Pivot (`{segment}_trend_pivot.csv`)**: One row per (New_Bucket, archetype_key, month) with year-separated columns: `qty_2024`, `qty_2025`, `net_sales_2024`, `net_sales_2025`, `ASP_2024`, `ASP_2025`, `pct_share_2024`, `pct_share_2025`. This is the format analysts can directly pivot in Excel.

**Pivot Ready (`{segment}_pivot_ready.xlsx`)**: Wide-format Excel file. Rows = New_Bucket. Columns = YYYY-MM date strings. Values = qty. Plus `archetype_key`, `TOTAL_QTY`, `VOL_PCT` columns. This is the primary analyst-facing file.

### Per-Portal vs. Consolidated

**Per-portal** (`per_portal/` folder): One set of files per (Division, Portal, Size) segment. For a segment like `HL_Flipkart_LARGE`, the outputs describe only Flipkart's HL Large sales.

**Consolidated** (`consolidated/` folder): One set of files per (Division, Size). The `HL_LARGE` consolidated view aggregates across all portals (Amazon, Flipkart, D2C, etc.). For the summary file, portal metrics become column suffixes: `qty_Amazon`, `qty_Flipkart`, etc.

### PNG Analysis Charts

Each segment also gets a four-panel PNG analysis chart:
- Panel 1: Horizontal bar chart of volume share per archetype
- Panel 2: Year-on-year grouped bar chart of qty per archetype
- Panel 3: Monthly % share trend lines (solid = year 1, dashed = year 2)
- Panel 4: Summary table (archetype key, price range, vol%, qty per year)

### Analyst Consumption Workflow

1. Open `{segment}_pivot_ready.xlsx` in Excel
2. The spreadsheet already has rows = archetypes, columns = YYYY-MM months
3. Insert a PivotTable or PivotChart on this data
4. Filter by Division, Size, Portal as needed
5. For cross-portal comparison, use the consolidated version

---

## 12. Diagnostic and Debug Layer

### NB09 — Threshold Sensitivity Analysis

NB09 is run standalone (not part of the main pipeline) via `python run_diagnostic.py`. It loads the segment pivots from all three channels simultaneously and tests each segment at three threshold levels.

**Inputs required**: `03_segment_pivots.pkl` and `02_fine_bucket_ts.csv` must exist for each channel before NB09 can run.

**For each segment, NB09 computes**: `k_at_070` (K at threshold 0.70), `k_at_060` (K at 0.60), `k_at_050` (K at 0.50), `k_diff_60` (k_60 − k_70), `needs_tuning` (True if any archetype at 0.70 has a peak-concentration flag).

**How to interpret the output**:

- If `k_diff_60 >= 2 AND total_vol > 10,000`: The segment genuinely benefits from a lower threshold. Add it to `segment_threshold_overrides` in `channel_registry.py` with value 0.60.
- If `k_diff_60 == 1 OR total_vol <= 10,000`: Marginal improvement or too little data to justify additional archetypes. Keep at 0.70.
- If `needs_tuning == True` but `k_diff_60 == 0`: The peak-concentration flag fired but the lower threshold doesn't help. The issue may be in the data itself (e.g., a single dominant price bucket that can't be split further).

NB09 also generates chart PNGs in `09_threshold_diagnostic_charts/` showing, for each flagged segment, the volume distribution and trend lines at both thresholds.

**Current status**: NB09 was used to identify the 30 segments in the current `segment_threshold_overrides`. It needs to be re-run after any pipeline run to confirm the overrides are still appropriate.

### NB10 — Pivot Detail

NB10 generates per-flagged-segment Excel files (`10_pivot_detail/`) with detailed year×month quantity and net_sales tables. Unlike the main reporting (NB08 which shows all segments), NB10 focuses specifically on segments identified by NB09 as needing closer inspection.

**When to use NB10**: Before finalizing the threshold overrides in `channel_registry.py`. The NB10 Excel files let analysts visually verify that the additional archetypes produced at threshold 0.60 make business sense — e.g., one archetype covering the premium sub-segment and another covering the standard sub-segment.

**NB10 logic**: For each flagged segment, re-runs `cluster_auto()` at either 0.60 or 0.70 (based on the NB09 `k_diff_60 >= 2 AND vol > 10,000` rule), builds a year × month pivot of qty, attaches a price_range column, and writes to Excel with separate sheets for qty and net_sales plus a metadata INFO sheet.

Output: one `.xlsx` per flagged segment plus `10_master_nb_summary.csv` (one row per New Bucket per flagged segment).

---

## 13. Source Code Breakdown (src/)

### `clustering.py`

Contains two functions:

**`greedy_adjacent_cluster(pivot, vol_by_bucket, total_vol, min_vol_pct, max_k)`**

An older version of the core algorithm. Uses a different stopping rule than Auto-K: merges stop when the merged cluster's volume would fall below `min_vol_pct` AND the current count is already at or below `max_k`. This is a more conservative stopping criterion than the cumulative-cost approach. Used only for early experimentation (visible in NB04 cells 1–13); the production algorithm is `cluster_segment_auto` in NB04 Cell 26 / NB09.

Parameters:
- `pivot`: DataFrame, rows = bucket_min, cols = months, values = pct_share
- `vol_by_bucket`: dict mapping bucket_min → total qty
- `total_vol`: total segment qty (sum of all bucket volumes)
- `min_vol_pct`: minimum cluster volume fraction (float, e.g., 0.03 = 3%)
- `max_k`: maximum allowed clusters

Returns: `{bucket_min: New_Bucket_number}` dict

**`post_merge_cleanup(cluster_map, vol_by_bucket, total_vol, min_vol_pct)`**

Post-processing sweep: after the main merge, any cluster that still has less than `min_vol_pct` volume is merged into its price-adjacent neighbor (left neighbor preferred). Repeats until all clusters are above threshold. Renumbers 1..K in ascending price order after each fix. Used as a cleanup pass after `greedy_adjacent_cluster`.

### `channel_registry.py`

The single most important configuration file. Defines all channel-specific behavior as a dictionary `CHANNEL_REGISTRY` with keys `"TT"`, `"EC"`, `"MT"`.

For each channel, the following keys are defined:

| Key | Type | Description |
|-----|------|-------------|
| `raw_path` | str | Relative path to raw Excel file |
| `raw_sheet` | str | Sheet name to read |
| `range_col` | str | Column name containing price ranges |
| `portal_col` | str | Column name for portal |
| `portal_is_int` | bool | True for TT (integer portals), False for EC/MT |
| `channel_filter` | str | Value used to filter `Final Channel` column |
| `bucket_width` | int | Standard bucket width (100) |
| `bucket_width_tail` | int or None | Wider bucket width for high-price items (500) |
| `tail_switch_price` | dict | Per-division price threshold for tail bucketing |
| `segment_dims` | list | Columns defining a segment key |
| `ignore_years` | list | Years to exclude |
| `rolling_median_months` | int | ASP smoothing window (3) |
| `min_history_months` | int | Minimum active months for a bucket (3 for TT, 6 for EC/MT) |
| `noise_floor_pct` | float | Minimum volume share for active bucket (0.001) |
| `max_k` | int | Maximum archetypes per segment (8 for TT, 10 for EC/MT) |
| `min_cluster_vol_pct` | float | Minimum cluster volume fraction (0.03 for TT, 0.01 for EC/MT) |
| `trend_similarity_threshold` | float | Global threshold (0.70) |
| `min_segment_qty` | int | Minimum volume for segment to qualify (0 for TT, 5000 for EC/MT) |
| `out_path` | str | Output directory |
| `validation_file` | str | Path to ground truth Excel |
| `validation_sheet` | str | Sheet name for ground truth |
| `validation_gt_col` | str | Column name for ground truth New Bucket |
| `validation_min_col` | str | Column name for ground truth price minimum |
| `validation_join` | str | Join strategy ("floor_100" or "parse_string") |
| `portal_abbrev` | dict | Integer portal → string abbreviation (TT only) |
| `gt_key_col` | str | Ground truth archetype key column name |
| `segment_threshold_overrides` | dict | Per-segment threshold overrides |

The `get_channel(name)` function validates the channel name and returns the appropriate dict.

### `config.py`

A thin wrapper that reads the `CHANNEL` environment variable (set by `run_pipeline.py`), calls `get_channel(CHANNEL)` to get the registry entry, and re-exports all keys as module-level constants. This allows any notebook to do `from config import *` and immediately have all channel-specific constants in scope.

The environment variable injection (`CHANNEL=EC python ...`) is the mechanism by which papermill passes the channel selection into notebooks at runtime. Without this, notebooks would always use the default channel (`TT`).

Also exports legacy variables (`DISTANCE_THRESHOLD = 0.4`, `MIN_BUCKET_MONTHS = 3`) that were used in early algorithm iterations and are kept for compatibility with old cells.

### `pipeline.py`

Contains a single function `assign_buckets(asp, division, cfg_dict)` that encapsulates the bucket assignment logic: if the division has a `tail_switch_price` defined and the ASP meets or exceeds it, use `bucket_width_tail` (500); otherwise use `bucket_width` (100). Returns `int((asp // width) * width)`.

This function is imported by NB02 to perform the per-row bucket assignment.

### `run_pipeline.py`

The main orchestration script. Accepts command-line arguments and executes notebooks sequentially using papermill.

**CLI interface:**
```
python run_pipeline.py --channel EC
python run_pipeline.py --channel TT --start-from 03   # resume from NB03
python run_pipeline.py --channel MT --only 06         # run only NB06
```

**Execution flow:**
1. Parse args: `--channel` (required), `--start-from` (optional, resume), `--only` (optional, single notebook)
2. Set `os.environ["CHANNEL"] = channel` so that all spawned notebooks see the correct channel
3. For each notebook in the NOTEBOOKS list (or filtered subset): find the file in `notebooks/`, call `pm.execute_notebook()` with `environment_variables={"CHANNEL": channel}` and `timeout=3600`
4. Write timestamped log to `src/logs/{channel}/run_{YYYYMMDD_HHMMSS}.log`
5. If any notebook fails (raises `PapermillExecutionError`), log the cell index and error, and exit with code 1

**Error reporting:** When a notebook fails, the partially-executed output notebook is saved to `{notebook_name}_executed.ipynb`. This file is invaluable for debugging: open it in Jupyter and scroll to the last executed cell to see the exact error.

### `run_diagnostic.py`

Simpler variant of `run_pipeline.py` specifically for NB09. Key differences: no `--channel` flag (NB09 loads all channels itself), different log directory (`logs/diagnostic/`), shorter timeout (1800s).

### `ec_config.py`

A legacy standalone config file for EC channel, predating the unified `channel_registry.py`. Contains the same constants as the EC entry in `channel_registry.py`. No longer actively used — kept for backward compatibility with any notebooks that import it directly.

### `write_nb09.py` and `write_nb10_pivot_detail.py`

Scripts that programmatically generate the notebook JSON for NB09 and NB10. The notebooks are constructed by calling `md()` and `code()` helper functions that append cells to a `CELLS` list, then write the list as a valid `.ipynb` JSON file.

**When to use these**: If the corresponding notebook file becomes corrupted (the `NameError: name 'null'` error in `nbconvert` is a symptom of this) or needs to be regenerated after code changes, run `python write_nb09.py` or `python write_nb10_pivot_detail.py` from the `src/` directory. The script will also validate each cell's JSON is free of literal `null` values (a common corruption source).

---

## 14. Configuration System

### How Thresholds Are Controlled

The `trend_similarity_threshold` in `channel_registry.py` controls the default threshold for all segments in a channel. The `segment_threshold_overrides` dict overrides this for specific segments. Both are read in NB04 as:

```python
seg_thr = cfg.get('segment_threshold_overrides', {}).get(seg_key, None)
fmap = cluster_segment_auto(..., threshold_override=seg_thr)
```

### How Segments Are Defined

Segments are not hardcoded. They emerge organically from the data: any (Division, Portal, Size) combination with sales records in the cleaned data is a segment. The `segment_dims = ["Division", "Portal", "Size"]` config key specifies which columns define the segment key. The `min_segment_qty` filter (0 for TT, 5,000 for EC/MT) removes segments with insufficient volume before clustering.

### How to Modify Behavior Safely

**To add a threshold override for a segment:**
1. Run NB09 to confirm `k_diff_60 >= 2 AND total_vol > 10,000` for the segment
2. Add the segment key and value 0.60 to `segment_threshold_overrides` in `channel_registry.py`
3. Re-run the pipeline from NB04: `python run_pipeline.py --channel EC --start-from 04`

**To change the global threshold:**
Modify `trend_similarity_threshold` in the appropriate channel entry. Lower values (e.g., 0.60) produce more archetypes everywhere. Higher values (0.80) produce fewer. Test on a single channel before applying globally.

**To change MAX_K:**
Modify `max_k` in the channel entry. Increasing to 12 would allow up to 12 archetypes per segment. Note: this only affects the cap — Auto-K may still choose fewer if the data supports it.

**To add a new channel:**
Add a new entry to `CHANNEL_REGISTRY` in `channel_registry.py` with all required keys. Add the channel name to the `choices` list in `run_pipeline.py`'s `parse_args()`.

---

## 15. Execution Guide

### Environment Setup

```bash
# Python 3.14+ recommended (project uses 3.14.3)
pip install pandas numpy scipy scikit-learn matplotlib seaborn papermill openpyxl jupyter nbconvert --break-system-packages
```

### Running the Main Pipeline

```powershell
# Navigate to src directory
cd "D:\archetype_engine - Copy_2 - Copy\src"

# Run EC channel (90 segments, ~15–20 minutes)
python run_pipeline.py --channel EC

# Run TT channel (14 segments, ~3–5 minutes)
python run_pipeline.py --channel TT

# Run MT channel (45 segments, ~8–12 minutes)
python run_pipeline.py --channel MT
```

Each channel produces outputs in `data/outputs/{CHANNEL}/`.

### Running the Diagnostic

After all three channels have been run:

```powershell
python run_diagnostic.py
```

This requires `03_segment_pivots.pkl` and `02_fine_bucket_ts.csv` to exist for all three channels. Output: `data/outputs/09_threshold_diagnostic.csv` and charts in `data/outputs/09_threshold_diagnostic_charts/`.

### Generating Pivot Detail Files

```powershell
cd "..\notebooks"
jupyter nbconvert --to notebook --execute 10_pivot_detail.ipynb --output 10_pivot_detail_executed.ipynb
```

Or regenerate the notebook first if needed:

```powershell
cd "..\src"
python write_nb10_pivot_detail.py
```

### Resuming After Failure

If the pipeline fails at notebook 06:

```powershell
python run_pipeline.py --channel EC --start-from 06
```

### Running a Single Notebook

```powershell
python run_pipeline.py --channel TT --only 08
```

---

## 16. Failure Modes and Debugging

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| `PermissionError: [Errno 13] Permission denied` | An output CSV or XLSX is open in Excel | Close the file in Excel, re-run from the failing notebook |
| `argument --only: expected one argument` | Missing the notebook number after `--only` | Supply the number: `--only 08` not `--only` |
| `NameError: name 'null' is not defined` | Notebook JSON file has been corrupted with literal `null` values (not Python `None`) | Run `python write_nb09.py` or `write_nb10_pivot_detail.py` from `src/`, then retry |
| `FileNotFoundError: 03_segment_pivots.pkl` | NB03 has not been run, or ran for a different channel | Run pipeline from NB03: `--start-from 03` |
| `ValueError: Channel 'XX' nahi mila` | Invalid channel name passed to `get_channel()` | Use one of `EC`, `TT`, `MT` exactly |
| `KeyError` in NB04 or NB06 | A segment key in `segment_threshold_overrides` doesn't match the actual data | Check spelling — segment keys are case-sensitive and follow `DIV_Portal_SIZE` format |
| Pipeline times out (>3600s) | A notebook is hanging (rare — usually NB01 if Excel file is very large) | Set `TIMEOUT` in `run_pipeline.py` to a larger value, or investigate the file size |
| NB06 shows low validation accuracy (<80%) | Threshold is wrong for many segments, or data has changed significantly | Re-run NB09 and review threshold overrides |

### How to Resume Pipeline Mid-Run

If the pipeline fails at NB04:

```powershell
python run_pipeline.py --channel EC --start-from 04
```

All previously generated files (NB01–NB03 outputs) are preserved. The pipeline re-reads them without re-running the earlier notebooks.

### Inspecting a Failed Notebook

When papermill reports a failure, the partially-executed notebook is always saved:
- `notebooks/04_clustering (1)_executed.ipynb` (for NB04)

Open this file in Jupyter Notebook or VS Code, scroll to the last executed cell, and read the error traceback. The output cells above the failure are also preserved and often contain useful diagnostic prints.

---

## 17. Design Decisions and Tradeoffs

### Why Notebooks + papermill

Jupyter notebooks provide an interactive, visual development environment where each step can be individually inspected, modified, and re-run. This was essential during development: testing different algorithm variants (v1 through v5 are all visible in NB04), comparing against ground truth immediately after each change, and building intuition for the data's behavior.

papermill enables these notebooks to be run programmatically and sequentially from a single script, with proper error handling, environment variable injection, and logging. It bridges the gap between exploratory analysis and production execution without requiring a full conversion to Python scripts.

The tradeoff: notebooks are harder to version control than pure Python files (diff noise from cell outputs), and debugging failures requires opening the executed notebook rather than reading a stack trace directly.

### Why Greedy Adjacent Merge

As documented in Section 6.5, multiple clustering approaches were prototyped: dendrogram with elbow method (NB04 Cell 3), silhouette score selection (NB04 Cell 18 — v5), composite score with volume imbalance penalty (NB04 Cell 16 — v3), hierarchical contiguity enforcement (NB04 Cell 17 — v4), and the final Auto-K greedy merge with cumulative cost stopping (NB04 Cell 26).

The greedy approach won because it is the most transparent to business analysts (it directly mimics manual grouping), most predictable in behavior, fastest to run, and most consistently produces valid results across all 157 segments.

### Why Share-Based Trends

Absolute sales volumes contain both structural (price-sensitivity) signal and trend signal (overall category growth, promotional effects). By normalizing to within-segment share, the algorithm focuses purely on the relative popularity pattern of each price bucket over time. Two adjacent buckets that both grew 30% but whose seasonal pattern is the same will be correctly grouped; two adjacent buckets at the same absolute volume but with opposing seasonality will be correctly separated.

### Limitations

**The threshold is globally tuned, not per-segment learned.** The 0.70 default and 0.60 overrides were determined by manual inspection of NB09 diagnostic outputs. An ideal system would learn an appropriate threshold per segment from the data.

**Contiguity constraint is absolute.** There are cases where a non-adjacent pair of price buckets genuinely behaves similarly (e.g., ₹999 promotional bundles and ₹1,999 premium bundles both spike during festivals). The algorithm cannot merge these, which is the correct business behavior for price range definitions.

**No notion of "segment not ready."** If a segment has very few months of data, clustering still runs. The results may be meaningless. The `min_segment_qty` filter only checks volume, not data stability.

**Single-year pivots.** If only one year of data exists (e.g., new portal), the trend is extremely short and clustering results should be treated with caution.

---

## 18. Extension Opportunities

### Real-Time Pipeline

Replace papermill-based notebook execution with a proper task orchestrator (Airflow, Prefect, or Dagster). Each notebook maps cleanly to a task. Dependencies (NB03 requires NB02 output) are expressed as task dependencies. Triggers on new data arrival instead of manual execution.

### UI Layer

Build a Streamlit or Dash application on top of the NB08 outputs. Allow analysts to select a segment, view the current archetypes, and interactively test different thresholds using a slider. The UI would call `cluster_segment_auto()` directly and display the result in real time.

### Auto-Threshold Learning

Rather than manually inspecting NB09 output and adding overrides, train a simple regression model: given segment features (total volume, number of active buckets, coefficient of variation across months, `k_diff_60`), predict the optimal threshold. This could be done with a small labeled dataset from the current manual overrides as training examples.

### ML-Based Segmentation

Replace the correlation-distance greedy merge with a learned similarity model. Train a contrastive or metric learning model on the existing validated (segment, archetype) pairs. This would allow the system to learn which features of a bucket's time series are most predictive of correct grouping, potentially outperforming Pearson correlation for edge cases.

### Cross-Channel Archetype Alignment

Currently each channel produces independent archetype definitions. For products sold across TT, EC, and MT, the same physical price points may map to different New Bucket labels in different channels. A post-processing step that aligns archetype boundaries across channels would improve cross-channel analysis.

---

## 19. Glossary

**ABT (Analytical Base Table)**: The enriched sales table produced by NB07. Every raw transaction enriched with its archetype label. The master dataset for downstream analysis.

**Active Bucket**: A price bucket that meets both the `min_history_months` and `noise_floor_pct` filters. Only active buckets participate in clustering; sparse buckets are assigned to the nearest active bucket's archetype.

**Archetype / New Bucket (NB)**: A contiguous group of ₹100 price buckets with similar monthly sales-share trends. The output of clustering. Labeled NB1, NB2, ..., NBK in ascending price order.

**archetype_key**: A unique string identifier for an (archetype, segment) pair. Format varies by channel: for TT: `{div}{abbrev}{portal}{nb}{size}` (e.g., `HLTT18_CABIN`); for EC/MT: `{portal}{div}{size}{nb}` (e.g., `AmazonHL_LARGE3`).

**Auto-K**: The algorithm that automatically determines K (number of archetypes) from the data using a cumulative merge cost threshold.

**bucket_min**: The lower bound of a ₹100 price bucket. A product with ASP ₹1,847 maps to `bucket_min = 1800`.

**channel_registry.py**: The central configuration file defining all per-channel settings. The single source of truth for channel behavior.

**Cumulative Cost Threshold**: The fraction of total merge cost (0.70 by default) at which the greedy adjacent merge algorithm stops. Higher values → fewer archetypes (more merging). Lower values → more archetypes (less merging).

**Division**: Product category. HL = Hardluggage, SL = Softluggage, BP = Backpack, BS = Business/Small, DF = Duffel.

**Fine Bucket**: Synonym for price bucket — a ₹100-wide price interval.

**IGNORE_YEARS**: Years excluded from analysis. Currently [2023] for all channels.

**K**: The number of archetypes (New Buckets) in a segment.

**MAX_K**: The maximum allowed K per segment. 8 for TT, 10 for EC and MT.

**merge_cost**: The dissimilarity between two adjacent bucket groups, computed as (1 − Pearson correlation) / 2. Ranges 0 (identical trends) to 1 (opposite trends).

**min_cluster_vol_pct**: Minimum fraction of segment volume that any single archetype must represent. 0.03 (3%) for TT, 0.01 (1%) for EC/MT.

**min_history_months**: Minimum number of months with non-zero sales for a bucket to be considered active. 3 for TT, 6 for EC/MT.

**noise_floor_pct**: Minimum fraction of total segment volume a bucket must represent to be active. 0.001 (0.1%) for all channels.

**papermill**: Python library that executes Jupyter notebooks programmatically, with parameter injection via environment variables and full output capture.

**pct_share**: A price bucket's percentage of total segment sales in a given month. The values in the segment pivot matrix.

**Portal**: Sales channel within a channel type. EC portals: Amazon, Flipkart, D2C, Myntra, Blinkit, MP, Others. MT portals: Dmart, Others, Reliance, Vishal. TT portals: integer IDs.

**Segment**: The atomic unit of analysis. Uniquely identified by Division × Portal × Size.

**segment_threshold_overrides**: Per-segment threshold values that override the global `trend_similarity_threshold` for specific high-complexity segments.

**Size**: Product size category. CABIN, LARGE, MEDIUM, SO2, SO3, Single, DF, DFT.

**Sparse Bucket**: A price bucket that does not meet the active bucket criteria. Assigned to the nearest active bucket's archetype after clustering.

**tail_switch_price**: Division-specific price threshold above which bucket width expands from ₹100 to ₹500 (the "tail"). Prevents sparse high-price buckets from dominating cluster count.

**trend_similarity_threshold**: The cumulative merge cost fraction at which the Auto-K algorithm stops. Default 0.70. Lower values produce more archetypes.

