# ── Channel ───────────────────────────────────────────────────────────────
CHANNEL      = "EC"
IGNORE_YEARS = [2023]

# ── Bucketing ─────────────────────────────────────────────────────────────
BUCKET_WIDTH          = 100
BUCKET_WIDTH_TAIL     = 500
ROLLING_MEDIAN_MONTHS = 3

TAIL_SWITCH_PRICE = {
    'BP': 1500,
    'BS': 1500,
    'DF': 1500,
    'HL': 5000,
    'SL': 4000,
}

# ── Clustering ────────────────────────────────────────────────────────────
MIN_HISTORY_MONTHS         = 6
NOISE_FLOOR_PCT            = 0.001
MAX_K                      = 10
MIN_CLUSTER_VOL_PCT        = 0.01
TREND_SIMILARITY_THRESHOLD = 0.70

# ── Segment filtering ─────────────────────────────────────────────────────
MIN_SEGMENT_QTY = 5000

# ── Paths ─────────────────────────────────────────────────────────────────
RAW_PATH  = "data/raw/ec_data.xlsx"
RAW_SHEET = "Sheet1"
OUT_PATH  = "data/outputs/EC/"
LOG_PATH  = "logs/"