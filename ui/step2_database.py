"""Step 2 — 選擇資料庫（內建或上傳）。"""
from pathlib import Path

import pandas as pd
import streamlit as st

from core.data_io import DB_DISPLAY_NAMES, FormatError, load_database

DATABASES_DIR = Path(__file__).parent.parent / "databases"


@st.cache_data
def _load_builtin(name: str) -> pd.DataFrame:
    raw = (DATABASES_DIR / name).read_bytes()
    return load_database(raw)


def render():
    st.header("Step 2 — 選擇比對資料庫")

    builtins = (
        sorted(p.name for p in DATABASES_DIR.glob("*.csv"))
        if DATABASES_DIR.exists()
        else []
    )

    source = st.radio("來源", ["內建資料庫", "上傳自訂資料庫"], horizontal=True, key="s2_source")

    db_df: pd.DataFrame | None = None
    db_name: str | None = None

    if source == "內建資料庫":
        if builtins:
            chosen = st.selectbox("選擇資料庫", builtins, key="s2_builtin_sel")
            try:
                db_df = _load_builtin(chosen)
                db_name = chosen
            except FormatError as e:
                st.error(str(e))
        else:
            st.warning("databases/ 目錄中找不到任何 CSV 檔案。")
    else:
        uploaded = st.file_uploader("上傳資料庫 CSV", type="csv", key="s2_upload")
        if uploaded is not None:
            try:
                db_df = load_database(uploaded.read())
                db_name = uploaded.name
            except FormatError as e:
                st.error(str(e))

    if db_df is not None:
        st.session_state.database = {"df": db_df, "name": db_name}
        st.success(f"已載入：{db_name}（{len(db_df)} 筆）")
        display_df = db_df.rename(columns=DB_DISPLAY_NAMES)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    db_ready = st.session_state.get("database") is not None

    st.divider()
    left, _, right = st.columns([1, 8, 1])
    with left:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with right:
        if st.button(
            "Next →",
            type="primary",
            disabled=not db_ready,
            use_container_width=True,
        ):
            st.session_state.step = 3
            st.rerun()
