# channel_registry.py
# Har channel ki alag settings yahan hain.
# Naya channel add karna ho toh sirf yahan ek entry add karo.

CHANNEL_REGISTRY = {

    "TT": {
        "raw_path"                 : "data/raw/manual_validation.xlsx",
        "raw_sheet"                : "raw",
        "range_col"                : "Masked Range",
        "portal_col"               : "Portal",
        "portal_is_int"            : True,
        "channel_filter"           : "TT",
        "bucket_width"             : 100,
        "bucket_width_tail"        : None,
        "tail_switch_price"        : {},
        "segment_dims"             : ["Division", "Portal", "Size"],
        "ignore_years"             : [2023],
        "rolling_median_months"    : 3,
        "min_history_months"       : 3,
        "noise_floor_pct"          : 0.001,
        "max_k"                    : 8,   # TT: capped at 8
        "min_cluster_vol_pct"      : 0.03,
        "trend_similarity_threshold": 0.70,
        "min_segment_qty"          : 0,
        "out_path"                 : "data/outputs/TT/",
        "validation_file"          : "data/raw/manual_validation.xlsx",
        "validation_sheet"         : "Bucket_map",
        "validation_gt_col"        : "New Bucket",
        "validation_min_col"       : "min",
        "validation_join"          : "floor_100",
        "portal_abbrev"            : {1: "TT"},
        "gt_key_col"               : "key_2",
        "segment_threshold_overrides": {
            # k_diff_60 >= 2 AND vol > 10,000 — genuine under-segmentation
            "HL_1_SO2"   : 0.60,
            "SL_1_SO2"   : 0.60,
            "BP_1_Single": 0.60,
            "SL_1_CABIN" : 0.60,
            # NOTE: HL_1_CABIN, HL_1_MEDIUM, SL_1_LARGE already at MAX_K=8
            # Lowering threshold won't help — only raising max_k would.
        },
    },

    "EC": {
        "raw_path"                 : "data/raw/ec_data.xlsx",
        "raw_sheet"                : "Sheet1",
        "range_col"                : "Range",
        "portal_col"               : "Portal",
        "portal_is_int"            : False,
        "channel_filter"           : "EC",
        "bucket_width"             : 100,
        "bucket_width_tail"        : 500,
        "tail_switch_price"        : {
            "BP": 1500,
            "BS": 1500,
            "DF": 1500,
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
        "min_segment_qty"          : 5000,
        "out_path"                 : "data/outputs/EC/",
        "validation_file"          : "data/raw/ec_data.xlsx",
        "validation_sheet"         : "Bucket_mapped",
        "validation_gt_col"        : "New Bucket",
        "validation_min_col"       : "ASP_bucket",
        "validation_join"          : "parse_string",
        "portal_abbrev"            : {},
        "gt_key_col"               : "key",
        "segment_threshold_overrides": {
            # k_diff_60 >= 2 AND vol > 10,000 — genuine under-segmentation
            "HL_MP_CABIN"        : 0.60,
            "HL_MP_MEDIUM"       : 0.60,
            "HL_Others_LARGE"    : 0.60,
            "HL_Others_MEDIUM"   : 0.60,
            "HL_Amazon_LARGE"    : 0.60,
            "HL_Flipkart_LARGE"  : 0.60,
            "HL_Flipkart_MEDIUM" : 0.60,
            "SL_MP_CABIN"        : 0.60,
            "SL_MP_LARGE"        : 0.60,
            "SL_MP_MEDIUM"       : 0.60,
            "BP_D2C_Single"      : 0.60,
            "BP_Flipkart_Single" : 0.60,
            "BP_MP_Single"       : 0.60,
            "BP_Others_Single"   : 0.60,
        },
    },

    "MT": {
        "raw_path"                  : "data/raw/mt_data.xlsx",
        "raw_sheet"                 : "raw",
        "range_col"                 : "Range_mask",
        "portal_col"                : "Portal",
        "portal_is_int"             : False,
        "channel_filter"            : "MT",
        "bucket_width"              : 100,
        "bucket_width_tail"         : 500,
        "tail_switch_price"         : {
            "BP": 1500,
            "BS": 1500,
            "DF": 1500,
            "HL": 5000,
            "SL": 4000,
        },
        "segment_dims"              : ["Division", "Portal", "Size"],
        "ignore_years"              : [2023],
        "rolling_median_months"     : 3,
        "min_history_months"        : 6,
        "noise_floor_pct"           : 0.001,
        "max_k"                     : 10,
        "min_cluster_vol_pct"       : 0.01,
        "trend_similarity_threshold": 0.70,
        "min_segment_qty"           : 5000,
        "out_path"                  : "data/outputs/MT/",
        "validation_file"           : "data/raw/mt_data.xlsx",
        "validation_sheet"          : "Bucket_mapped",
        "validation_gt_col"         : "New Bucket",
        "validation_min_col"        : "ASP_bucket",
        "validation_join"           : "parse_string",
        "portal_abbrev"             : {},
        "gt_key_col"                : "key",
        "segment_threshold_overrides": {
            # k_diff_60 >= 2 AND vol > 10,000 — genuine under-segmentation
            "HL_Reliance_CABIN"  : 0.60,
            "HL_Reliance_MEDIUM" : 0.60,
            "HL_Reliance_LARGE"  : 0.60,
            "HL_Others_LARGE"    : 0.60,
            "HL_Others_MEDIUM"   : 0.60,
            "HL_Vishal_MEDIUM"   : 0.60,
            "SL_Others_CABIN"    : 0.60,
            "SL_Others_LARGE"    : 0.60,
            "SL_Others_MEDIUM"   : 0.60,
            "SL_Reliance_LARGE"  : 0.60,
            "SL_Reliance_MEDIUM" : 0.60,
            "BP_Others_Single"   : 0.60,
        },
    },

}


def get_channel(name: str) -> dict:
    """
    Notebook mein use karo:  cfg = get_channel("EC")
    """
    if name not in CHANNEL_REGISTRY:
        raise ValueError(
            f"Channel '{name}' nahi mila.\n"
            f"Available channels: {list(CHANNEL_REGISTRY.keys())}"
        )
    return CHANNEL_REGISTRY[name]
