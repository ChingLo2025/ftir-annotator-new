"""Shared UI widgets — pairs sliders with number_input boxes for manual entry."""
from __future__ import annotations

import streamlit as st


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def paired_slider(
    label: str,
    min_value,
    max_value,
    default,
    step,
    key: str,
    help: str | None = None,
    fmt: str | None = None,
    ratio: tuple[int, int] = (3, 1),
):
    """Slider + number_input pair sharing state via callbacks."""
    sl_key = f"_psl_{key}"
    nu_key = f"_pnu_{key}"
    if sl_key not in st.session_state:
        st.session_state[sl_key] = default
        st.session_state[nu_key] = default

    def _from_sl():
        st.session_state[nu_key] = st.session_state[sl_key]

    def _from_nu():
        v = _clamp(st.session_state[nu_key], min_value, max_value)
        st.session_state[nu_key] = v
        st.session_state[sl_key] = v

    c1, c2 = st.columns(ratio)
    with c1:
        st.slider(
            label,
            min_value=min_value,
            max_value=max_value,
            step=step,
            key=sl_key,
            on_change=_from_sl,
            help=help,
        )
    with c2:
        st.markdown("<div style='height:1.85rem'></div>", unsafe_allow_html=True)
        st.number_input(
            f"num_{key}",
            min_value=min_value,
            max_value=max_value,
            step=step,
            key=nu_key,
            on_change=_from_nu,
            label_visibility="collapsed",
            format=fmt,
        )
    return st.session_state[sl_key]


def paired_range_slider(
    label: str,
    min_value,
    max_value,
    default: tuple,
    step,
    key: str,
    help: str | None = None,
    ratio: tuple[int, int, int] = (3, 1, 1),
):
    """Range slider + two number_inputs (min/max), state shared via callbacks."""
    sl_key = f"_psl_{key}"
    lo_key = f"_pnu_lo_{key}"
    hi_key = f"_pnu_hi_{key}"
    if sl_key not in st.session_state:
        st.session_state[sl_key] = default
        st.session_state[lo_key] = default[0]
        st.session_state[hi_key] = default[1]

    def _from_sl():
        lo, hi = st.session_state[sl_key]
        st.session_state[lo_key] = lo
        st.session_state[hi_key] = hi

    def _from_nu():
        lo = _clamp(st.session_state[lo_key], min_value, max_value)
        hi = _clamp(st.session_state[hi_key], min_value, max_value)
        if lo > hi:
            lo, hi = hi, lo
        st.session_state[lo_key] = lo
        st.session_state[hi_key] = hi
        st.session_state[sl_key] = (lo, hi)

    c1, c2, c3 = st.columns(ratio)
    with c1:
        st.slider(
            label,
            min_value=min_value,
            max_value=max_value,
            step=step,
            key=sl_key,
            on_change=_from_sl,
            help=help,
        )
    with c2:
        st.markdown("<div style='height:1.85rem'></div>", unsafe_allow_html=True)
        st.number_input(
            f"lo_{key}",
            min_value=min_value,
            max_value=max_value,
            step=step,
            key=lo_key,
            on_change=_from_nu,
            label_visibility="collapsed",
        )
    with c3:
        st.markdown("<div style='height:1.85rem'></div>", unsafe_allow_html=True)
        st.number_input(
            f"hi_{key}",
            min_value=min_value,
            max_value=max_value,
            step=step,
            key=hi_key,
            on_change=_from_nu,
            label_visibility="collapsed",
        )
    return st.session_state[sl_key]


