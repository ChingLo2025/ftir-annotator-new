"""前處理（規格書 v1.2 §4）：反轉 → 基線校正 → 平滑。

所有處理皆作用於反轉訊號 y = 100 − %T（峰朝上）；
顯示用曲線再映回 %T 方向。
"""
from __future__ import annotations

import numpy as np
from scipy.signal import savgol_filter

DEFAULTS = {
    "baseline_on": True,
    "lam": 1e6,
    "p": 0.01,
    "diff_order": 2,
    "smooth_on": False,
    "window": 11,
    "polyorder": 3,
}

LAM_OPTIONS = [1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9]
P_OPTIONS = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1]


def run(wavenumber, transmittance, params: dict) -> dict:
    """回傳 dict：y_inverted / baseline / y_processed / t_processed。"""
    wn = np.asarray(wavenumber, dtype=float)
    y = 100.0 - np.asarray(transmittance, dtype=float)  # 反轉，峰朝上

    baseline = np.zeros_like(y)
    if params["baseline_on"]:
        from pybaselines import Baseline  # 延遲載入，core 其他功能不受套件影響

        fitter = Baseline(x_data=wn)
        baseline, _ = fitter.asls(
            y,
            lam=float(params["lam"]),
            p=float(params["p"]),
            diff_order=int(params["diff_order"]),
        )

    y_proc = y - baseline

    if params["smooth_on"]:
        w = int(params["window"])
        if w % 2 == 0:
            w += 1
        w = max(5, min(w, len(y_proc) - 1 if len(y_proc) % 2 == 0 else len(y_proc)))
        po = min(int(params["polyorder"]), w - 1)
        y_proc = savgol_filter(y_proc, window_length=w, polyorder=po)

    return {
        "y_inverted": y,
        "baseline": baseline,
        "y_processed": y_proc,
        "t_processed": 100.0 - y_proc,
    }


def is_active(params: dict) -> bool:
    """是否有任何前處理開啟（決定圖上要不要畫「處理後」曲線）。"""
    return bool(params["baseline_on"] or params["smooth_on"])
