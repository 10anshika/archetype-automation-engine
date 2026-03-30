import numpy as np


def greedy_adjacent_cluster(pivot, vol_by_bucket, total_vol,
                             min_vol_pct, max_k):
    """
    Analyst ki tarah kaam karta hai:
    - Har bucket apna group hai shuru mein
    - Har step mein sabse similar ADJACENT pair merge karo
    - Ruko jab next merge min_vol_pct se neeche jaaye
    - Non-adjacent buckets kabhi merge nahi hote

    Parameters:
        pivot         : DataFrame — rows=buckets, cols=months, values=pct_share
        vol_by_bucket : dict — {bucket_min: total_qty}
        total_vol     : int  — segment ka total volume
        min_vol_pct   : float — minimum cluster volume (0.03 = 3%)
        max_k         : int  — maximum clusters allowed

    Returns:
        dict — {bucket_min: New_Bucket_number}
    """
    buckets  = sorted(pivot.index.tolist())
    clusters = {i: [b] for i, b in enumerate(buckets)}

    def cluster_series(bucket_list):
        return pivot.loc[bucket_list].mean(axis=0)

    def pearson_sim(list1, list2):
        s1 = cluster_series(list1)
        s2 = cluster_series(list2)
        if s1.std() == 0 or s2.std() == 0:
            return 0.5
        return float(np.corrcoef(s1, s2)[0, 1])

    def cluster_vol_pct(bucket_list):
        return sum(vol_by_bucket.get(b, 0) for b in bucket_list) / total_vol

    while len(clusters) > 2:
        cluster_ids = sorted(clusters.keys())
        best_sim    = -1
        best_pair   = None

        for i in range(len(cluster_ids) - 1):
            c1  = cluster_ids[i]
            c2  = cluster_ids[i + 1]
            sim = pearson_sim(clusters[c1], clusters[c2])
            if sim > best_sim:
                best_sim  = sim
                best_pair = (c1, c2)

        if best_pair is None:
            break

        c1, c2 = best_pair
        merged         = clusters[c1] + clusters[c2]
        merged_vol_pct = cluster_vol_pct(merged)

        if merged_vol_pct < min_vol_pct and len(clusters) <= max_k:
            break

        clusters[c1] = merged
        del clusters[c2]

    result = {}
    for new_id, (_, bucket_list) in enumerate(
            sorted(clusters.items()), start=1):
        for b in bucket_list:
            result[b] = new_id

    return result


def post_merge_cleanup(cluster_map, vol_by_bucket, total_vol, min_vol_pct):
    """
    Main merge ke baad — agar koi cluster min_vol_pct se neeche hai
    toh use adjacent cluster mein merge karo.
    """
    while True:
        clusters = {}
        for bucket, nb in cluster_map.items():
            clusters.setdefault(nb, []).append(bucket)

        small = {nb: bl for nb, bl in clusters.items()
                 if sum(vol_by_bucket.get(b, 0) for b in bl) / total_vol < min_vol_pct}

        if not small:
            break

        nb_to_fix  = sorted(small.keys())[0]
        bl_to_fix  = clusters[nb_to_fix]
        min_bucket = min(bl_to_fix)
        max_bucket = max(bl_to_fix)

        other_nbs = sorted([n for n in clusters if n != nb_to_fix])
        if not other_nbs:
            break

        # Nearest neighbour by price
        left_nb  = max([n for n in other_nbs
                        if max(clusters[n]) < min_bucket], default=None)
        right_nb = min([n for n in other_nbs
                        if min(clusters[n]) > max_bucket], default=None)

        target = left_nb if left_nb is not None else right_nb
        if target is None:
            break

        for b in bl_to_fix:
            cluster_map[b] = target

        # Renumber 1..K in ascending price order
        seen = []
        for b in sorted(cluster_map):
            if cluster_map[b] not in seen:
                seen.append(cluster_map[b])
        remap      = {old: new + 1 for new, old in enumerate(seen)}
        cluster_map = {b: remap[c] for b, c in cluster_map.items()}

    return cluster_map
