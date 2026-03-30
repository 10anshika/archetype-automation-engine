# pipeline.py — shared utility functions used by notebooks

def assign_buckets(asp, division, cfg_dict):
    """
    Assign a single ASP value to its bucket_min.
    Uses tail bucketing (wider buckets) for high-price items if configured.
    """
    if asp is None or asp != asp:   # NaN check
        return 0

    tail_switch = cfg_dict.get('tail_switch_price', {})
    bucket_width_tail = cfg_dict.get('bucket_width_tail', None)
    bucket_width = cfg_dict.get('bucket_width', 100)

    if (bucket_width_tail is not None
            and division in tail_switch
            and asp >= tail_switch[division]):
        width = bucket_width_tail
    else:
        width = bucket_width

    return int((asp // width) * width)