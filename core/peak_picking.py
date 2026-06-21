"""Peak picking（規格書 v1.2 §5）。

作用於處理後反轉訊號；FWHM 以 peak_widths(rel_height=0.5) 的
left/right 內插點換算為 cm⁻¹（非均勻間距亦正確）。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import find_peaks, peak_widths

DEFAULTS = {
    "prominence_pct": 0.5,   # 反轉訊號全幅的百分比
    "use_min_height": False,
    "min_height": 1.0,       # %T 單位（反轉訊號高度）
    "min_spacing": 5.0,      # cm⁻¹
    "use_fwhm_filter": True,
    "fwhm_min": 2.0,
    "fwhm_max": 250.0,
}

_COLUMNS = ["peak_id", "position", "intensity", "fwhm", "prominence"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=_COLUMNS)


def pick_peaks(wavenumber, y_processed, params: dict) -> pd.DataFrame:
    """回傳 peak list（高波數在前，符合 FTIR 報表慣例）。"""
    wn = np.asarray(wavenumber, dtype=float)
    y = np.asarray(y_processed, dtype=float)

    span = float(np.ptp(y))
    if span <= 0 or len(y) < 3:
        return _empty()

    prominence = params["prominence_pct"] / 100.0 * span
    spacing = float(np.median(np.diff(wn)))
    distance = max(1, int(round(params["min_spacing"] / spacing))) if spacing > 0 else 1
    height = float(params["min_height"]) if params["use_min_height"] else None

    idx, props = find_peaks(y, prominence=prominence, height=height, distance=distance)
    if len(idx) == 0:
        return _empty()

    _, _, left_ips, right_ips = peak_widths(y, idx, rel_height=0.5)
    grid = np.arange(len(wn), dtype=float)
    fwhm = np.interp(right_ips, grid, wn) - np.interp(left_ips, grid, wn)

    df = pd.DataFrame(
        {
            "position": wn[idx],
            "intensity": y[idx],
            "fwhm": fwhm,
            "prominence": props["prominences"],
        }
    )

    if params["use_fwhm_filter"]:
        df = df[(df["fwhm"] >= params["fwhm_min"]) & (df["fwhm"] <= params["fwhm_max"])]

    df = df.sort_values("position", ascending=False).reset_index(drop=True)
    df.insert(0, "peak_id", df.index + 1)
    return df
