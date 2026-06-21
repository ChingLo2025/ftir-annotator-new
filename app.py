"""FTIR Auto-Annotation Tool — Streamlit 入口（規格書 v1.2.1）。"""
import streamlit as st

from core import matching, peak_picking, preprocess

st.set_page_config(page_title="FTIR Auto-Annotator", layout="wide")

STEP_NAMES = [
    "1. 載入光譜",
    "2. 選擇資料庫",
    "3. Peak Picking",
    "4. 預覽",
    "5. 確認",
    "6. 匯出",
]


def _init_state():
    defaults: dict = {
        "step": 1,
        "spectrum": None,
        "database": None,
        "params_pre": preprocess.DEFAULTS.copy(),
        "params_peak": peak_picking.DEFAULTS.copy(),
        "params_match": matching.DEFAULTS.copy(),
        "selections": {},
        "_warn_back": False,
        "_peaks_df": None,
        "_candidates": None,
        "_preprocess_result": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _progress_strip():
    step = st.session_state.step
    cols = st.columns(6)
    for i, (col, name) in enumerate(zip(cols, STEP_NAMES), 1):
        with col:
            if i == step:
                st.markdown(f"**:blue[{name}]**")
            elif i < step:
                st.markdown(f":gray[✓ {name}]")
            else:
                st.markdown(f":gray[{name}]")


_init_state()

st.title("FTIR Auto-Annotation Tool")
_progress_strip()
st.divider()

_step = st.session_state.step

if _step == 1:
    from ui import step1_spectrum
    step1_spectrum.render()
elif _step == 2:
    from ui import step2_database
    step2_database.render()
elif _step == 3:
    from ui import step3_processing
    step3_processing.render()
elif _step == 4:
    from ui import step4_preview
    step4_preview.render()
elif _step == 5:
    from ui import step5_confirm
    step5_confirm.render()
elif _step == 6:
    from ui import step6_export
    step6_export.render()
