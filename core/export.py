"""輸出（規格書 v1.2 §9）：多區段 CSV（utf-8-sig, CRLF）與 PNG 光譜圖。"""
from __future__ import annotations

import csv
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import matching  # noqa: E402

N_COLS = 9

RESULT_HEADER = [
    "Peak Position (cm-1)",
    "Annotation 1", "Annotation 1 Score", "Vibration Mode", "Functional Group",
    "Annotation 2", "Annotation 2 score", "Vibration Mode", "Functional Group",
]


def _fmt_score(s: float) -> str:
    text = f"{s:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def _row(*cells) -> list[str]:
    out = [str(c) for c in cells] + [""] * N_COLS
    return out[:N_COLS]


def result_rows(peaks_df: pd.DataFrame, candidates: dict, selections: dict) -> list[list[str]]:
    """Annotation Result 區的資料列（不含標頭）。"""
    rows: list[list[str]] = []
    for _, pk in peaks_df.iterrows():
        pid = int(pk["peak_id"])
        cands = candidates.get(pid, [])
        cells: list[str] = [str(int(round(pk["position"])))]

        if not cands:
            cells.append("Unassigned")
        else:
            sel = selections.get(pid)
            if sel:
                chosen = cands[sel - 1]
                cells += [
                    chosen["functional_group"],
                    _fmt_score(chosen["score"]),
                    chosen["vibration_mode"],
                    chosen["functional_group"],
                ]
            else:
                cells += ["Not Annotated", "", "", ""]
            ref = matching.reference_candidate(cands, sel)
            if ref is not None:
                cells += [
                    ref["functional_group"],
                    _fmt_score(ref["score"]),
                    ref["vibration_mode"],
                    ref["functional_group"],
                ]
        rows.append(_row(*cells))
    return rows


def build_csv(
    peaks_df: pd.DataFrame,
    candidates: dict,
    selections: dict,
    params_pre: dict,
    params_peak: dict,
    params_match: dict,
) -> bytes:
    rows: list[list[str]] = []

    # ---- Peak Picking Parameter ----
    rows.append(_row("Peak Picking Parameter"))
    rows.append(_row("Prominence", f"{params_peak['prominence_pct']:.2f}%"))
    rows.append(
        _row(
            "Minimum Peak Height",
            f"{params_peak['min_height']:g}" if params_peak["use_min_height"] else "Not Used",
        )
    )
    rows.append(_row("Minimum Peak Spacing", f"{params_peak['min_spacing']:g}"))
    rows.append(
        _row(
            "FWHM Filter",
            f"{params_peak['fwhm_min']:g}~{params_peak['fwhm_max']:g}"
            if params_peak["use_fwhm_filter"]
            else "Not Used",
        )
    )
    if params_pre["baseline_on"]:
        rows.append(_row("Baseline Calibration Lamda", f"{params_pre['lam']:.0f}"))
        rows.append(_row("Baseline Calibration P", f"{params_pre['p']:g}"))
        rows.append(_row("Baseline Diff_Order", f"{int(params_pre['diff_order'])}"))
    else:
        rows.append(_row("Baseline Calibration Lamda", "Baseline Off"))
        rows.append(_row("Baseline Calibration P", "Baseline Off"))
        rows.append(_row("Baseline Diff_Order", "Baseline Off"))
    if params_pre["smooth_on"]:
        rows.append(_row("Smoothing Window", f"{int(params_pre['window'])}"))
        rows.append(_row("Polyorder", f"{int(params_pre['polyorder'])}"))
    else:
        rows.append(_row("Smoothing Window", "Smoothing Off"))
        rows.append(_row("Polyorder", "Smoothing Off"))
    rows.append(_row())

    # ---- Peak Annotation Parameter ----
    rows.append(_row("Peak Annotation Parameter"))
    rows.append(_row("w_f", f"{params_match['w_f']:g}"))
    rows.append(_row("Tolerance Scale", f"{params_match['scale']:g}"))
    rows.append(_row("Score Threshold", f"{params_match['threshold']:g}"))
    rows.append(_row("k_pos", f"{params_match['k_pos']:g}"))
    rows.append(_row("k_fwhm", f"{params_match['k_fwhm']:g}"))
    rows.append(_row())

    # ---- Annotation Result ----
    rows.append(_row("Annotation Result"))
    rows.append(list(RESULT_HEADER))
    rows.extend(result_rows(peaks_df, candidates, selections))

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")


def build_png(wavenumber, transmittance, peaks_df: pd.DataFrame) -> bytes:
    """原始 %T 光譜＋峰位數字標註（不含 annotation 文字），300 dpi。"""
    wn = np.asarray(wavenumber, dtype=float)
    tr = np.asarray(transmittance, dtype=float)

    fig, ax = plt.subplots(figsize=(11, 5), dpi=300)
    ax.plot(wn, tr, lw=0.9, color="#1f4e79")

    for _, pk in peaks_df.iterrows():
        i = int(np.argmin(np.abs(wn - pk["position"])))
        ax.plot(wn[i], tr[i], marker="v", ms=3, color="#c00000", zorder=3)
        ax.annotate(
            f"{pk['position']:.0f}",
            xy=(wn[i], tr[i]),
            xytext=(0, -6),
            textcoords="offset points",
            rotation=90,
            ha="center",
            va="top",
            fontsize=6.5,
            color="#333333",
        )

    ax.set_xlabel("Wavenumber (cm$^{-1}$)")
    ax.set_ylabel("Transmittance (%)")
    ax.invert_xaxis()
    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin - 0.16 * (ymax - ymin), ymax)  # 預留下方標籤空間
    ax.margins(x=0.01)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
