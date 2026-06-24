"""Step 4 — Annotation Preview."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import matching, peak_picking, preprocess
from ui._widgets import paired_slider


def render():
    st.header("Step 4 — Annotation Preview")

    spec = st.session_state.spectrum
    wn = spec["df"]["wavenumber"].values
    tr = spec["df"]["transmittance"].values
    db_df = st.session_state.database["df"]
    pm = st.session_state.params_match

    # Recompute peaks with current params
    result = preprocess.run(wn, tr, st.session_state.params_pre)
    peaks_df = peak_picking.pick_peaks(wn, result["y_processed"], st.session_state.params_peak)

    # ── Matching parameter controls ───────────────────────────────────────────
    with st.expander("Matching Parameters (auto-recalculates)", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            pm["w_f"] = paired_slider(
                "w_f (FWHM Weight)", 0.0, 1.0, float(pm["w_f"]), 0.05, key="pm_wf",
                help="Weight of FWHM similarity in the total score. Larger = FWHM match is more important. Smaller = peak position match dominates.",
                ratio=(2, 1),
            )
        with c2:
            pm["scale"] = paired_slider(
                "Tolerance Scale", 0.5, 3.0, float(pm["scale"]), 0.1, key="pm_scale",
                help="Scales all matching tolerance windows proportionally. Larger = more lenient matching (wider search radius). Smaller = stricter position and FWHM requirements.",
                ratio=(2, 1),
            )
        with c3:
            pm["threshold"] = paired_slider(
                "Score Threshold", 0.0, 1.0, float(pm["threshold"]), 0.05, key="pm_thr",
                help="Minimum score required for a candidate to be auto-assigned in Step 5. Larger = only high-confidence matches are auto-assigned. Smaller = more peaks receive an auto-assignment.",
                ratio=(2, 1),
            )
        with c4:
            pm["k_position"] = paired_slider(
                "k_position", 1.0, 5.0, float(pm["k_position"]), 0.5, key="pm_kpos",
                help="Hard cutoff multiplier for position scoring. Score drops linearly beyond the tolerance window and reaches zero at k_position × tolerance. Larger = wider acceptable range. Smaller = score drops to zero sooner.",
                ratio=(2, 1),
            )
        with c5:
            pm["k_fwhm"] = paired_slider(
                "k_fwhm", 1.0, 6.0, float(pm["k_fwhm"]), 0.5, key="pm_kfwhm",
                help="Hard cutoff multiplier for FWHM scoring. Score drops linearly beyond the FWHM tolerance and reaches zero at k_fwhm × tolerance. Larger = wider acceptable FWHM range. Smaller = stricter FWHM requirement.",
                ratio=(2, 1),
            )

    # ── Run matching ──────────────────────────────────────────────────────────
    candidates = matching.match_peaks(peaks_df, db_df, pm)

    # ── Plotly chart ──────────────────────────────────────────────────────────
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=wn, y=tr, mode="lines", name="Spectrum",
            line=dict(color="#1f4e79", width=1),
        )
    )

    for _, pk in peaks_df.iterrows():
        pid = int(pk["peak_id"])
        cands = candidates.get(pid, [])
        pk_tr = float(np.interp(pk["position"], wn, tr))

        if not cands:
            color = "#aaaaaa"
            hover = "Unassigned"
        else:
            best = cands[0]
            color = "#c00000"
            hover = (
                f"#{best['rank']} {best['functional_group']}<br>"
                f"{best['vibration_mode']}<br>S={best['score']:.3f}"
            )

        fig.add_trace(
            go.Scatter(
                x=[pk["position"]],
                y=[pk_tr],
                mode="markers+text",
                showlegend=False,
                marker=dict(symbol="triangle-down", color=color, size=8),
                text=[str(int(round(pk["position"])))],
                textposition="bottom center",
                textfont=dict(size=8, color=color),
                hovertext=hover,
                hoverinfo="x+y+text",
            )
        )

    fig.update_xaxes(autorange="reversed", title="Wavenumber (cm⁻¹)")
    fig.update_yaxes(title="Transmittance (%)")
    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=400)
    st.plotly_chart(fig, use_container_width=True)

    # ── Candidate table ───────────────────────────────────────────────────────
    st.subheader("候選清單（所有峰）")
    rows = []
    for _, pk in peaks_df.iterrows():
        pid = int(pk["peak_id"])
        cands = candidates.get(pid, [])
        pos = int(round(pk["position"]))
        if not cands:
            rows.append(
                {
                    "峰 #": pid,
                    "位置 (cm⁻¹)": pos,
                    "排名": "-",
                    "Functional Group": "Unassigned",
                    "Vibration Mode": "-",
                    "Score (S)": "-",
                    "Score Pos": "-",
                    "Score FWHM": "-",
                }
            )
        else:
            for c in cands:
                rows.append(
                    {
                        "峰 #": pid,
                        "位置 (cm⁻¹)": pos,
                        "排名": c["rank"],
                        "Functional Group": c["functional_group"],
                        "Vibration Mode": c["vibration_mode"],
                        "Score (S)": f"{c['score']:.3f}",
                        "Score Pos": f"{c['score_pos']:.3f}",
                        "Score FWHM": (
                            f"{c['score_fwhm']:.3f}" if c["score_fwhm"] is not None else "-"
                        ),
                    }
                )

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Store for Step 5
    st.session_state["_peaks_df"] = peaks_df
    st.session_state["_candidates"] = candidates

    st.divider()
    left, _, right = st.columns([1, 8, 1])
    with left:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 3
            st.rerun()
    with right:
        if st.button("Next →", type="primary", use_container_width=True):
            # Initialize per-peak selections using current matching results
            sel: dict[int, int | None] = {}
            for _, pk in peaks_df.iterrows():
                pid = int(pk["peak_id"])
                sel[pid] = matching.default_selection(
                    candidates.get(pid, []), pm["threshold"]
                )
            st.session_state.selections = sel
            # Clear any stale Step-5 selectbox keys so they re-init from new sel
            for key in list(st.session_state.keys()):
                if key.startswith("s5_sel_"):
                    del st.session_state[key]
            st.session_state.step = 5
            st.rerun()
