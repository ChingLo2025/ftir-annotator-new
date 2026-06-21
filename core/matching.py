"""比對與打分（規格書 v1.2 §6）。

候選資格：位置分 > 0（FWHM 永不影響資格）。
位置分（嚴）：範圍內滿分，超出邊界 d ≥ k_pos·T_p′ 歸零。
FWHM 分（寬鬆）：範圍內滿分，超出邊界 d_w ≥ k_fwhm·T_w′ 歸零。
T′ = Tolerance Scale × 資料庫每筆容差。
總分 S = (1 − w_f)·score_pos + w_f·score_fwhm；該筆無 FWHM → S = score_pos。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULTS = {
    "w_f": 0.2,
    "scale": 1.0,      # Tolerance Scale
    "threshold": 0.5,  # Score Threshold：僅決定 Step 5 預設選擇
    "k_position": 2.0,
    "k_fwhm": 3.0,
}


def _band_score(value: float, center: float, tol: float, k: float) -> float:
    """範圍 center±tol 內 1 分；超出邊界線性衰減，d ≥ k·tol 歸零。"""
    d = abs(value - center) - tol
    if d <= 0:
        return 1.0
    zero_at = k * tol
    if zero_at <= 0:
        return 0.0
    return max(0.0, 1.0 - d / zero_at)


def match_peaks(peaks_df: pd.DataFrame, db_df: pd.DataFrame, params: dict) -> dict[int, list[dict]]:
    """回傳 {peak_id: [candidate, ...]}，candidate 依總分排序並帶 rank（1 起算）。

    candidate 欄位：db_index, functional_group, vibration_mode,
                    score, score_pos, score_fwhm（無 FWHM 時為 None）, rank
    """
    s = float(params["scale"])
    w_f = float(params["w_f"])
    result: dict[int, list[dict]] = {}

    for _, pk in peaks_df.iterrows():
        cands: list[dict] = []
        for db_i, r in db_df.iterrows():
            score_pos = _band_score(pk["position"], r["position"], s * r["position_tol"], params["k_position"])
            if score_pos <= 0:
                continue  # 位置分 > 0 才是候選
            if not np.isnan(r["fwhm"]):
                score_fwhm = _band_score(pk["fwhm"], r["fwhm"], s * r["fwhm_tol"], params["k_fwhm"])
                score = (1.0 - w_f) * score_pos + w_f * score_fwhm
            else:
                score_fwhm = None
                score = score_pos
            cands.append(
                {
                    "db_index": int(db_i),
                    "functional_group": r["functional_group"],
                    "vibration_mode": r["vibration_mode"],
                    "score": float(score),
                    "score_pos": float(score_pos),
                    "score_fwhm": None if score_fwhm is None else float(score_fwhm),
                }
            )
        cands.sort(key=lambda c: (-c["score"], -c["score_pos"]))
        for rank, c in enumerate(cands, start=1):
            c["rank"] = rank
        result[int(pk["peak_id"])] = cands

    return result


def default_selection(candidates: list[dict], threshold: float):
    """預設選擇：第 1 名 S ≥ 門檻 → 1；否則 None（不標註）。無候選 → None。"""
    if candidates and candidates[0]["score"] >= float(threshold):
        return 1
    return None


def reference_candidate(candidates: list[dict], selected_rank):
    """Annotation 2：排名最高且非所選的候選；不存在回傳 None。"""
    for c in candidates:
        if selected_rank is None or c["rank"] != selected_rank:
            return c
    return None
