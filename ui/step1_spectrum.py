"""Step 1 — 載入 FTIR 光譜 CSV。"""
import streamlit as st
import plotly.graph_objects as go
from core.data_io import load_spectrum, FormatError


def render():
    st.header("Step 1 — 載入 FTIR 光譜")

    uploaded = st.file_uploader(
        "上傳光譜 CSV（請使用PerkinElmer預設輸出格式，第二列為cm-1,%T，第三列起為data）",
        type="csv",
        key="s1_upload",
    )

    if uploaded is not None:
        raw = uploaded.read()
        try:
            df, meta = load_spectrum(raw)
            st.session_state.spectrum = {"df": df, "meta": meta}
            if meta["n_duplicates_merged"] > 0:
                st.info(f"已合併 {meta['n_duplicates_merged']} 個重複波數（取平均）。")
        except FormatError as e:
            st.error(str(e))
            st.session_state.spectrum = None

    spec = st.session_state.get("spectrum")

    if spec is not None:
        meta = spec["meta"]
        df = spec["df"]
        st.success(
            f"已載入：{meta['n_points']} 點，範圍 {meta['wn_min']:.0f}–{meta['wn_max']:.0f} cm⁻¹"
        )
        with st.expander("Instrument metadata", expanded=False):
            st.text(meta["metadata_line"])

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df["wavenumber"],
                y=df["transmittance"],
                mode="lines",
                name="Spectrum",
                line=dict(color="#1f4e79", width=1),
            )
        )
        fig.update_xaxes(autorange="reversed", title="Wavenumber (cm⁻¹)")
        fig.update_yaxes(title="Transmittance (%)")
        fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=350)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    _, right = st.columns([9, 1])
    with right:
        if st.button(
            "Next →",
            type="primary",
            disabled=(spec is None),
            use_container_width=True,
        ):
            st.session_state.step = 2
            st.rerun()
