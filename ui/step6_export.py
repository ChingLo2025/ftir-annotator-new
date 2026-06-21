"""Step 6 — 匯出 CSV 與 PNG。"""
import streamlit as st

from core.export import build_csv, build_png


def render():
    st.header("Step 6 — 匯出結果")

    spec = st.session_state.spectrum
    wn = spec["df"]["wavenumber"].values
    tr = spec["df"]["transmittance"].values
    peaks_df = st.session_state.get("_peaks_df")
    candidates = st.session_state.get("_candidates")
    selections = st.session_state.selections

    if peaks_df is None or candidates is None:
        st.error("資料遺失，請重新從 Step 3 開始。")
        return

    # Build outputs
    csv_bytes = build_csv(
        peaks_df,
        candidates,
        selections,
        st.session_state.params_pre,
        st.session_state.params_peak,
        st.session_state.params_match,
    )
    png_bytes = build_png(wn, tr, peaks_df)

    # Download buttons
    dl_csv, dl_png = st.columns(2)
    with dl_csv:
        st.download_button(
            "📄 下載標註結果 CSV",
            data=csv_bytes,
            file_name="ftir_annotation.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
        )
    with dl_png:
        st.download_button(
            "🖼 下載光譜圖 PNG",
            data=png_bytes,
            file_name="ftir_spectrum.png",
            mime="image/png",
            use_container_width=True,
        )

    # PNG preview
    st.image(png_bytes, caption="光譜圖預覽（300 dpi，匯出後可放大）", use_container_width=True)

    # Summary metrics
    st.subheader("標註摘要")
    all_pids = [int(pk["peak_id"]) for _, pk in peaks_df.iterrows()]
    annotated = sum(
        1 for pid in all_pids if candidates.get(pid) and selections.get(pid) is not None
    )
    not_annotated = sum(
        1 for pid in all_pids if candidates.get(pid) and selections.get(pid) is None
    )
    unassigned = sum(1 for pid in all_pids if not candidates.get(pid))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("峰總數", len(all_pids))
    m2.metric("已標註", annotated)
    m3.metric("不標註", not_annotated)
    m4.metric("Unassigned", unassigned)

    st.divider()
    if st.button("← Back"):
        st.session_state.step = 5
        st.rerun()
