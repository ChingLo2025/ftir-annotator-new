"""Step 3 — 前處理參數與 Peak Picking。"""
import math

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from core import peak_picking, preprocess
from ui._widgets import paired_range_slider, paired_slider


def render():
    st.header("Step 3 — 前處理與 Peak Picking")

    spec = st.session_state.spectrum
    wn = spec["df"]["wavenumber"].values
    tr = spec["df"]["transmittance"].values

    pp = st.session_state.params_pre
    pk = st.session_state.params_peak

    wn_lo = float(np.min(wn))
    wn_hi = float(np.max(wn))

    # Backfill mask defaults for older sessions
    for k, v in peak_picking.DEFAULTS.items():
        pk.setdefault(k, v)

    ctrl_col, chart_col = st.columns([1, 3])

    # ── Left: controls ────────────────────────────────────────────────────────
    with ctrl_col:
        st.subheader("Preprocessing")

        pp["baseline_on"] = st.checkbox(
            "Baseline Correction (ALS)",
            value=pp["baseline_on"],
            help="Removes slowly varying baseline drift. Larger λ = smoother, more global correction. Smaller λ = more local, follows the spectrum more closely.",
        )
        if pp["baseline_on"]:
            log_lam = paired_slider(
                "log₁₀(λ)",
                min_value=3.0,
                max_value=9.0,
                default=float(math.log10(max(1.0, float(pp["lam"])))),
                step=0.5,
                key="pp_loglam",
                help="Smoothness of the baseline (log scale). λ = 10^value. Larger = smoother baseline. Smaller = baseline follows local features.",
                fmt="%.2f",
            )
            pp["lam"] = float(10 ** log_lam)
            pp["p"] = paired_slider(
                "p",
                min_value=0.001,
                max_value=0.1,
                default=float(pp["p"]),
                step=0.001,
                key="pp_p",
                help="Asymmetry parameter. Smaller = baseline stays below peaks. Larger = baseline tracks the signal more symmetrically.",
                fmt="%.4f",
            )
            pp["diff_order"] = st.radio(
                "Diff Order",
                [1, 2, 3],
                index=int(pp["diff_order"]) - 1,
                horizontal=True,
                help="Derivative order for the penalty term. Higher = penalises curvature more strongly, producing a flatter baseline.",
            )

        st.markdown("---")

        pp["smooth_on"] = st.checkbox(
            "Smoothing (Savitzky-Golay)",
            value=pp["smooth_on"],
            help="Reduces noise while preserving peak shape. Larger window = more smoothing (may broaden peaks). Smaller window = less smoothing (more noise retained).",
        )
        if pp["smooth_on"]:
            raw_w = int(pp["window"])
            init_w = raw_w if raw_w % 2 == 1 else raw_w + 1
            pp["window"] = paired_slider(
                "Window Length (odd)",
                min_value=5,
                max_value=51,
                default=init_w,
                step=2,
                key="pp_window",
                help="Width of the smoothing window (must be odd). Larger = more noise reduction but can broaden peaks. Smaller = preserves narrow peaks but retains more noise.",
            )
            pp["polyorder"] = paired_slider(
                "Polyorder",
                min_value=2,
                max_value=5,
                default=int(pp["polyorder"]),
                step=1,
                key="pp_polyorder",
                help="Polynomial order for curve fitting within the window. Higher = better peak shape preservation. Lower = more aggressive smoothing.",
            )

        st.markdown("---")
        st.subheader("Peak Picking")

        pk["prominence_pct"] = paired_slider(
            "Prominence (%)",
            min_value=0.05,
            max_value=20.0,
            default=float(pk["prominence_pct"]),
            step=0.05,
            key="pk_prom",
            help="Minimum peak prominence relative to the signal range. Larger = only tall, distinct peaks detected. Smaller = more peaks detected (including noise peaks).",
        )
        pk["use_min_height"] = st.checkbox(
            "Enable Min Peak Height",
            value=pk["use_min_height"],
            help="Toggle filtering by absolute peak height. Enable to exclude weak peaks below a set threshold.",
        )
        if pk["use_min_height"]:
            pk["min_height"] = st.number_input(
                "Min Height",
                value=float(pk["min_height"]),
                min_value=0.0,
                step=0.5,
                help="Minimum absolute intensity of a peak (inverted signal). Larger = only stronger peaks accepted. Smaller = weaker peaks also included.",
            )
        pk["min_spacing"] = paired_slider(
            "Min Peak Spacing (cm⁻¹)",
            min_value=0.0,
            max_value=50.0,
            default=float(pk["min_spacing"]),
            step=1.0,
            key="pk_spacing",
            help="Minimum distance between two adjacent peaks. Larger = fewer peaks (nearby peaks merged into one). Smaller = more peaks detected separately.",
        )
        pk["use_fwhm_filter"] = st.checkbox(
            "FWHM Filter",
            value=pk["use_fwhm_filter"],
            help="Filter peaks by full-width at half-maximum (peak width). Excludes peaks that are too narrow or too broad.",
        )
        if pk["use_fwhm_filter"]:
            fmin, fmax = paired_range_slider(
                "FWHM Range (cm⁻¹)",
                min_value=0.0,
                max_value=500.0,
                default=(float(pk["fwhm_min"]), float(pk["fwhm_max"])),
                step=1.0,
                key="pk_fwhm",
                help="Allowed range of FWHM values. Peaks outside this range are excluded.",
            )
            pk["fwhm_min"] = fmin
            pk["fwhm_max"] = fmax

        st.markdown("---")
        st.subheader("Masks")
        st.caption("Exclude wavenumber regions from peak picking (e.g. atmospheric CO₂).")

        pk["masks_enable"] = st.checkbox(
            "Enable Masks",
            value=pk.get("masks_enable", False),
            help="When enabled, peaks within the specified wavenumber ranges are removed from the peak list.",
        )
        if pk["masks_enable"]:
            pk["masks_n"] = st.radio(
                "Number of Masks",
                [1, 2],
                index=int(pk.get("masks_n", 1)) - 1,
                horizontal=True,
            )
            for i in range(1, int(pk["masks_n"]) + 1):
                st.markdown(f"**Mask {i}**")
                cur_lo = float(pk.get(f"mask{i}_lo", 0.0))
                cur_hi = float(pk.get(f"mask{i}_hi", 0.0))
                if not (wn_lo <= cur_lo <= wn_hi):
                    cur_lo = wn_lo
                if not (wn_lo <= cur_hi <= wn_hi):
                    cur_hi = wn_lo
                mc1, mc2 = st.columns(2)
                with mc1:
                    pk[f"mask{i}_lo"] = st.number_input(
                        f"Mask {i} min (cm⁻¹)",
                        value=cur_lo,
                        min_value=wn_lo,
                        max_value=wn_hi,
                        step=1.0,
                        key=f"mask_{i}_lo_input",
                    )
                with mc2:
                    pk[f"mask{i}_hi"] = st.number_input(
                        f"Mask {i} max (cm⁻¹)",
                        value=cur_hi,
                        min_value=wn_lo,
                        max_value=wn_hi,
                        step=1.0,
                        key=f"mask_{i}_hi_input",
                    )

    # ── Right: chart ──────────────────────────────────────────────────────────
    with chart_col:
        result = preprocess.run(wn, tr, pp)
        peaks_df = peak_picking.pick_peaks(wn, result["y_processed"], pk)
        masks = peak_picking.active_masks(pk)

        fig = go.Figure()
        for lo, hi in masks:
            fig.add_vrect(
                x0=lo, x1=hi,
                fillcolor="rgba(160,160,160,0.25)",
                line_width=0,
                layer="below",
                annotation_text="Mask",
                annotation_position="top left",
                annotation_font_size=10,
            )
        fig.add_trace(
            go.Scatter(
                x=wn, y=tr, mode="lines", name="原始 %T",
                line=dict(color="#1f4e79", width=1),
            )
        )
        if preprocess.is_active(pp):
            fig.add_trace(
                go.Scatter(
                    x=wn, y=result["t_processed"], mode="lines", name="處理後 %T",
                    line=dict(color="#e06c00", width=1, dash="dash"),
                )
            )

        if len(peaks_df) > 0:
            pk_wn = peaks_df["position"].values
            pk_tr = np.interp(pk_wn, wn, tr)
            fig.add_trace(
                go.Scatter(
                    x=pk_wn,
                    y=pk_tr,
                    mode="markers+text",
                    name="Peaks",
                    marker=dict(symbol="triangle-down", color="#c00000", size=8),
                    text=[str(int(round(p))) for p in pk_wn],
                    textposition="bottom center",
                    textfont=dict(size=9),
                    hovertemplate="%{x:.0f} cm⁻¹<extra></extra>",
                )
            )

        fig.update_xaxes(autorange="reversed", title="Wavenumber (cm⁻¹)")
        fig.update_yaxes(title="Transmittance (%)")
        fig.update_layout(
            margin=dict(l=0, r=0, t=30, b=0),
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        st.plotly_chart(fig, use_container_width=True)

        n_peaks = len(peaks_df)
        if n_peaks == 0:
            st.warning("未偵測到任何峰，請嘗試降低 Prominence 或調整其他參數。")
        else:
            st.caption(f"偵測到 **{n_peaks}** 個峰")

    # Peak list table (full width)
    if len(peaks_df) > 0:
        display = peaks_df.rename(
            columns={
                "peak_id": "#",
                "position": "位置 (cm⁻¹)",
                "intensity": "強度（反轉）",
                "fwhm": "FWHM (cm⁻¹)",
                "prominence": "Prominence",
            }
        ).set_index("#")
        display["位置 (cm⁻¹)"] = display["位置 (cm⁻¹)"].round(1)
        display["強度（反轉）"] = display["強度（反轉）"].round(2)
        display["FWHM (cm⁻¹)"] = display["FWHM (cm⁻¹)"].round(2)
        display["Prominence"] = display["Prominence"].round(3)
        st.dataframe(display, use_container_width=True)

    # Store for downstream steps
    st.session_state["_peaks_df"] = peaks_df
    st.session_state["_preprocess_result"] = result

    st.divider()
    left, _, right = st.columns([1, 8, 1])
    with left:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with right:
        if st.button(
            "Next →",
            type="primary",
            disabled=(len(peaks_df) == 0),
            use_container_width=True,
        ):
            st.session_state.step = 4
            st.rerun()
