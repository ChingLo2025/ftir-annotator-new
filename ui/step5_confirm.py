"""Step 5 — 逐峰確認 Annotation（下拉單選）。"""
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from core import matching


def _auto_sel(peaks_df, candidates, threshold):
    """重新計算自動建議選擇（{peak_id: rank|None}）。"""
    return {
        int(pk["peak_id"]): matching.default_selection(
            candidates.get(int(pk["peak_id"]), []), threshold
        )
        for _, pk in peaks_df.iterrows()
    }


def _reset_selectbox_keys(peaks_df, candidates, sel):
    """刪除所有 s5_sel_* 鍵，讓下次 render 以 sel dict 重新初始化。"""
    for _, pk in peaks_df.iterrows():
        pid = int(pk["peak_id"])
        st.session_state.pop(f"s5_sel_{pid}", None)


_STICKY_CSS = """
<style>
section[data-testid="stMain"] div[data-testid="stVerticalBlock"]
    > div[data-testid="stElementContainer"]:has(> div > div > div[data-testid="stPlotlyChart"]),
section[data-testid="stMain"] div[data-testid="stVerticalBlock"]
    > div[data-testid="element-container"]:has(> div > div > div[data-testid="stPlotlyChart"]),
section[data-testid="stMain"] div[data-testid="stVerticalBlock"]
    > div:has(> div > div[data-testid="stPlotlyChart"]) {
    position: sticky;
    top: 3rem;
    z-index: 999;
    background: white;
    padding-top: 0.4rem;
    padding-bottom: 0.4rem;
    box-shadow: 0 4px 6px -3px rgba(0,0,0,0.12);
}
</style>
"""


def render():
    st.header("Step 5 — Annotation Confirmation")
    st.markdown(_STICKY_CSS, unsafe_allow_html=True)

    # ── Step 5 → Step 4 警告 ──────────────────────────────────────────────────
    if st.session_state.get("_warn_back", False):
        st.warning(
            "返回後目前所有 annotation 選擇將遺失，並重設為預設值。確認返回？"
        )
        c1, c2, *_ = st.columns([1.2, 1, 8])
        with c1:
            if st.button("確認返回", type="primary"):
                st.session_state.selections = {}
                st.session_state["_warn_back"] = False
                st.session_state.step = 4
                st.rerun()
        with c2:
            if st.button("取消"):
                st.session_state["_warn_back"] = False
                st.rerun()
        return  # 不繼續渲染其他內容

    peaks_df = st.session_state.get("_peaks_df")
    candidates = st.session_state.get("_candidates")
    if peaks_df is None or candidates is None:
        st.error("資料遺失，請重新從 Step 3 開始。")
        return

    sel: dict[int, int | None] = st.session_state.selections
    pm = st.session_state.params_match
    auto = _auto_sel(peaks_df, candidates, pm["threshold"])

    # ── 快捷按鈕 ──────────────────────────────────────────────────────────────
    ba, bb, _ = st.columns([1.6, 2.2, 6])
    with ba:
        if st.button("全部採用第一名"):
            new_sel = {
                int(pk["peak_id"]): (1 if candidates.get(int(pk["peak_id"])) else None)
                for _, pk in peaks_df.iterrows()
            }
            st.session_state.selections = new_sel
            _reset_selectbox_keys(peaks_df, candidates, new_sel)
            st.rerun()
    with bb:
        if st.button("全部重設為自動建議"):
            new_sel = _auto_sel(peaks_df, candidates, pm["threshold"])
            st.session_state.selections = new_sel
            _reset_selectbox_keys(peaks_df, candidates, new_sel)
            st.rerun()

    # ── Plotly 光譜（反映目前選擇） ───────────────────────────────────────────
    spec = st.session_state.spectrum
    wn = spec["df"]["wavenumber"].values
    tr = spec["df"]["transmittance"].values

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
        current_rank = sel.get(pid)

        if not cands:
            color = "#aaaaaa"   # Unassigned
        elif current_rank is None:
            color = "#aaaaaa"   # 不標註
        elif sel.get(pid) != auto.get(pid):
            color = "#e07b00"   # 用戶手動修改（橘色強調）
        else:
            color = "#c00000"   # 正常

        # Hover 文字
        if cands and current_rank is not None:
            chosen = cands[current_rank - 1]
            hover = f"{chosen['functional_group']} | S={chosen['score']:.2f}"
        elif not cands:
            hover = "Unassigned"
        else:
            hover = "不標註"

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
    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=370)
    st.plotly_chart(fig, use_container_width=True)

    # ── 逐峰確認列 ────────────────────────────────────────────────────────────
    st.subheader("逐峰選擇")

    for _, pk in peaks_df.iterrows():
        pid = int(pk["peak_id"])
        cands = candidates.get(pid, [])
        pos = int(round(pk["position"]))

        hdr, info_a, info_b, ctrl = st.columns([1, 1.2, 1.2, 5])
        with hdr:
            st.markdown(f"**Peak {pid}**  \n{pos} cm⁻¹")
        with info_a:
            st.markdown(f"強度: {pk['intensity']:.1f}")
        with info_b:
            st.markdown(f"FWHM: {pk['fwhm']:.1f} cm⁻¹")
        with ctrl:
            if not cands:
                st.markdown("*Unassigned（無候選）*")
            else:
                options = [
                    f"#{c['rank']} | {c['functional_group']} – {c['vibration_mode']} (S={c['score']:.2f})"
                    for c in cands
                ]
                options.append("─── 不標註 ───")
                n_opts = len(options)
                sel_key = f"s5_sel_{pid}"

                # 首次進入（或快捷按鈕重設後）以 sel dict 初始化
                if sel_key not in st.session_state:
                    current_rank = sel.get(pid)
                    init_idx = (n_opts - 1) if current_rank is None else (current_rank - 1)
                    st.session_state[sel_key] = init_idx

                chosen_idx = st.selectbox(
                    f"peak_{pid}_label",
                    options=range(n_opts),
                    format_func=lambda i, opts=options: opts[i],
                    label_visibility="collapsed",
                    key=sel_key,
                )
                sel[pid] = None if chosen_idx == n_opts - 1 else chosen_idx + 1

        st.markdown("---")

    # 寫回 session state
    st.session_state.selections = sel

    st.divider()
    left, _, right = st.columns([1, 8, 1])
    with left:
        if st.button("← Back", use_container_width=True):
            st.session_state["_warn_back"] = True
            st.rerun()
    with right:
        if st.button("Next →", type="primary", use_container_width=True):
            st.session_state.step = 6
            st.rerun()
