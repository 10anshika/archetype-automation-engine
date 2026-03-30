import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from channel_registry import get_channel

# ── Channel switch: set env var CHANNEL=EC before launching ──────────────
_CHANNEL = os.environ.get("CHANNEL", "TT")
# ─────────────────────────────────────────────────────────────────────────

cfg = get_channel(_CHANNEL)

# Core exports
CHANNEL                    = _CHANNEL
RAW_PATH                   = cfg["raw_path"]
RAW_SHEET                  = cfg["raw_sheet"]
OUT_PATH                   = cfg["out_path"]
IGNORE_YEARS               = cfg["ignore_years"]
BUCKET_WIDTH               = cfg["bucket_width"]
ROLLING_MEDIAN_MONTHS      = cfg["rolling_median_months"]
TREND_SIMILARITY_THRESHOLD = cfg["trend_similarity_threshold"]
MIN_HISTORY_MONTHS         = cfg["min_history_months"]
NOISE_FLOOR_PCT            = cfg["noise_floor_pct"]
MAX_K                      = cfg["max_k"]
MIN_CLUSTER_VOL_PCT        = cfg["min_cluster_vol_pct"]
LOG_PATH                   = "logs/"

# EC-specific exports (safe for TT too — TT registry has all these keys)
RANGE_COL           = cfg["range_col"]
PORTAL_IS_INT       = cfg["portal_is_int"]
MIN_SEGMENT_QTY     = cfg["min_segment_qty"]
TAIL_SWITCH_PRICE   = cfg.get("tail_switch_price", {})
BUCKET_WIDTH_TAIL   = cfg.get("bucket_width_tail", None)
PORTAL_ABBREV       = cfg["portal_abbrev"]
VALIDATION_FILE     = cfg["validation_file"]
VALIDATION_SHEET    = cfg["validation_sheet"]
VALIDATION_GT_COL   = cfg["validation_gt_col"]
VALIDATION_MIN_COL  = cfg["validation_min_col"]
VALIDATION_JOIN     = cfg["validation_join"]
GT_KEY_COL          = cfg["gt_key_col"]

# Legacy experiment variables — do not delete, old cells use these
DISTANCE_THRESHOLD = 0.4
MIN_BUCKET_MONTHS  = 3