"""讀取與驗證輸入檔（規格書 v1.2 §2）。

光譜檔：第 1 列 metadata 一律忽略，第 2 列標頭須含 cm-1 與 %T。
資料庫檔：中心值 ± 容差格式，六欄。
格式不符一律拋出 FormatError，訊息可直接顯示給使用者。
"""
from __future__ import annotations

import io

import numpy as np
import pandas as pd


class FormatError(ValueError):
    """輸入檔格式不符規格。"""


SPECTRUM_MIN_POINTS = 50

# 資料庫欄名（正規化後）→ 內部欄名
_DB_COLUMNS = {
    "functional group": "functional_group",
    "vibration mode": "vibration_mode",
    "peak position (cm-1)": "position",
    "peak position tolerance (cm-1)": "position_tol",
    "fwhm (cm-1)": "fwhm",
    "fwhm tolerance (cm-1)": "fwhm_tol",
}

DB_DISPLAY_NAMES = {
    "functional_group": "Functional Group",
    "vibration_mode": "Vibration Mode",
    "position": "Peak Position (cm-1)",
    "position_tol": "Peak Position Tolerance (cm-1)",
    "fwhm": "FWHM (cm-1)",
    "fwhm_tol": "FWHM Tolerance (cm-1)",
}


def _decode(raw: bytes) -> str:
    """先試 UTF-8（含 BOM），再試 Big5/cp950。"""
    for enc in ("utf-8-sig", "cp950"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise FormatError("無法解讀檔案編碼（支援 UTF-8 / Big5）。")


def _norm(name) -> str:
    return " ".join(str(name).strip().lower().split())


def load_spectrum(raw: bytes) -> tuple[pd.DataFrame, dict]:
    """讀光譜檔 → (DataFrame[wavenumber, transmittance] 升冪, meta dict)。"""
    text = _decode(raw)
    lines = text.splitlines()
    if len(lines) < 3:
        raise FormatError("檔案內容不足：需第 1 列 metadata、第 2 列標頭與資料列。")

    meta_line = lines[0].strip()
    try:
        df = pd.read_csv(io.StringIO("\n".join(lines[1:])))
    except Exception as exc:  # noqa: BLE001 - 轉成統一的使用者錯誤
        raise FormatError(f"無法解析為 CSV：{exc}") from exc

    cols = {_norm(c): c for c in df.columns}
    wn_col, t_col = cols.get("cm-1"), cols.get("%t")
    if wn_col is None or t_col is None:
        raise FormatError(
            "第 2 列標頭須含 cm-1 與 %T 兩欄，實際讀到："
            + "、".join(str(c) for c in df.columns)
        )

    out = pd.DataFrame(
        {
            "wavenumber": pd.to_numeric(df[wn_col], errors="coerce"),
            "transmittance": pd.to_numeric(df[t_col], errors="coerce"),
        }
    ).dropna(how="all")

    n_bad = int(out.isna().any(axis=1).sum())
    if n_bad:
        raise FormatError(f"有 {n_bad} 列含非數值資料，請檢查檔案內容。")

    n_dup = int(out["wavenumber"].duplicated().sum())
    if n_dup:
        out = out.groupby("wavenumber", as_index=False)["transmittance"].mean()

    out = out.sort_values("wavenumber").reset_index(drop=True)
    if len(out) < SPECTRUM_MIN_POINTS:
        raise FormatError(f"資料點僅 {len(out)} 點（需 ≥ {SPECTRUM_MIN_POINTS}）。")

    meta = {
        "metadata_line": meta_line,
        "n_points": int(len(out)),
        "wn_min": float(out["wavenumber"].min()),
        "wn_max": float(out["wavenumber"].max()),
        "n_duplicates_merged": n_dup,
    }
    return out, meta


def load_database(raw: bytes) -> pd.DataFrame:
    """讀資料庫檔 → DataFrame（內部欄名），逐列驗證。"""
    text = _decode(raw)
    try:
        df = pd.read_csv(io.StringIO(text))
    except Exception as exc:  # noqa: BLE001
        raise FormatError(f"無法解析為 CSV：{exc}") from exc

    norm_map = {_norm(c): c for c in df.columns}
    missing = [k for k in _DB_COLUMNS if k not in norm_map]
    if missing:
        raise FormatError(
            "缺少欄位：" + "、".join(missing)
            + "（須含 Functional Group / Vibration Mode / Peak Position (cm-1) /"
              " Peak Position Tolerance (cm-1) / FWHM (cm-1) / FWHM Tolerance (cm-1)）"
        )

    out = pd.DataFrame({v: df[norm_map[k]] for k, v in _DB_COLUMNS.items()}).dropna(how="all")
    out["functional_group"] = out["functional_group"].astype(str).str.strip()
    out["vibration_mode"] = out["vibration_mode"].astype(str).str.strip()
    for c in ("position", "position_tol", "fwhm", "fwhm_tol"):
        out[c] = pd.to_numeric(out[c], errors="coerce")

    problems: list[str] = []
    for i, r in out.iterrows():
        row_no = i + 2  # 含標頭列的原始列號
        if not r["functional_group"] or r["functional_group"].lower() == "nan":
            problems.append(f"第 {row_no} 列：Functional Group 空白")
        if not r["vibration_mode"] or r["vibration_mode"].lower() == "nan":
            problems.append(f"第 {row_no} 列：Vibration Mode 空白")
        if np.isnan(r["position"]) or np.isnan(r["position_tol"]):
            problems.append(f"第 {row_no} 列：Peak Position 與其 Tolerance 須為數值")
        elif r["position_tol"] <= 0:
            problems.append(f"第 {row_no} 列：Peak Position Tolerance 須 > 0")
        if np.isnan(r["fwhm"]) != np.isnan(r["fwhm_tol"]):
            problems.append(f"第 {row_no} 列：FWHM 與其 Tolerance 須成對填寫或成對留空")
        elif not np.isnan(r["fwhm_tol"]) and r["fwhm_tol"] <= 0:
            problems.append(f"第 {row_no} 列：FWHM Tolerance 須 > 0")
    if problems:
        raise FormatError("資料庫內容錯誤：\n" + "\n".join(problems))
    if len(out) == 0:
        raise FormatError("資料庫沒有任何資料列。")

    return out.reset_index(drop=True)
