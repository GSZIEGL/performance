# performance_app_v2_0_hu.py
# AI-assisted Performance Recommendation System - magyar Streamlit MVP
# Upload -> standardizálás -> KPI-k -> szabályalapú insightok -> coach-friendly javaslatok -> Excel/Word/PDF export

from __future__ import annotations

import html
import io
import hashlib
import os
import json
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    from docx import Document
    from docx.shared import Inches, Pt
except Exception:
    Document = None

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except Exception:
    SimpleDocTemplate = None
    pdfmetrics = None
    TTFont = None


try:
    from supabase import create_client
except Exception:
    create_client = None

FPI_IMPORT_ENGINE_VERSION = "FPI_TACTICAL_MERGE_V072_TACTICAL_PDF_HELPER_FIX_2026_06_17"

# -----------------------------------------------------------------------------
# Oldalbeállítás
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Football Performance Intelligence",
    page_icon="⚽",
    layout="wide",
)

st.markdown(
    """
    <style>
    .insight-card {
        border-radius: 16px;
        padding: 18px 20px;
        margin-bottom: 16px;
        background: rgba(31, 41, 55, 0.72);
        border: 1px solid rgba(255,255,255,0.10);
        box-shadow: 0 6px 18px rgba(0,0,0,0.12);
    }
    .insight-title {
        font-size: 1.15rem;
        font-weight: 800;
        margin-bottom: 6px;
    }
    .pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
        margin-right: 8px;
    }
    .pill-critical { background:#7f1d1d; color:#fecaca; }
    .pill-warning { background:#78350f; color:#fde68a; }
    .pill-info { background:#1e3a8a; color:#bfdbfe; }
    .insight-label { font-weight: 800; margin-top: 10px; }
    .insight-text { line-height: 1.45; margin-bottom: 6px; }
    .wrap-table table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    .wrap-table th, .wrap-table td {
        border: 1px solid rgba(255,255,255,0.12);
        padding: 10px;
        vertical-align: top;
        white-space: normal !important;
        overflow-wrap: break-word;
        word-break: normal;
        font-size: 0.92rem;
    }
    .wrap-table th { background: rgba(30, 64, 175, 0.60); font-weight: 800; }
    .wrap-table tr:nth-child(even) { background: rgba(255,255,255,0.03); }
    .priority-card {
        border-radius: 16px;
        padding: 16px 18px;
        margin-bottom: 12px;
        background: rgba(17, 24, 39, 0.78);
        border-left: 7px solid #22c55e;
        box-shadow: 0 6px 18px rgba(0,0,0,0.10);
    }
    .micro-pill {
        display: inline-block;
        padding: 6px 10px;
        border-radius: 10px;
        background: rgba(59,130,246,.18);
        border: 1px solid rgba(147,197,253,.22);
        margin: 3px;
        font-weight: 700;
    }

    .score-card {
        border-radius: 18px;
        padding: 18px 20px;
        margin-bottom: 14px;
        background: linear-gradient(135deg, rgba(15,23,42,.92), rgba(30,41,59,.82));
        border: 1px solid rgba(148,163,184,.22);
        box-shadow: 0 8px 24px rgba(0,0,0,.14);
    }
    .score-number {
        font-size: 2.4rem;
        font-weight: 900;
        line-height: 1;
    }
    .score-label {
        color: #e0f2fe;
        font-weight: 800;
        margin-top: 6px;
    }
    .mini-muted {
        color: #dbeafe;
        font-size: .92rem;
        line-height: 1.35;
    }

    .hero-box {border-radius:24px;padding:24px 28px;margin-bottom:20px;background:radial-gradient(circle at top left,rgba(34,197,94,.22),transparent 34%),radial-gradient(circle at bottom right,rgba(59,130,246,.24),transparent 30%),linear-gradient(135deg,rgba(2,6,23,.96),rgba(15,23,42,.88));border:1px solid rgba(148,163,184,.22);box-shadow:0 18px 45px rgba(0,0,0,.28)}
    .hero-title {font-size:2.1rem;font-weight:950;letter-spacing:-.04em;margin-bottom:4px}.hero-sub{color:#dbeafe;font-size:1.02rem;line-height:1.45}
    .premium-kpi{border-radius:20px;padding:18px;background:linear-gradient(145deg,rgba(15,23,42,.94),rgba(30,41,59,.78));border:1px solid rgba(148,163,184,.20);box-shadow:0 10px 28px rgba(0,0,0,.18);min-height:120px}
    .premium-kpi-label{color:#dbeafe;font-size:.86rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em}.premium-kpi-value{font-size:2rem;font-weight:950;margin-top:8px;line-height:1}.premium-kpi-note{color:#dbeafe;font-size:.86rem;margin-top:9px}
    .risk-high{border-left:8px solid #ef4444!important}.risk-medium{border-left:8px solid #f59e0b!important}.risk-low{border-left:8px solid #22c55e!important}
    .section-chip{display:inline-block;padding:5px 11px;border-radius:999px;background:rgba(34,197,94,.15);border:1px solid rgba(34,197,94,.25);color:#bbf7d0;font-weight:850;margin:2px 4px 8px 0}

    .intro-card {
        border-radius: 22px;
        padding: 22px 24px;
        margin-bottom: 16px;
        background: linear-gradient(135deg, rgba(15,23,42,.95), rgba(30,41,59,.82));
        border: 1px solid rgba(148,163,184,.24);
        box-shadow: 0 12px 34px rgba(0,0,0,.20);
    }
    .intro-card h2, .intro-card h3 {
        margin-top: 0;
        margin-bottom: 8px;
    }
    .intro-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 14px;
        margin-top: 14px;
    }
    .feature-box {
        border-radius: 18px;
        padding: 16px 18px;
        background: rgba(15,23,42,.72);
        border: 1px solid rgba(148,163,184,.18);
    }
    .feature-title {
        font-weight: 900;
        font-size: 1.02rem;
        margin-bottom: 6px;
        color: #bfdbfe;
    }
    .feature-text {
        color: #e0f2fe;
        line-height: 1.45;
        font-size: .94rem;
    }
    .export-panel {
        border-radius: 22px;
        padding: 20px;
        background: radial-gradient(circle at top right, rgba(34,197,94,.16), transparent 35%),
                    linear-gradient(135deg, rgba(2,6,23,.94), rgba(15,23,42,.86));
        border: 1px solid rgba(148,163,184,.24);
        margin-bottom: 18px;
    }
   
 .fpi-clean-card {
   border-radius: 20px;
   padding: 18px 20px;
   background: #ffffff;
   color: #0f172a;
   border: 1px solid #e2e8f0;
   box-shadow: 0 10px 28px rgba(15,23,42,.08);
   margin-bottom: 14px;
 }
 .fpi-dark-card {
   border-radius: 20px;
   padding: 18px 20px;
   background: linear-gradient(135deg,#0f172a,#1e293b);
   color: #f8fafc;
   border: 1px solid rgba(148,163,184,.28);
   box-shadow: 0 14px 36px rgba(15,23,42,.22);
   margin-bottom: 14px;
 }
 .fpi-muted { color:#64748b; }
 .fpi-dark-card .fpi-muted { color:#cbd5e1; }
 .export-panel p, .export-panel div, .export-panel h3 { color: #f8fafc; }
 .feature-box, .intro-card, .score-card, .priority-card, .insight-card { color: #f8fafc; }
 .feature-text, .mini-muted { color: #dbeafe !important; }


 /* ===== FPI WOW UI refresh ===== */
 .stApp {
   background:
     radial-gradient(circle at 10% 5%, rgba(34,197,94,.18), transparent 28%),
     radial-gradient(circle at 90% 0%, rgba(59,130,246,.20), transparent 30%),
     linear-gradient(135deg, #020617 0%, #0f172a 52%, #111827 100%);
 }
 .block-container { padding-top: 1.1rem; padding-bottom: 2rem; }
 .fpi-hero-wow {
   border-radius: 30px; padding: 28px 30px; margin: 8px 0 22px 0;
   background: radial-gradient(circle at top left, rgba(34,197,94,.30), transparent 34%),
               radial-gradient(circle at bottom right, rgba(59,130,246,.34), transparent 30%),
               linear-gradient(135deg, rgba(15,23,42,.98), rgba(30,41,59,.86));
   border: 1px solid rgba(226,232,240,.18);
   box-shadow: 0 24px 70px rgba(0,0,0,.35);
   color: #f8fafc;
 }
 .fpi-hero-wow h1 { margin: 0; font-size: 2.55rem; line-height: 1; letter-spacing: -0.055em; font-weight: 950; }
 .fpi-hero-wow p { margin: 10px 0 0 0; color: #cbd5e1; font-size: 1.02rem; line-height: 1.45; }
 .fpi-chip-row { margin-top: 16px; }
 .fpi-chip-wow {
   display: inline-block; padding: 7px 12px; margin: 4px 6px 0 0; border-radius: 999px;
   background: rgba(15,23,42,.55); border: 1px solid rgba(148,163,184,.28);
   color: #dbeafe; font-weight: 800; font-size: .86rem;
 }
 .fpi-summary-card {
   border-radius: 24px; padding: 20px 22px; margin: 10px 0 18px 0;
   background: rgba(248,250,252,.97); color: #0f172a;
   border: 1px solid rgba(226,232,240,.95); box-shadow: 0 18px 46px rgba(15,23,42,.18);
 }
 .fpi-summary-card h3 { margin: 0 0 10px 0; font-size: 1.18rem; font-weight: 950; color: #0f172a; }
 .fpi-summary-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 14px; margin-top: 12px; }
 .fpi-summary-item { border-radius: 16px; padding: 12px 13px; background: #f8fafc; border: 1px solid #e2e8f0; }
 .fpi-summary-label { font-size: .75rem; text-transform: uppercase; letter-spacing: .06em; color: #64748b; font-weight: 900; margin-bottom: 4px; }
 .fpi-summary-value { color: #0f172a; font-weight: 800; line-height: 1.35; }
 .fpi-action-card {
   border-radius: 20px; padding: 16px 18px; margin: 12px 0;
   background: linear-gradient(135deg, #ecfdf5, #eff6ff);
   color: #0f172a; border: 1px solid #bfdbfe; box-shadow: 0 10px 28px rgba(37,99,235,.12);
 }
 .fpi-action-card b { color:#0f172a; }
 .fpi-kpi-panel {
   border-radius: 22px; padding: 17px 18px;
   background: linear-gradient(145deg, rgba(255,255,255,.98), rgba(239,246,255,.96));
   color: #0f172a; border: 1px solid rgba(219,234,254,.95);
   box-shadow: 0 14px 34px rgba(15,23,42,.14); min-height: 118px;
 }
 .fpi-kpi-panel .label { color: #64748b; font-size: .78rem; font-weight: 900; text-transform: uppercase; letter-spacing: .07em; }
 .fpi-kpi-panel .value { color: #0f172a; font-size: 2.05rem; font-weight: 950; letter-spacing: -.04em; margin-top: 6px; }
 .fpi-kpi-panel .note { color: #475569; font-size: .86rem; margin-top: 5px; line-height: 1.35; }
 .fpi-section-title { color: #f8fafc; font-size: 1.35rem; font-weight: 950; margin: 22px 0 10px 0; letter-spacing: -.03em; }
 .insight-card, .priority-card, .score-card, .intro-card, .feature-box, .export-panel { color: #f8fafc !important; }
 .feature-text, .mini-muted, .premium-kpi-note, .hero-sub { color: #dbeafe !important; }


 /* ===== FPI contrast/readability fix ===== */
 html, body, .stApp, [data-testid="stAppViewContainer"] {
   color: #f8fafc !important;
 }
 [data-testid="stSidebar"] {
   background: linear-gradient(180deg, #020617, #0f172a) !important;
 }
 [data-testid="stSidebar"] * {
   color: #f8fafc !important;
 }
 .stMarkdown, .stText, p, span, label, div {
   text-rendering: optimizeLegibility;
 }
 .fpi-hero-wow,
 .fpi-hero-wow *,
 .fpi-dark-card,
 .fpi-dark-card *,
 .fpi-glass,
 .fpi-glass *,
 .intro-card,
 .intro-card *,
 .feature-box,
 .feature-box *,
 .score-card,
 .score-card *,
 .priority-card,
 .priority-card *,
 .insight-card,
 .insight-card *,
 .export-panel,
 .export-panel * {
   color: #f8fafc !important;
 }
 .fpi-hero-wow p,
 .hero-sub,
 .feature-text,
 .mini-muted,
 .premium-kpi-note,
 .score-label {
   color: #dbeafe !important;
 }
 .fpi-summary-card,
 .fpi-summary-card *,
 .fpi-summary-item,
 .fpi-summary-item *,
 .fpi-action-card,
 .fpi-action-card *,
 .fpi-kpi-panel,
 .fpi-kpi-panel * {
   color: #0f172a !important;
 }
 .fpi-summary-label,
 .fpi-kpi-panel .label,
 .fpi-kpi-panel .note,
 .fpi-muted {
   color: #475569 !important;
 }
 .fpi-chip-wow,
 .section-chip,
 .micro-pill {
   color: #f8fafc !important;
   background: rgba(15,23,42,.78) !important;
   border-color: rgba(226,232,240,.32) !important;
 }
 .pill-critical { background:#991b1b !important; color:#ffffff !important; }
 .pill-warning { background:#92400e !important; color:#ffffff !important; }
 .pill-info { background:#1d4ed8 !important; color:#ffffff !important; }
 .wrap-table th {
   background: #1e3a8a !important;
   color: #ffffff !important;
 }
 .wrap-table td {
   color: #f8fafc !important;
   background: rgba(15,23,42,.72) !important;
 }
 .wrap-table tr:nth-child(even) td {
   background: rgba(30,41,59,.82) !important;
 }
 .stDataFrame, .stDataFrame * {
   color: inherit;
 }
 div[data-testid="stMetricValue"] {
   color: #f8fafc !important;
 }
 div[data-testid="stMetricLabel"] {
   color: #dbeafe !important;
 }
 .stAlert, .stAlert * {
   color: #0f172a !important;
 }
 button, button * {
   font-weight: 800 !important;
 }


 /* ===== FPI tab + CTA readability fix ===== */
 button[data-baseweb="tab"] {
   color: #cbd5e1 !important;
   font-weight: 850 !important;
   opacity: 1 !important;
   background: transparent !important;
 }
 button[data-baseweb="tab"] * {
   color: #cbd5e1 !important;
   font-weight: 850 !important;
   opacity: 1 !important;
 }
 button[data-baseweb="tab"][aria-selected="true"],
 button[data-baseweb="tab"][aria-selected="true"] * {
   color: #ffffff !important;
   font-weight: 950 !important;
 }
 button[data-baseweb="tab"]:hover,
 button[data-baseweb="tab"]:hover * {
   color: #ffffff !important;
 }
 div[data-baseweb="tab-list"] {
   gap: 8px;
   background: rgba(15,23,42,.42);
   border-radius: 18px;
   padding: 8px 10px;
   border: 1px solid rgba(148,163,184,.18);
 }
 div[data-baseweb="tab-border"] {
   background-color: #ef4444 !important;
   height: 3px !important;
 }
 .stDownloadButton > button {
   background: linear-gradient(135deg,#22c55e,#16a34a) !important;
   color: #ffffff !important;
   border: 0 !important;
   border-radius: 16px !important;
   font-weight: 950 !important;
   min-height: 48px !important;
   box-shadow: 0 14px 34px rgba(34,197,94,.24) !important;
 }
 .stDownloadButton > button:hover {
   background: linear-gradient(135deg,#16a34a,#15803d) !important;
   color: #ffffff !important;
   transform: translateY(-1px);
   box-shadow: 0 18px 42px rgba(34,197,94,.32) !important;
 }
 .stDownloadButton > button * {
   color: #ffffff !important;
   font-weight: 950 !important;
 }
 .stButton > button {
   border-radius: 14px !important;
   font-weight: 900 !important;
 }
 input, textarea, [data-baseweb="input"] input {
   color: #0f172a !important;
   background: #ffffff !important;
 }
 [data-testid="stSidebar"] .stAlert,
 [data-testid="stSidebar"] .stAlert * {
   color: #0f172a !important;
 }
 [data-testid="stSidebar"] .stAlert {
   background: #dbeafe !important;
   border-radius: 14px !important;
 }


 /* ===== FPI HARD READABILITY PATCH ===== */
 :root {
   --fpi-dark: #020617;
   --fpi-panel: #0f172a;
   --fpi-panel-2: #111827;
   --fpi-white: #f8fafc;
   --fpi-muted-light: #dbeafe;
   --fpi-text-dark: #0f172a;
   --fpi-green: #22c55e;
   --fpi-blue: #2563eb;
 }

 /* Main text on dark background */
 .stApp, .stApp p, .stApp span, .stApp label, .stApp div {
   text-shadow: none !important;
 }

 /* Sidebar: everything readable */
 [data-testid="stSidebar"] {
   background: linear-gradient(180deg, #020617 0%, #0b1220 100%) !important;
 }
 [data-testid="stSidebar"] h1,
 [data-testid="stSidebar"] h2,
 [data-testid="stSidebar"] h3,
 [data-testid="stSidebar"] p,
 [data-testid="stSidebar"] label,
 [data-testid="stSidebar"] span,
 [data-testid="stSidebar"] div {
   color: #f8fafc !important;
 }

 /* Sidebar input fields */
 [data-testid="stSidebar"] input,
 [data-testid="stSidebar"] textarea,
 [data-testid="stSidebar"] [data-baseweb="input"],
 [data-testid="stSidebar"] [data-baseweb="input"] > div {
   background: #ffffff !important;
   color: #0f172a !important;
   border-color: #cbd5e1 !important;
   border-radius: 12px !important;
 }
 [data-testid="stSidebar"] input::placeholder {
   color: #64748b !important;
   opacity: 1 !important;
 }

 /* Sidebar buttons: no white-on-white */
 [data-testid="stSidebar"] .stButton > button,
 [data-testid="stSidebar"] button {
   background: linear-gradient(135deg,#2563eb,#1d4ed8) !important;
   color: #ffffff !important;
   border: 1px solid rgba(255,255,255,.25) !important;
   border-radius: 14px !important;
   font-weight: 900 !important;
   min-height: 44px !important;
 }
 [data-testid="stSidebar"] .stButton > button *,
 [data-testid="stSidebar"] button * {
   color: #ffffff !important;
   font-weight: 900 !important;
 }
 [data-testid="stSidebar"] .stButton > button:hover,
 [data-testid="stSidebar"] button:hover {
   background: linear-gradient(135deg,#1d4ed8,#1e40af) !important;
 }

 /* Alerts in sidebar */
 [data-testid="stSidebar"] .stAlert {
   background: #dbeafe !important;
   border: 1px solid #93c5fd !important;
   border-radius: 16px !important;
 }
 [data-testid="stSidebar"] .stAlert *,
 [data-testid="stSidebar"] .stAlert p,
 [data-testid="stSidebar"] .stAlert div {
   color: #0f172a !important;
 }

 /* Toggle label */
 [data-testid="stSidebar"] [data-testid="stWidgetLabel"] * {
   color: #f8fafc !important;
 }

 /* Top KPI labels: force light */
 div[data-testid="stMetric"],
 div[data-testid="stMetric"] * {
   color: #f8fafc !important;
 }
 div[data-testid="stMetricLabel"],
 div[data-testid="stMetricLabel"] *,
 div[data-testid="stMetricDelta"],
 div[data-testid="stMetricDelta"] * {
   color: #dbeafe !important;
   opacity: 1 !important;
 }
 div[data-testid="stMetricValue"],
 div[data-testid="stMetricValue"] * {
   color: #ffffff !important;
   opacity: 1 !important;
 }

 /* Weekly summary / action boxes: force light cards with dark text */
 .fpi-action-card,
 .fpi-action-card *,
 .fpi-summary-card,
 .fpi-summary-card *,
 .fpi-summary-item,
 .fpi-summary-item * {
   background-color: #f8fafc !important;
   color: #0f172a !important;
   opacity: 1 !important;
   text-shadow: none !important;
 }
 .fpi-action-card {
   background: linear-gradient(135deg,#f8fafc,#e0f2fe) !important;
   border: 1px solid #93c5fd !important;
   box-shadow: 0 18px 42px rgba(15,23,42,.24) !important;
 }
 .fpi-summary-label {
   color: #334155 !important;
 }
 .fpi-summary-value {
   color: #0f172a !important;
 }

 /* Any markdown card that has blue background but dark text */
 .stMarkdown div[style*="background"],
 .stMarkdown div[style*="background"] p,
 .stMarkdown div[style*="background"] span {
   opacity: 1 !important;
 }

 /* Tabs readable */
 button[data-baseweb="tab"],
 button[data-baseweb="tab"] *,
 [role="tab"],
 [role="tab"] * {
   color: #e2e8f0 !important;
   opacity: 1 !important;
   font-weight: 850 !important;
 }
 button[data-baseweb="tab"][aria-selected="true"],
 button[data-baseweb="tab"][aria-selected="true"] *,
 [role="tab"][aria-selected="true"],
 [role="tab"][aria-selected="true"] * {
   color: #ffffff !important;
   font-weight: 950 !important;
 }
 button[data-baseweb="tab"]:hover,
 button[data-baseweb="tab"]:hover *,
 [role="tab"]:hover,
 [role="tab"]:hover * {
   color: #ffffff !important;
 }

 /* Download buttons: strong green CTA */
 .stDownloadButton > button,
 .stDownloadButton > button * {
   background: linear-gradient(135deg,#22c55e,#16a34a) !important;
   color: #ffffff !important;
   border: none !important;
   font-weight: 950 !important;
   opacity: 1 !important;
 }
 .stDownloadButton > button {
   border-radius: 16px !important;
   min-height: 48px !important;
   box-shadow: 0 16px 36px rgba(34,197,94,.28) !important;
 }

 /* Data tables: keep default white readable */
 [data-testid="stDataFrame"] {
   background: #ffffff !important;
   color: #0f172a !important;
 }
 [data-testid="stDataFrame"] * {
   color: #0f172a !important;
 }

 /* Selectboxes / dropdowns in main */
 [data-baseweb="select"] div,
 [data-baseweb="select"] span {
   color: #0f172a !important;
 }


 /* Final direct summary readability override */
 .fpi-readable-summary, .fpi-readable-summary * {
   color: #0f172a !important;
   opacity: 1 !important;
   text-shadow: none !important;
 }
 div[style*="Heti vezetői összefoglaló"],
 div[style*="Heti vezetői összefoglaló"] * {
   color: #0f172a !important;
   opacity: 1 !important;
   text-shadow: none !important;
 }
 /* Expander / Smart mapper readable */
 div[data-testid="stExpander"] {
   background: #ffffff !important;
   border: 1px solid #cbd5e1 !important;
   border-radius: 18px !important;
 }
 div[data-testid="stExpander"],
 div[data-testid="stExpander"] *,
 div[data-testid="stExpander"] p,
 div[data-testid="stExpander"] label,
 div[data-testid="stExpander"] span {
   color: #0f172a !important;
   opacity: 1 !important;
 }
 div[data-testid="stExpander"] input,
 div[data-testid="stExpander"] textarea,
 div[data-testid="stExpander"] [data-baseweb="select"] *,
 div[data-testid="stExpander"] [data-baseweb="input"] * {
   color: #0f172a !important;
   background: #ffffff !important;
 }


 /* ===== Weekly summary final readability override ===== */
 pre, pre * {
   color: #000000 !important;
 }
 div[style*="Heti vezetői összefoglaló"],
 div[style*="Heti vezetői összefoglaló"] *,
 div[style*="border-left:10px solid #2563eb"],
 div[style*="border-left:10px solid #2563eb"] * {
   color: #000000 !important;
   opacity: 1 !important;
   text-shadow: none !important;
 }

 </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Oszlopmapping
# -----------------------------------------------------------------------------
STANDARD_COLUMNS = {
    "player_name": ["Játékos neve", "Player", "Player Name", "Name", "name", "Név", "Nev", "Játékos", "Jatekos", "Athlete", "Athlete Name", "Player full name", "Full Name"],
    "session_type": ["Típus", "Type", "Session Type", "Edzés/Meccs", "SessionType", "Activity Type", "Drill Type", "Event Type", "Training/Match"],
    "session_name": ["Szakasz neve", "Session", "Session Name", "Activity", "Drill", "Exercise", "Event", "Session title"],
    "position": ["Poszt", "Position", "Player Position", "Role", "Playing Position", "Post", "Pos"],
    "start_time": ["Kezdési idő", "Start Time", "Start", "Dátum", "Date", "Session Date", "Day", "Datum", "Kezdés", "Start date", "StartTime", "Split"],
    "end_time": ["Befejezési idő", "End Time", "End", "Finish", "Befejezés", "EndTime"],
    "duration": ["Időtartam", "Duration", "Time", "Minutes", "Idő", "Időtartam [perc]", "Duration [min]", "Duration min"],
    "match_minutes": ["Játékperc", "Játékpercek", "Meccsperc", "Meccspercek", "Minutes played", "Minutes Played", "Playing Time", "Match Minutes", "Match minutes", "Player minutes", "On pitch minutes"],
    "total_distance": ["Teljes táv [m]", "Tel\xadjes táv [m]", "Total Distance", "Distance", "Össztáv", "Total distance (m)", "Total Dist", "Dist Total", "Distance [m]", "TD", "Total Distance m"],
    "distance_per_min": ["Táv/perc [m/min]", "Distance/min", "Distance Per Min", "m/min", "Distance per minute", "m per min", "m/minute", "Rel Distance"],
    "max_speed": ["Maximális sebesség [km/h]", "Max Speed", "Maximum Speed", "Top Speed", "Peak Speed", "Max Velocity", "Vmax"],
    "avg_speed": ["Átlagsebesség [km/h]", "Average Speed", "Avg Speed", "Mean Speed"],
    "sprints": ["Sprintek", "Sprints", "Sprint Count", "Number of Sprints", "Sprint #", "Sprint efforts", "Sprints count  ()", "Sprints count"],
    "speed_zone_3": ["Táv a sebesség célzónában 3 [m] (14.40 - 19.79 km/h)"],
    "speed_zone_4": ["Táv a sebesség célzónában 4 [m] (19.80 - 24.99 km/h)", "Distance(4+5)  (m)", "Distance(4+5)", "Distance 4+5", "HSR Distance"],
    "speed_zone_5": ["Táv a sebesség célzónában 5 [m] (25.00- km/h)", "Total sprints distance  (m)", "Total sprints distance", "Sprint distance", "Sprint Distance"],
    "training_load": ["Edzési terhelési pontérték", "Terhelési pont", "Player Load", "Load", "Training Load", "Total Load", "Workload", "Load Score"],
    "cardio_load": ["Kardióterhelés", "Cardio Load"],
    "recovery_hours": ["Regenerálódási idő [h]", "Recovery Time", "Recovery"],
    "muscle_load": ["Izomterhelés", "Muscle Load", "Muscular Load", "Mechanical Load"],
    "hr_avg": ["Átlagos pulzus [bpm]", "Average HR", "Avg HR", "Mean HR", "HR avg", "Avg Heart Rate"],
    "hr_max": ["Maximális pulzus [bpm]", "Max HR", "Maximum HR", "Peak HR", "Max Heart Rate"],
    "hrv": ["HRV (RMSSD)", "HRV", "RMSSD", "HRV RMSSD"],
    "acc_low": ["Gyorsulások száma (2.00 - 2.49 m/s²)"],
    "acc_mid": ["Gyorsulások száma (2.50 - 2.99 m/s²)"],
    "acc_high": ["Gyorsulások száma (3.00 - 50.00 m/s²)", "Total Accelerations  ()", "Total Accelerations", "Accelerations (2+3)  ()", "Accelerations (2+3)"],
    "dec_low": ["Gyorsulások száma (-2.49 - -2.00 m/s²)"],
    "dec_mid": ["Gyorsulások száma (-2.99 - -2.50 m/s²)"],
    "dec_high": ["Gyorsulások száma (-50.00 - -3.00 m/s²)", "Total Decelerations  ()", "Total Decelerations", "Decelerations (2+3)  ()", "Decelerations (2+3)"],
    "high_efforts": ["High Efforts", "High Effort", "High efforts", "Nagy intenzitású erőfeszítések", "Nagy intenzitású akciók", "Explosive Efforts", "Explosive efforts", "High Intensity Efforts", "HIE", "Efforts High", "HI Efforts"],
}

CORE_REQUIRED = ["player_name", "session_type", "start_time"]
SEVERITY_RANK = {"KRITIKUS": 0, "FIGYELMEZTETÉS": 1, "INFORMÁCIÓ": 2}

METRIC_LABELS = {
    "training_load": "Terhelési pont",
    "total_distance": "Össztáv",
    "sprint_distance": "Sprinttáv",
    "hsr_distance": "Nagy sebességű táv",
    "distance_per_min": "Táv/perc",
    "max_speed": "Maximális sebesség",
    "dec_count": "Lassítások",
    "acc_count": "Gyorsulások",
    "high_efforts": "Nagy intenzitású erőfeszítések",
}

PLAYSTYLE_OPTIONS = {
    "Kiegyensúlyozott": "Általános, kiegyensúlyozott performance profil.",
    "Pressing": "Magas intenzitás, sok gyorsulás/lassítás, erős munkasűrűség.",
    "Transition": "Gyors átmenetek, magas sprint- és maximális sebességű inger igény.",
    "Possession": "Stabil volumen, kontrollált intenzitás, fenntartható terhelés.",
    "Low Block": "Rövidebb, robbanékony intenzív blokkok, kontrollált összterhelés.",
}



# -----------------------------------------------------------------------------
# Smart Mapper v2 - magyarázat és összevont GPS mezők
# -----------------------------------------------------------------------------
MAPPER_FIELD_INFO = {
    "player_name": ("Játékos neve", "A játékos azonosítója / neve.", "szöveg", "minden játékos szintű elemzés, risk motor", True),
    "session_type": ("Típus", "Az esemény típusa: Edzés vagy Meccs.", "szöveg", "edzés-meccs összevetés, readiness", True),
    "start_time": ("Kezdési idő / dátum – dátum/idő", "Az edzés vagy mérkőzés dátuma.", "dátum/idő", "heti bontás, mikrociklus, trendek", True),
    "duration": ("Időtartam", "Az esemény hossza.", "perc vagy hh:mm:ss", "táv/perc, intenzitás", False),
    "match_minutes": ("Játékperc / szereplési idő", "Meccsen ténylegesen pályán töltött perc. Ha nincs külön oszlop, az app meccsnél az időtartamot használja.", "perc vagy hh:mm:ss", "per90 normalizálás, meccs-edzés összevetés", False),
    "total_distance": ("Teljes táv", "Összes megtett távolság.", "méter", "terhelési volumen, heti load, risk", False),
    "distance_per_min": ("Táv/perc", "Relatív futóteljesítmény.", "m/perc", "meccsintenzitás, játékmodell", False),
    "max_speed": ("Maximális sebesség", "Legnagyobb elért sebesség.", "km/h", "max speed trend, frissesség", False),
    "sprints": ("Sprintek száma", "Sprint akciók darabszáma, nem méter.", "darab", "sprint expozíció", False),
    "speed_zone_4": ("Nagy sebességű futás / Zone 4 vagy 4+5", "Nagy sebességű távolság. Ha csak Distance(4+5) van, ide válaszd.", "méter", "HSR, játékmodell, load profil", False),
    "speed_zone_5": ("Sprint táv / Zone 5", "Sprint zónában megtett távolság. Ez méter, nem darabszám.", "méter", "sprintterhelés, sprint fit", False),
    "training_load": ("Edzési terhelési pont", "GPS/rendszer által számolt load pont.", "pont", "heti terhelés, risk", False),
    "muscle_load": ("Izomterhelés", "Mechanikus/izomterhelési mutató.", "pont", "neuromuszkuláris kockázat", False),
    "hr_avg": ("Átlagpulzus", "Átlagos pulzus.", "bpm", "belső terhelés", False),
    "hr_max": ("Max pulzus", "Maximális pulzus.", "bpm", "belső terhelés", False),
    "acc_high": ("Gyorsulások", "Nagy intenzitású vagy összesített gyorsulások száma.", "darab", "neuromuszkuláris terhelés", False),
    "dec_high": ("Lassítások", "Nagy intenzitású vagy összesített lassítások száma.", "darab", "excentrikus terhelés, risk", False),
    "high_efforts": ("High Efforts", "Nagy intenzitású akciók összesített mutatója.", "darab / pont", "pressing/transition profil", False),
}


def mapper_label(std_col: str) -> str:
    return MAPPER_FIELD_INFO.get(std_col, (std_col, "", "", "", False))[0]


def mapper_unit(std_col: str) -> str:
    return MAPPER_FIELD_INFO.get(std_col, ("", "", "", "", False))[2]


def mapper_desc(std_col: str) -> str:
    label, meaning, unit, used_for, required = MAPPER_FIELD_INFO.get(std_col, (std_col, "", "", "", False))
    extra = ""
    if std_col == "speed_zone_4":
        extra = " Összevont 4+5 zóna esetén ezt válaszd ide; az app HSR-ként kezeli."
    elif std_col == "speed_zone_5":
        extra = " Ide ne darabszámot válassz, hanem méter alapú sprinttávot."
    elif std_col == "sprints":
        extra = " Ide darabszám kell, nem sprinttáv méterben."
    elif std_col in ["acc_high", "dec_high"]:
        extra = " Ha csak összesített oszlop van, az is használható."
    return f"{meaning} Várt egység: {unit}. Ebből számolódik: {used_for}.{extra}"


def mapper_warning(std_col: str, source_col: object) -> str:
    s = _norm_mapping_text(source_col)
    if not s:
        return ""
    if std_col == "sprints" and any(x in s for x in ["distance", "tav", "meter", "metre"]):
        return "⚠ Sprintekhez darabszám kell, ez inkább sprinttávnak tűnik."
    if std_col == "speed_zone_5" and any(x in s for x in ["count", "darab"]):
        return "⚠ Sprint távhoz méter kell, ez inkább sprint darabszámnak tűnik."
    if std_col in ["speed_zone_4", "speed_zone_5", "total_distance"] and any(x in s for x in ["count", "darab"]):
        return "⚠ Ehhez távolság kellene, nem darabszám."
    if std_col in ["acc_high", "dec_high", "sprints"] and any(x in s for x in ["distance", "meter", "metre"]):
        return "⚠ Ehhez darabszám jellegű oszlop kellene, nem méter."
    return ""


def enhanced_mapping_quality_df(raw_df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> pd.DataFrame:
    rows = []
    for std_col, aliases in STANDARD_COLUMNS.items():
        src = mapping.get(std_col)
        score = smart_column_score(src, std_col, aliases) if src else 0
        required = MAPPER_FIELD_INFO.get(std_col, ("", "", "", "", std_col in CORE_REQUIRED))[4]
        rows.append({
            "App mező": mapper_label(std_col),
            "Technikai mező": std_col,
            "Mit jelent?": mapper_desc(std_col),
            "Várt egység": mapper_unit(std_col),
            "Kiválasztott Excel oszlop": src or "",
            "Bizonyosság": score,
            "Kötelező": "igen" if required else "nem",
            "Figyelmeztetés": mapper_warning(std_col, src),
        })
    return pd.DataFrame(rows)


def mapping_compatibility_score(mapping: Dict[str, Optional[str]]) -> Tuple[int, List[str]]:
    weights = {
        "player_name": 20, "session_type": 15, "start_time": 15,
        "total_distance": 8, "duration": 5, "distance_per_min": 7,
        "max_speed": 8, "sprints": 5, "speed_zone_4": 5,
        "speed_zone_5": 7, "training_load": 5, "match_minutes": 4, "acc_high": 3,
        "dec_high": 3, "high_efforts": 4,
    }
    total = sum(weights.values())
    got = 0
    missing = []
    for k, w in weights.items():
        if mapping.get(k):
            got += w
        else:
            missing.append(mapper_label(k))
    return int(round(got / total * 100)), missing


def render_mapping_score(mapping: Dict[str, Optional[str]]) -> None:
    score, missing = mapping_compatibility_score(mapping)
    if score >= 85:
        st.success(f"GPS fájl kompatibilitás: {score}% – nagyon jó")
    elif score >= 65:
        st.warning(f"GPS fájl kompatibilitás: {score}% – használható, de néhány mező hiányzik")
    else:
        st.error(f"GPS fájl kompatibilitás: {score}% – javítsd a mappinget")
    if missing:
        st.caption("Hiányzó fontos mezők: " + ", ".join(missing[:8]) + ("..." if len(missing) > 8 else ""))


def normalize_combined_fields(out: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> pd.DataFrame:
    """Összevont GPS mezők kezelése, pl. Distance(4+5).
    Ha csak 4+5 oszlop van, azt HSR-ként használjuk. A sprint distance ilyenkor becslés,
    de az eredeti összevont értéket nem duplázzuk a HSR számításnál.
    """
    out = out.copy()
    src_z4 = str(mapping.get("speed_zone_4") or "").lower()
    src_z5 = str(mapping.get("speed_zone_5") or "").lower()
    combined_45 = any(x in src_z4 for x in ["4+5", "hsr", "high speed"])
    out["combined_zone_4_5_used"] = bool(combined_45)

    if "speed_zone_4" not in out.columns:
        out["speed_zone_4"] = 0
    if "speed_zone_5" not in out.columns:
        out["speed_zone_5"] = 0

    z5_missing = out["speed_zone_5"].fillna(0).sum() == 0
    if z5_missing and combined_45 and out["speed_zone_4"].fillna(0).sum() > 0:
        out["speed_zone_5"] = out["speed_zone_4"] * 0.30
        out["estimated_sprint_distance"] = True
    else:
        out["estimated_sprint_distance"] = False

    # HSR: külön z4+z5 esetén összeg, összevont 4+5 esetén maga az összevont oszlop.
    if combined_45:
        out["hsr_distance"] = out["speed_zone_4"]
    else:
        out["hsr_distance"] = out[["speed_zone_4", "speed_zone_5"]].sum(axis=1, min_count=1)
    out["sprint_distance"] = out["speed_zone_5"]
    return out

# -----------------------------------------------------------------------------
# V4.5 - Smart Mapper fallback helpers
# -----------------------------------------------------------------------------
def _norm_mapping_text(text: object) -> str:
    import unicodedata
    text = str(text or "").lower().replace("\u00ad", " ")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def smart_column_score(source_col: object, std_col: str, aliases: List[str]) -> int:
    src = _norm_mapping_text(source_col)
    if not src:
        return 0
    alias_norms = [_norm_mapping_text(a) for a in aliases] + [_norm_mapping_text(std_col)]
    best = 0
    for a in alias_norms:
        if not a:
            continue
        if src == a:
            best = max(best, 100)
        elif src.replace(" ", "") == a.replace(" ", ""):
            best = max(best, 96)
        elif a in src or src in a:
            best = max(best, 86 if len(a) >= 4 else 70)
        else:
            src_tokens = set(src.split())
            a_tokens = set(a.split())
            if src_tokens and a_tokens:
                overlap = len(src_tokens & a_tokens) / max(1, len(a_tokens))
                best = max(best, int(overlap * 78))
    hints = {
        "player_name": ["player", "jatekos", "nev", "name", "athlete"],
        "session_type": ["type", "tipus", "match", "game", "training", "edzes", "meccs"],
        "start_time": ["date", "datum", "start", "day", "ido"],
        "duration": ["duration", "minutes", "perc", "time"],
        "match_minutes": ["minutes played", "match minutes", "jatekp", "jatekperc", "meccsperc", "playing time"],
        "total_distance": ["distance", "tav", "dist", "total"],
        "distance_per_min": ["min", "minute", "rel", "per"],
        "max_speed": ["max", "speed", "velocity", "vmax"],
        "sprints": ["sprint"],
        "training_load": ["load", "terheles", "workload"],
        "speed_zone_4": ["zone 4", "z4", "19", "24", "hsr"],
        "speed_zone_5": ["zone 5", "z5", "25", "sprint distance"],
        "acc_high": ["acc", "acceleration", "gyorsulas", "3"],
        "dec_high": ["dec", "deceleration", "lassitas", "-3"],
        "high_efforts": ["high effort", "effort"],
    }
    if std_col in hints:
        hit = sum(1 for h in hints[std_col] if h in src)
        if hit:
            best = max(best, min(94, 58 + hit * 14))
    return int(best)

def suggest_mapping(raw_df: pd.DataFrame) -> Dict[str, Optional[str]]:
    suggestions: Dict[str, Optional[str]] = {}
    used = set()
    for std_col, aliases in STANDARD_COLUMNS.items():
        scored = []
        for c in raw_df.columns:
            if c in used:
                continue
            scored.append((smart_column_score(c, std_col, aliases), c))
        scored.sort(reverse=True, key=lambda x: x[0])
        if scored and scored[0][0] >= 58:
            suggestions[std_col] = scored[0][1]
            used.add(scored[0][1])
        else:
            suggestions[std_col] = None
    return suggestions

def mapping_quality_df(raw_df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> pd.DataFrame:
    rows = []
    for std_col, aliases in STANDARD_COLUMNS.items():
        src = mapping.get(std_col)
        score = smart_column_score(src, std_col, aliases) if src else 0
        rows.append({
            "Standard mező": std_col,
            "Felismert forrásoszlop": src or "",
            "Bizonyosság": score,
            "Kötelező": "igen" if std_col in CORE_REQUIRED else "nem",
            "Magyar név": METRIC_LABELS.get(std_col, std_col),
        })
    return pd.DataFrame(rows)

def export_mapping_profile(mapping: Dict[str, Optional[str]], profile_name: str = "GPS mapping profil") -> bytes:
    payload = {
        "profile_name": profile_name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mapping": mapping,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

def load_mapping_profile(uploaded_file) -> Dict[str, Optional[str]]:
    try:
        payload = json.loads(uploaded_file.read().decode("utf-8"))
        return payload.get("mapping", {})
    except Exception:
        return {}

@dataclass
class Insight:
    title: str
    severity: str
    observation: str
    impact: str
    recommendation: str
    scope: str = "Csapat"

    def as_dict(self) -> Dict[str, str]:
        return {
            "Súlyosság": self.severity,
            "Terület": self.scope,
            "Megállapítás": self.title,
            "Mit látunk?": self.observation,
            "Miért fontos?": self.impact,
            "Javaslat": self.recommendation,
        }


# -----------------------------------------------------------------------------
# Segédfüggvények
# -----------------------------------------------------------------------------
def clean_col_name(col: object) -> str:
    if col is None:
        return ""
    return str(col).replace("\u00ad", "").strip()


def find_column(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    cleaned = {clean_col_name(c).lower(): c for c in df.columns}
    for alias in aliases:
        key = clean_col_name(alias).lower()
        if key in cleaned:
            return cleaned[key]

    # óvatos fuzzy fallback
    for alias in aliases:
        a = clean_col_name(alias).lower()
        for c in df.columns:
            cc = clean_col_name(c).lower()
            if a and (a in cc or cc in a):
                return c
    return None


def to_numeric(series: pd.Series) -> pd.Series:
    if series.dtype == object:
        return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False), errors="coerce")
    return pd.to_numeric(series, errors="coerce")


def duration_to_minutes(x) -> float:
    if pd.isna(x):
        return np.nan
    if isinstance(x, pd.Timedelta):
        return x.total_seconds() / 60
    if hasattr(x, "hour") and hasattr(x, "minute") and hasattr(x, "second"):
        return x.hour * 60 + x.minute + x.second / 60
    if isinstance(x, str):
        try:
            td = pd.to_timedelta(x)
            return td.total_seconds() / 60
        except Exception:
            return np.nan
    if isinstance(x, (int, float, np.number)):
        # Excel időtört: 0.5 = 12 óra
        if float(x) < 2:
            return float(x) * 24 * 60
        return float(x)
    return np.nan


def normalize_session_type(x: object) -> str:
    text = str(x).strip().lower()
    if "meccs" in text or "match" in text or "game" in text or "mérk" in text:
        return "Meccs"
    if "edzés" in text or "training" in text or "train" in text:
        return "Edzés"
    return str(x).strip() if str(x).strip() else "Ismeretlen"



def _plausible_datetime(dt: object) -> Optional[pd.Timestamp]:
    """Csak életszerű sportadat-dátumot enged át. Mezszám/ID ne lehessen év."""
    try:
        ts = pd.to_datetime(dt, errors="coerce", dayfirst=True)
        if pd.isna(ts):
            return None
        if 2015 <= int(ts.year) <= 2035:
            return ts
    except Exception:
        return None
    return None


def extract_date_from_text(text: object) -> Optional[pd.Timestamp]:
    """Dátum kinyerése szövegből, de csak valódi dátummintából.

    Fontos: a puszta számokat (pl. mezszám: 49, 9946) nem értelmezzük dátumként.
    Ez akadályozza meg a 9946-W01 típusú hibás hetek képződését.
    """
    s = str(text or "").strip()
    if not s or s.lower() in ["nan", "none", "nat"]:
        return None

    # Puszta szám nem dátum, kivéve Excel serial tartomány.
    if re.fullmatch(r"\d+(\.\d+)?", s):
        try:
            val = float(s)
            if 25000 < val < 90000:
                return _plausible_datetime(pd.to_datetime(val, unit="D", origin="1899-12-30", errors="coerce"))
        except Exception:
            pass
        return None

    patterns = [
        (r"(20\d{2})[-._/ ](\d{1,2})[-._/ ](\d{1,2})", "ymd"),
        (r"(\d{1,2})[-._/ ](\d{1,2})[-._/ ](20\d{2})", "dmy"),
    ]
    for pat, mode in patterns:
        m = re.search(pat, s)
        if m:
            try:
                if mode == "ymd":
                    return _plausible_datetime(f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}")
                return _plausible_datetime(f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}")
            except Exception:
                pass

    # 02.01. jellegű lapnév / split. Csak akkor, ha tényleg dátumszerű pontozás van benne.
    m = re.search(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(?!\d)", s)
    if m:
        year = datetime.now().year
        return _plausible_datetime(f"{year}-{int(m.group(2)):02d}-{int(m.group(1)):02d}")

    # Általános parser csak akkor, ha van benne dátumelválasztó vagy hónap/év jelleg.
    if not re.search(r"[-./:]|20\d{2}", s):
        return None
    return _plausible_datetime(pd.to_datetime(s, errors="coerce", dayfirst=True))


def parse_datetime_series(series: pd.Series, fallback_source: Optional[pd.Series] = None, sheet_name: str = "") -> pd.Series:
    """Robusztus, de védett dátumfelismerés.

    Sorrend:
    1) Ha az oszlop eleve dátum/datetime, azt használja.
    2) Szöveges dátumokat parse-ol.
    3) Csak sikertelen esetben néz Split/lapnév fallbacket.
    4) 2015-2035 közötti dátumokat fogad el.
    """
    n = len(series) if series is not None else (len(fallback_source) if fallback_source is not None else 0)
    if series is None:
        base = pd.Series([pd.NaT] * n)
    else:
        # Excel/pandas datetime oszlopnál ez a legfontosabb út: ne fusson rá text-rescue.
        base = pd.to_datetime(series, errors="coerce", dayfirst=True)
        base = base.apply(lambda x: _plausible_datetime(x) if pd.notna(x) else pd.NaT)

        success_rate = float(base.notna().mean()) if len(base) else 0.0
        if success_rate < 0.60:
            text_parsed = series.apply(extract_date_from_text)
            text_parsed = pd.to_datetime(text_parsed, errors="coerce")
            if len(text_parsed) and text_parsed.notna().mean() > success_rate:
                base = base.fillna(text_parsed)

    if fallback_source is not None and (len(base) == 0 or base.notna().mean() < 0.60):
        fallback = fallback_source.apply(extract_date_from_text)
        fallback = pd.to_datetime(fallback, errors="coerce")
        base = base.fillna(fallback)

    if len(base) and base.notna().mean() < 0.60:
        sheet_dt = extract_date_from_text(sheet_name)
        if sheet_dt is not None and pd.notna(sheet_dt):
            base = base.fillna(sheet_dt)

    return pd.to_datetime(base, errors="coerce")


def make_iso_week_series(dt_series: pd.Series) -> pd.Series:
    """Egységes ISO hét címke: 2025-W29.

    V6.2 WEEK RESCUE:
    - csak a dátumrészt használja, az időpontot figyelmen kívül hagyja;
    - ha egy rövid, összefüggő dátumtartományból irreálisan sok hét keletkezne,
      akkor a teljes blokkot a kezdődátum ISO hetére menti.
    Ez védi az appot attól, hogy egymás utáni napokat külön heteknek vegyen,
    ha a dátumcellában időpont vagy extra szöveg is szerepel.
    """
    dts = pd.to_datetime(dt_series, errors="coerce")
    date_only = dts.dt.normalize() if hasattr(dts, "dt") else pd.to_datetime(dts, errors="coerce")
    weeks = date_only.apply(lambda x: f"{int(x.isocalendar().year)}-W{int(x.isocalendar().week):02d}" if pd.notna(x) else np.nan)

    valid = date_only.dropna()
    if len(valid) >= 2:
        span_days = int((valid.max() - valid.min()).days)
        unique_weeks = weeks.dropna().nunique()
        if span_days <= 10 and unique_weeks > 3:
            anchor = valid.min()
            rescue_week = f"{int(anchor.isocalendar().year)}-W{int(anchor.isocalendar().week):02d}"
            weeks = weeks.where(date_only.isna(), rescue_week)
            st.session_state["week_rescue_applied"] = {
                "reason": "short_date_span_many_weeks",
                "span_days": span_days,
                "original_unique_weeks": int(unique_weeks),
                "rescued_week": rescue_week,
                "date_min": str(valid.min()),
                "date_max": str(valid.max()),
            }
        else:
            st.session_state["week_rescue_applied"] = {
                "reason": "not_needed",
                "span_days": span_days,
                "unique_weeks": int(unique_weeks),
                "date_min": str(valid.min()),
                "date_max": str(valid.max()),
            }
    return weeks


def sheet_is_likely_helper(sheet_name: str, raw_df: Optional[pd.DataFrame] = None) -> bool:
    """Segédlapok kizárása az összesített adatlapból."""
    name = _norm_mapping_text(sheet_name)
    helper_tokens = [
        "dashboard", "riport", "report", "summary", "osszefoglalo", "összefoglaló",
        "benchmark", "benchmarks", "mapping", "mapper", "settings", "beallitas",
        "útmutató", "utmutato", "guide", "help", "readme", "sablon", "template",
        "pivot", "chart", "diagram", "grafikon", "calc", "szamitas", "reference",
        "lista", "players", "jatekoslista", "metadata"
    ]
    if any(tok in name for tok in helper_tokens):
        return True
    if raw_df is None or raw_df.empty:
        return True
    sample = " ".join([str(x).lower() for x in raw_df.head(8).fillna("").astype(str).values.ravel()[:200]])
    data_hints = ["name", "player", "játékos", "jatekos", "total distance", "teljes táv", "duration", "split", "date", "dátum", "datum"]
    return sum(1 for h in data_hints if h in sample) < 2

def detect_header_row(raw_df: pd.DataFrame) -> Optional[int]:
    """Általános fejlécfelismerés GPS/Excel exportokhoz.

    Nem fix sorra épít. Az első 50 sort pontozza magyar és angol GPS kulcsszavak alapján.
    Így működik akkor is, ha a fejléc az első sorban van (MegyeI.xlsx Data lap), és akkor is,
    ha néhány üres/logó/meta sor előzi meg.
    """
    if raw_df is None or raw_df.empty:
        return None

    header_keywords = {
        "player": ["jatekos", "játékos", "player", "athlete", "name", "nev", "név"],
        "date": ["kezdesi ido", "kezdési idő", "start time", "session date", "date", "datum", "dátum", "split"],
        "type": ["tipus", "típus", "session type", "type", "training", "match", "edzes", "edzés", "meccs"],
        "duration": ["idotartam", "időtartam", "duration", "minutes", "time"],
        "distance": ["teljes tav", "teljes táv", "total distance", "distance", "dist", "tav perc", "táv perc"],
        "speed": ["maximalis sebesseg", "maximális sebesség", "max speed", "top speed", "velocity"],
        "load": ["edzesi terheles", "edzési terhelés", "training load", "player load", "workload", "load"],
        "intensity": ["sprintek", "sprints", "gyorsulas", "gyorsulás", "lassitas", "lassítás", "high efforts"],
    }

    max_scan = min(50, len(raw_df))
    best_i: Optional[int] = None
    best_score = -999

    for i in range(max_scan):
        row = raw_df.iloc[i].tolist()
        cells = [str(v).strip() for v in row if str(v).strip().lower() not in ["nan", "none", ""]]
        if not cells:
            continue
        joined_raw = " | ".join(cells)
        joined_norm = _norm_mapping_text(joined_raw)

        score = 0
        matched_groups = 0
        for _, kws in header_keywords.items():
            if any(_norm_mapping_text(k) in joined_norm for k in kws):
                score += 10
                matched_groups += 1

        # A fejléc többnyire sok szöveges cellát tartalmaz, kevés tiszta számot.
        numeric_like = sum(1 for c in cells if re.fullmatch(r"\d+(\.\d+)?", c))
        text_like = len(cells) - numeric_like
        if text_like >= 4:
            score += 8
        if numeric_like > max(3, text_like):
            score -= 18

        # Következő sorban legyen valamennyi adat, különben lehet címblokk.
        if i + 1 < len(raw_df):
            next_vals = [str(v).strip() for v in raw_df.iloc[i + 1].tolist() if str(v).strip().lower() not in ["nan", "none", ""]]
            if len(next_vals) >= 3:
                score += 4

        if matched_groups >= 2 and score > best_score:
            best_score = score
            best_i = i

    return best_i if best_score >= 24 else None

def normalize_uploaded_sheet(raw_df: pd.DataFrame, sheet_name: str = "") -> pd.DataFrame:
    """Egy munkalap megtisztítása az app számára.
    Kezeli:
    - üres első sor
    - 2. sorban lévő fejléc
    - több meccslap
    - hiányzó Típus / Kezdési idő / Szakasz neve mező
    """
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()

    df = raw_df.copy()

    # 1) Ha header=None-ból jön, keressük meg a valódi fejlécsort.
    header_row = detect_header_row(df)
    if header_row is not None:
        new_cols = []
        for j, x in enumerate(df.iloc[header_row].tolist()):
            name = clean_col_name(x)
            new_cols.append(name if name and name.lower() not in ["nan", "none"] else f"col_{j+1}")
        df = df.iloc[header_row + 1:].copy()
        df.columns = new_cols
    else:
        # 2) Ha mégis header=0 jelleggel jönne.
        df.columns = [clean_col_name(c) if clean_col_name(c) else f"col_{i+1}" for i, c in enumerate(df.columns)]

    # Üres és Unnamed oszlopok törlése.
    df = df.dropna(how="all")
    keep_cols = []
    for c in df.columns:
        cs = str(c).strip()
        if not cs:
            continue
        if cs.startswith("Unnamed"):
            continue
        if cs.lower() in ["nan", "none"]:
            continue
        keep_cols.append(c)
    df = df[keep_cols] if keep_cols else df

    # Cellák whitespace tisztítása szöveges oszlopokban.
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].apply(lambda x: str(x).strip() if pd.notna(x) else x)

    # Tipikus GPS-export: Name nevű oszlop legyen biztosan felismerhető.
    # Nem nevezzük át player_name-re itt, csak adunk magyar alias oszlopot, ha kell.
    if "Name" in df.columns and "Játékos neve" not in df.columns:
        df["Játékos neve"] = df["Name"]

    # Ha nincs típus, ebből a workbookból ez meccsadat.
    if not any(c in df.columns for c in ["Típus", "Type", "Session Type", "Edzés/Meccs"]):
        df["Típus"] = "Meccs"

    if not any(c in df.columns for c in ["Szakasz neve", "Session Name", "Session"]):
        df["Szakasz neve"] = sheet_name or "GPS mérkőzés"

    # Kezdési idő kinyerése Splitből vagy lapnévből, ha nincs explicit dátum.
    has_start = any(c in df.columns for c in ["Kezdési idő", "Start Time", "Start", "Date", "Dátum", "Session Date"])
    if not has_start:
        dates = []
        split_col = "Split" if "Split" in df.columns else None
        for _, row in df.iterrows():
            dt = extract_date_from_text(row.get(split_col, "")) if split_col else None
            if dt is None or pd.isna(dt):
                dt = extract_date_from_text(sheet_name)
            if dt is None or pd.isna(dt):
                dt = pd.to_datetime("2026-01-01")
            dates.append(dt.strftime("%Y-%m-%d 17:00"))
        df["Kezdési idő"] = dates

    return df


def prepare_uploaded_sheets(sheets: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Munkalapok normalizálása.
    - Data/adat lap elsődleges és első helyen jelenik meg.
    - Segédlapok nem kerülnek az összesített adatlapba.
    - Ha van Data lap, az lesz a default; ha nincs, csak a valószínű adatlapok összesülnek.
    """
    prepared: Dict[str, pd.DataFrame] = {}
    relevant_frames: List[pd.DataFrame] = []
    data_like_names = []

    def is_data_sheet_name(n: str) -> bool:
        nn = _norm_mapping_text(n)
        return nn in ["data", "adat", "adatok", "gps data", "gps", "raw data", "nyers adat", "nyers adatok"]

    ordered_items = sorted(sheets.items(), key=lambda kv: (0 if is_data_sheet_name(kv[0]) else 1, kv[0]))
    for name, raw in ordered_items:
        clean = normalize_uploaded_sheet(raw, name)
        if clean is None or clean.empty:
            continue
        prepared[name] = clean
        if not sheet_is_likely_helper(name, raw):
            relevant_frames.append(clean)
            data_like_names.append(name)

    final: Dict[str, pd.DataFrame] = {}
    data_names = [n for n in prepared if is_data_sheet_name(n)]
    if data_names:
        # Data lap legyen az elsődleges: a felhasználó ezt látja elsőként.
        for n in data_names:
            final[n] = prepared[n]
        # Az összesített lap csak releváns adatlapokból épül, segédlapok nélkül.
        frames = [prepared[n] for n in data_like_names if n in prepared]
        if frames:
            final["Összes releváns adatlap"] = pd.concat(frames, ignore_index=True)
    elif relevant_frames:
        final["Összes releváns adatlap"] = pd.concat(relevant_frames, ignore_index=True)

    for name, df_sheet in prepared.items():
        if name not in final:
            final[name] = df_sheet
    return final if final else sheets

@st.cache_data(show_spinner=False)
def read_excel_all(file) -> Dict[str, pd.DataFrame]:
    # header=None kell, mert sok GPS exportnál az első sor üres,
    # a valódi fejléc a 2. sorban van.
    return pd.read_excel(file, sheet_name=None, header=None)


def standardize_dataframe(raw: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Optional[str]], List[str]]:
    df = raw.copy()
    df.columns = [clean_col_name(c) for c in df.columns]

    mapping: Dict[str, Optional[str]] = {}
    out = pd.DataFrame()

    for std_col, aliases in STANDARD_COLUMNS.items():
        source = find_column(df, aliases)
        mapping[std_col] = source
        if source is not None:
            out[std_col] = df[source]

    # GPS export fallback: ha van Name oszlop, az legyen játékosnév.
    if "player_name" not in out.columns and "Name" in df.columns:
        out["player_name"] = df["Name"]
        mapping["player_name"] = "Name"
    if "session_type" not in out.columns and "Típus" in df.columns:
        out["session_type"] = df["Típus"]
        mapping["session_type"] = "Típus"
    if "start_time" not in out.columns and "Kezdési idő" in df.columns:
        out["start_time"] = df["Kezdési idő"]
        mapping["start_time"] = "Kezdési idő"

    missing_core = [c for c in CORE_REQUIRED if c not in out.columns]
    if missing_core:
        return out, mapping, missing_core

    out["player_name"] = out["player_name"].astype(str).str.strip()
    out["session_type"] = out["session_type"].apply(normalize_session_type)
    fallback_source = df["Split"] if "Split" in df.columns else None
    out["start_time"] = parse_datetime_series(out["start_time"], fallback_source=fallback_source)
    out["session_date"] = out["start_time"].dt.date
    out["week"] = make_iso_week_series(out["start_time"])

    if "duration" in out.columns:
        out["duration_min"] = out["duration"].apply(duration_to_minutes)
    else:
        out["duration_min"] = np.nan

    numeric_cols = [
        "total_distance", "distance_per_min", "max_speed", "avg_speed", "sprints", "match_minutes",
        "speed_zone_3", "speed_zone_4", "speed_zone_5", "training_load", "cardio_load",
        "recovery_hours", "muscle_load", "hr_avg", "hr_max", "hrv", "high_efforts", "acc_low", "acc_mid",
        "acc_high", "dec_low", "dec_mid", "dec_high",
    ]
    for col in numeric_cols:
        if col in out.columns:
            out[col] = to_numeric(out[col])

    for col in ["speed_zone_3", "speed_zone_4", "speed_zone_5", "acc_low", "acc_mid", "acc_high", "dec_low", "dec_mid", "dec_high"]:
        if col not in out.columns:
            out[col] = 0

    out["hsr_distance"] = out[["speed_zone_4", "speed_zone_5"]].sum(axis=1, min_count=1)
    out["sprint_distance"] = out["speed_zone_5"]
    out["acc_count"] = out[["acc_low", "acc_mid", "acc_high"]].sum(axis=1, min_count=1)
    out["dec_count"] = out[["dec_low", "dec_mid", "dec_high"]].sum(axis=1, min_count=1)
    if "high_efforts" not in out.columns or out["high_efforts"].isna().all():
        out["high_efforts"] = out[["acc_mid", "acc_high", "dec_mid", "dec_high"]].sum(axis=1, min_count=1)
    else:
        out["high_efforts"] = to_numeric(out["high_efforts"])

    out = normalize_combined_fields(out, mapping)

    if "distance_per_min" not in out.columns or out["distance_per_min"].isna().all():
        if "total_distance" in out.columns:
            out["distance_per_min"] = out["total_distance"] / out["duration_min"]

    out = out.dropna(subset=["start_time"])
    out = out[out["player_name"].str.len() > 0]
    out = out[~out["player_name"].str.lower().str.contains("benchmark|átlag|atlag|összesen|osszesen", na=False)]
    out = finalize_exposure_columns(add_position_group(out))

    return out, mapping, []

def apply_mapping_to_raw(raw: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> Tuple[pd.DataFrame, Dict[str, Optional[str]], List[str]]:
    df = raw.copy()
    df.columns = [clean_col_name(c) for c in df.columns]
    out = pd.DataFrame()
    fixed_mapping: Dict[str, Optional[str]] = {}
    for std_col in STANDARD_COLUMNS:
        source = mapping.get(std_col)
        source = clean_col_name(source) if source else None
        fixed_mapping[std_col] = source
        if source and source in df.columns:
            out[std_col] = df[source]
    missing_core = [c for c in CORE_REQUIRED if c not in out.columns]
    if missing_core:
        return out, fixed_mapping, missing_core

    out["player_name"] = out["player_name"].astype(str).str.strip()
    out["session_type"] = out["session_type"].apply(normalize_session_type)
    fallback_source = df["Split"] if "Split" in df.columns else None
    out["start_time"] = parse_datetime_series(out["start_time"], fallback_source=fallback_source)
    out["session_date"] = out["start_time"].dt.date
    out["week"] = make_iso_week_series(out["start_time"])
    if "duration" in out.columns:
        out["duration_min"] = out["duration"].apply(duration_to_minutes)
    else:
        out["duration_min"] = np.nan

    numeric_cols = [
        "total_distance", "distance_per_min", "max_speed", "avg_speed", "sprints", "match_minutes",
        "speed_zone_3", "speed_zone_4", "speed_zone_5", "training_load", "cardio_load",
        "recovery_hours", "muscle_load", "hr_avg", "hr_max", "hrv", "high_efforts", "acc_low", "acc_mid",
        "acc_high", "dec_low", "dec_mid", "dec_high",
    ]
    for col in numeric_cols:
        if col in out.columns:
            out[col] = to_numeric(out[col])
    for col in ["speed_zone_3", "speed_zone_4", "speed_zone_5", "acc_low", "acc_mid", "acc_high", "dec_low", "dec_mid", "dec_high"]:
        if col not in out.columns:
            out[col] = 0

    out["hsr_distance"] = out[["speed_zone_4", "speed_zone_5"]].sum(axis=1, min_count=1)
    out["sprint_distance"] = out["speed_zone_5"]
    out["acc_count"] = out[["acc_low", "acc_mid", "acc_high"]].sum(axis=1, min_count=1)
    out["dec_count"] = out[["dec_low", "dec_mid", "dec_high"]].sum(axis=1, min_count=1)
    if "high_efforts" not in out.columns or out["high_efforts"].isna().all():
        out["high_efforts"] = out[["acc_mid", "acc_high", "dec_mid", "dec_high"]].sum(axis=1, min_count=1)
    else:
        out["high_efforts"] = to_numeric(out["high_efforts"])
    out = normalize_combined_fields(out, mapping)

    if "distance_per_min" not in out.columns or out["distance_per_min"].isna().all():
        if "total_distance" in out.columns:
            out["distance_per_min"] = out["total_distance"] / out["duration_min"]
    out = out.dropna(subset=["start_time"])
    out = out[out["player_name"].str.len() > 0]
    out = out[~out["player_name"].str.lower().str.contains("benchmark|átlag|atlag|összesen|osszesen", na=False)]
    out = finalize_exposure_columns(add_position_group(out))
    return out, fixed_mapping, []




def render_emergency_mapper(raw_df: pd.DataFrame, current_mapping: Dict[str, Optional[str]], missing_core: List[str]) -> None:
    """Mapper blokk akkor is, ha az app még nem tud elemezni.
    Cél: ne fusson hibára / st.stop előtt legyen javítási lehetőség.
    """
    st.markdown("### 🧭 Smart Excel Mapper – kötelező mezők javítása")
    st.info("A fájl szerkezete eltér a várt sablontól. Állítsd be a kötelező mezőket, majd kattints az alkalmazásra.")
    render_mapping_score(current_mapping)
    st.markdown("#### App mezők magyarázata")
    st.dataframe(enhanced_mapping_quality_df(raw_df, current_mapping), use_container_width=True)

    if raw_df is None or raw_df.empty:
        st.error("Nincs beolvasható nyers adat.")
        return

    cols = [""] + [str(c) for c in raw_df.columns]
    manual = dict(current_mapping or {})

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        default = manual.get("player_name") or ("Name" if "Name" in raw_df.columns else ("Játékos neve" if "Játékos neve" in raw_df.columns else ""))
        manual["player_name"] = st.selectbox(
            "Játékos neve / Name – szöveg",
            cols,
            index=cols.index(default) if default in cols else 0,
            key="emergency_map_player_name",
        ) or None

    with col_b:
        default = manual.get("session_type") or ("Típus" if "Típus" in raw_df.columns else "")
        manual["session_type"] = st.selectbox(
            "Típus – Edzés vagy Meccs",
            cols,
            index=cols.index(default) if default in cols else 0,
            key="emergency_map_session_type",
        ) or None

    with col_c:
        default = manual.get("start_time") or ("Kezdési idő" if "Kezdési idő" in raw_df.columns else ("Split" if "Split" in raw_df.columns else ""))
        manual["start_time"] = st.selectbox(
            "Kezdési idő / dátum – dátum/idő",
            cols,
            index=cols.index(default) if default in cols else 0,
            key="emergency_map_start_time",
        ) or None

    with st.expander("Haladó oszlopok mappingje", expanded=False):
        optional_fields = [
            "duration", "match_minutes", "total_distance", "distance_per_min", "max_speed", "sprints",
            "speed_zone_4", "speed_zone_5", "training_load", "muscle_load",
            "hr_avg", "hr_max", "acc_high", "dec_high", "high_efforts"
        ]
        for std_col in optional_fields:
            default = manual.get(std_col) or ""
            manual[std_col] = st.selectbox(
                f"{mapper_label(std_col)} | {mapper_unit(std_col)}",
                cols,
                index=cols.index(default) if default in cols else 0,
                key=f"emergency_map_{std_col}",
                help=mapper_desc(std_col),
            ) or None
            warn = mapper_warning(std_col, manual.get(std_col))
            if warn:
                st.warning(warn)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Mapping alkalmazása", use_container_width=True, key="apply_emergency_mapping"):
            mapped_df, fixed_mapping, missing = apply_mapping_to_raw(raw_df, manual)
            if missing:
                st.error(f"Még hiányzik: {', '.join(missing)}")
            else:
                st.session_state["mapped_df_override"] = mapped_df
                st.session_state["manual_mapping"] = fixed_mapping
                st.success("Mapping alkalmazva. Újratöltöm az elemzést.")
                st.rerun()

    with c2:
        if st.button("♻️ Mapping törlése", use_container_width=True, key="clear_emergency_mapping"):
            st.session_state.pop("mapped_df_override", None)
            st.session_state.pop("manual_mapping", None)
            st.rerun()

    st.caption("Tipp: Distance(4+5) = összevont nagysebességű táv, ezt a Zone 4 / HSR mezőhöz érdemes tenni. Sprints count = darab, Total sprints distance = méter.")
    st.markdown("#### Beolvasott oszlopok")
    st.write(list(raw_df.columns))
    st.markdown("#### Adat előnézet")
    st.dataframe(raw_df.head(8), use_container_width=True)



# -----------------------------------------------------------------------------
# V6.0 - Kapus + játékperc + exposure normalizálás
# -----------------------------------------------------------------------------
KEEPER_POSITION_TOKENS = ["gk", "goalkeeper", "kapus", "kapusposzt", "kap", "keeper"]
FIELD_METRICS_FOR_EXPOSURE = [
    "total_distance", "hsr_distance", "sprint_distance", "sprints", "acc_count", "dec_count",
    "high_efforts", "training_load", "muscle_load", "distance_per_min", "max_speed",
]
KEEPER_BENCHMARK_WEIGHTS = {
    "total_distance": 0.40,
    "distance_per_min": 0.55,
    "hsr_distance": 0.15,
    "sprint_distance": 0.10,
    "sprints": 0.15,
    "acc_count": 0.55,
    "dec_count": 0.55,
    "high_efforts": 0.60,
    "training_load": 0.70,
    "muscle_load": 0.70,
    "max_speed": 0.45,
}

def is_keeper_position_value(value: object) -> bool:
    txt = _norm_mapping_text(value)
    if not txt:
        return False
    return any(tok in txt for tok in KEEPER_POSITION_TOKENS)

def add_keeper_flag_from_position(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "position" in out.columns:
        out["is_goalkeeper"] = out["position"].apply(is_keeper_position_value).astype(bool)
    elif "position_group" in out.columns:
        out["is_goalkeeper"] = out["position_group"].astype(str).str.lower().str.contains("kapus|gk|goalkeeper", na=False)
    else:
        out["is_goalkeeper"] = False
    return out

def render_keeper_controls_and_apply(df: pd.DataFrame) -> pd.DataFrame:
    """Kapusok kezelése.
    - Ha van poszt, automatikusan felismeri a kapusokat.
    - Ha nincs poszt / nincs felismerés, oldalsávban rákérdez és a kiválasztott játékosokat kapusként kezeli.
    """
    if df is None or df.empty or "player_name" not in df.columns:
        return df
    out = add_keeper_flag_from_position(df)
    players_all = sorted(out["player_name"].dropna().astype(str).unique().tolist())
    auto_keepers = sorted(out.loc[out.get("is_goalkeeper", False), "player_name"].dropna().astype(str).unique().tolist()) if "is_goalkeeper" in out.columns else []
    has_position_col = (
        "position" in out.columns
        and out["position"].notna().any()
        and out["position"].astype(str).str.strip().replace({"": np.nan, "nan": np.nan, "None": np.nan}).notna().any()
    )
    if not has_position_col:
        st.sidebar.warning("Nincs felismerhető Poszt oszlop. Kérlek add meg, vannak-e kapusok az adatokban.")
    with st.sidebar.expander("Kapusok és játékpercek", expanded=(not has_position_col)):
        if has_position_col:
            st.caption("Poszt oszlop alapján automatikus kapusfelismerés aktív. Ezt felülírhatod, ha szükséges.")
            st.write("Felismert kapusok: " + (", ".join(auto_keepers) if auto_keepers else "nincs"))
            manual_override = st.checkbox("Kapuslista kézi felülírása", value=False, key="keeper_manual_override")
            if manual_override:
                selected = st.multiselect("Kapusok kiválasztása", players_all, default=auto_keepers, key="manual_keeper_players")
                out["is_goalkeeper"] = out["player_name"].astype(str).isin(selected)
        else:
            st.markdown("**Kapusok kézi megadása szükséges**")
            has_keepers = st.radio(
                "Szerepelnek kapusok az adatok között?",
                ["Igen", "Nem"],
                horizontal=True,
                key="has_goalkeepers_without_position",
                help="Mivel nincs Poszt oszlop, az app csak így tudja külön kezelni a kapusokat."
            )
            if has_keepers == "Igen":
                selected = st.multiselect(
                    "Kapusok kiválasztása",
                    players_all,
                    default=st.session_state.get("manual_keeper_players_no_pos", []),
                    key="manual_keeper_players_no_pos",
                    help="A kiválasztott játékosokra kapus-specifikus súlyozás kerül."
                )
                out["is_goalkeeper"] = out["player_name"].astype(str).isin(selected)
                if not selected:
                    st.warning("Válaszd ki a kapus(oka)t, különben minden játékos mezőnyjátékosként kerül értékelésre.")
            else:
                out["is_goalkeeper"] = False
        st.caption("A csapatszintű meccs-edzés összevetésben a mezőnyjátékos-profil az alap; kapusokra külön súlyozott benchmark kerül.")
    return finalize_exposure_columns(out)

def finalize_exposure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Játékpercek és terhelési exposure normalizálása.
    Fontos: egy meccsen 14 játékos szereplése nem 14x90 perc. A számítás a tényleges
    játékospercet használja, ha van; különben meccsnél a row szintű duration_min lesz az alap.
    Edzésnél a résztvevői percre és az egy főre jutó terhelésre normalizál.
    """
    if df is None or df.empty:
        return df
    out = df.copy()
    if "is_goalkeeper" not in out.columns:
        out = add_keeper_flag_from_position(out)
    if "duration_min" not in out.columns:
        out["duration_min"] = np.nan
    if "match_minutes" in out.columns:
        out["match_minutes"] = out["match_minutes"].apply(duration_to_minutes)
    else:
        out["match_minutes"] = np.nan
    # player_minutes: meccsnél tényleges játékperc, ha van; ha nincs, duration_min. Edzésnél duration_min.
    out["player_minutes"] = np.where(
        out.get("session_type", "").astype(str).eq("Meccs"),
        out["match_minutes"].where(out["match_minutes"].notna() & (out["match_minutes"] > 0), out["duration_min"]),
        out["duration_min"],
    )
    out["player_minutes"] = pd.to_numeric(out["player_minutes"], errors="coerce")
    out.loc[out["player_minutes"] <= 0, "player_minutes"] = np.nan
    group_cols = ["week", "session_date", "session_type"]
    if "session_name" in out.columns:
        group_cols.append("session_name")
    safe_group_cols = [c for c in group_cols if c in out.columns]
    if safe_group_cols:
        out["session_player_count"] = out.groupby(safe_group_cols)["player_name"].transform("nunique")
        out["field_player_count"] = out[~out["is_goalkeeper"]].groupby(safe_group_cols)["player_name"].transform("nunique")
        out["team_player_minutes"] = out.groupby(safe_group_cols)["player_minutes"].transform("sum")
        field_minutes = out.loc[~out["is_goalkeeper"]].groupby(safe_group_cols)["player_minutes"].sum().rename("field_team_minutes")
        out = out.merge(field_minutes.reset_index(), on=safe_group_cols, how="left")
    else:
        out["session_player_count"] = out["player_name"].nunique() if "player_name" in out.columns else np.nan
        out["field_player_count"] = out.loc[~out["is_goalkeeper"], "player_name"].nunique() if "player_name" in out.columns else np.nan
        out["team_player_minutes"] = out["player_minutes"].sum()
        out["field_team_minutes"] = out.loc[~out["is_goalkeeper"], "player_minutes"].sum()
    out["keeper_weight"] = 1.0
    for metric, weight in KEEPER_BENCHMARK_WEIGHTS.items():
        if metric in out.columns:
            out[f"{metric}_keeper_adjusted"] = np.where(out["is_goalkeeper"], out[metric] / max(weight, 0.01), out[metric])
    for metric in FIELD_METRICS_FOR_EXPOSURE:
        if metric in out.columns:
            out[f"{metric}_per90"] = np.where(out["player_minutes"] > 0, out[metric] / out["player_minutes"] * 90, np.nan)
            out[f"{metric}_per_player"] = np.where(out["session_player_count"] > 0, out[metric] / out["session_player_count"], np.nan)
            out[f"{metric}_per_field_player"] = np.where(out["field_player_count"] > 0, out[metric] / out["field_player_count"], np.nan)
    return out

def field_players_only(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if "is_goalkeeper" in df.columns:
        return df[~df["is_goalkeeper"].fillna(False)].copy()
    return df.copy()

def aggregate_weekly(df: pd.DataFrame) -> pd.DataFrame:
    # Csapatszintű összevetésnél a mezőnyjátékos-profil az alap, hogy a kapusok ne húzzák le
    # a sprint/HSR/intenzitás mutatókat. A kapusok külön szerepként maradnak a játékosszintű elemzésben.
    work = field_players_only(finalize_exposure_columns(df)) if df is not None and not df.empty else pd.DataFrame()
    if work.empty:
        return pd.DataFrame()
    agg_map = {
        "total_distance": "sum",
        "training_load": "sum",
        "muscle_load": "sum",
        "hsr_distance": "sum",
        "sprint_distance": "sum",
        "sprints": "sum",
        "acc_count": "sum",
        "dec_count": "sum",
        "high_efforts": "sum",
        "duration_min": "sum",
        "player_minutes": "sum",
        "team_player_minutes": "max",
        "field_team_minutes": "max",
        "session_player_count": "max",
        "field_player_count": "max",
        "distance_per_min": "mean",
        "max_speed": "max",
        "hr_avg": "mean",
        "hrv": "mean",
    }
    usable = {k: v for k, v in agg_map.items() if k in work.columns}
    res = work.groupby(["week", "session_type"], as_index=False).agg(usable)
    # Per90 / per participant normalizált csapatmutatók: különösen meccs-edzés arányhoz.
    for metric in ["total_distance", "hsr_distance", "sprint_distance", "sprints", "high_efforts", "training_load"]:
        if metric in res.columns and "field_team_minutes" in res.columns:
            res[f"{metric}_per90_team"] = np.where(res["field_team_minutes"] > 0, res[metric] / res["field_team_minutes"] * 90, np.nan)
        if metric in res.columns and "field_player_count" in res.columns:
            res[f"{metric}_per_field_player"] = np.where(res["field_player_count"] > 0, res[metric] / res["field_player_count"], np.nan)
    return res


def player_weekly(df: pd.DataFrame) -> pd.DataFrame:
    work = finalize_exposure_columns(df) if df is not None and not df.empty else pd.DataFrame()
    if work.empty:
        return pd.DataFrame()
    agg_map = {
        "total_distance": "sum",
        "training_load": "sum",
        "muscle_load": "sum",
        "hsr_distance": "sum",
        "sprint_distance": "sum",
        "sprints": "sum",
        "acc_count": "sum",
        "dec_count": "sum",
        "high_efforts": "sum",
        "duration_min": "sum",
        "player_minutes": "sum",
        "distance_per_min": "mean",
        "max_speed": "max",
        "hr_avg": "mean",
        "hrv": "mean",
        "is_goalkeeper": "max",
    }
    usable = {k: v for k, v in agg_map.items() if k in work.columns}
    res = work.groupby(["player_name", "week", "session_type"], as_index=False).agg(usable)
    for metric in ["total_distance", "hsr_distance", "sprint_distance", "sprints", "high_efforts", "training_load", "acc_count", "dec_count"]:
        if metric in res.columns and "player_minutes" in res.columns:
            res[f"{metric}_per90"] = np.where(res["player_minutes"] > 0, res[metric] / res["player_minutes"] * 90, np.nan)
    return res


def pct_change(current: float, previous: float) -> Optional[float]:
    if previous is None or pd.isna(previous) or previous == 0 or pd.isna(current):
        return None
    return (current - previous) / previous


def available_metric_options(df: pd.DataFrame, desired: List[str]) -> List[str]:
    return [m for m in desired if m in df.columns and not df[m].isna().all()]


def metric_name(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric)


def format_week_label(week_value: object) -> str:
    """Rövid, dashboard-barát hétfelirat.
    A pandas periodből érkező '2026-06-01/2026-06-07' helyett pl. '2026-W23'.
    """
    text = str(week_value or "")
    try:
        if "/" in text:
            start = pd.to_datetime(text.split("/")[0], errors="coerce")
            if pd.notna(start):
                iso = start.isocalendar()
                return f"{int(iso.year)}-W{int(iso.week):02d}"
        dt = pd.to_datetime(text, errors="coerce")
        if pd.notna(dt):
            iso = dt.isocalendar()
            return f"{int(iso.year)}-W{int(iso.week):02d}"
    except Exception:
        pass
    return text


def team_insights(df: pd.DataFrame, selected_week: str) -> List[Insight]:
    insights: List[Insight] = []
    weeks = sorted(df["week"].dropna().unique().tolist())
    week_idx = weeks.index(selected_week) if selected_week in weeks else len(weeks) - 1
    previous_week = weeks[week_idx - 1] if week_idx > 0 else None

    current = df[df["week"] == selected_week]
    prev = df[df["week"] == previous_week] if previous_week else pd.DataFrame()
    cur_train = current[current["session_type"] == "Edzés"]
    cur_match = current[current["session_type"] == "Meccs"]
    prev_train = prev[prev["session_type"] == "Edzés"] if not prev.empty else pd.DataFrame()

    # 1. Sprint underload
    if not cur_train.empty and not cur_match.empty and "sprint_distance" in df.columns:
        train_sprint = cur_train["sprint_distance"].mean()
        match_sprint = cur_match["sprint_distance"].mean()
        if pd.notna(match_sprint) and match_sprint > 0:
            ratio = train_sprint / match_sprint
            if ratio < 0.65:
                insights.append(Insight(
                    "Alacsony sprintterhelés", "KRITIKUS",
                    f"Az edzések átlagos sprintterhelése a meccsterhelés kb. {ratio:.0%}-a.",
                    "A nagy intenzitású terhelés jelentősen elmaradhat attól, amit a mérkőzés megkövetel.",
                    "Érdemes célzott sprint- vagy nagysebességű blokkokat beépíteni, ha ez illeszkedik a hét terhelési tervéhez.",
                ))
            elif ratio < 0.80:
                insights.append(Insight(
                    "Alacsony sprintterhelés", "FIGYELMEZTETÉS",
                    f"Az edzések átlagos sprintterhelése a meccsterhelés kb. {ratio:.0%}-a.",
                    "A meccsigényhez képest mérsékelt intenzitási hiány látható.",
                    "Érdemes ellenőrizni, hogy tudatos visszaterhelésről vagy nem kívánt intenzitáshiányról van-e szó.",
                ))

    # 2. Weekly load change
    if not cur_train.empty and not prev_train.empty and "training_load" in df.columns:
        cur_load = cur_train["training_load"].sum()
        prev_load = prev_train["training_load"].sum()
        chg = pct_change(cur_load, prev_load)
        if chg is not None:
            if chg > 0.25:
                insights.append(Insight(
                    "Heti terhelési kiugrás", "FIGYELMEZTETÉS",
                    f"Az edzés terhelési pontértéke {chg:.0%}-kal nőtt az előző héthez képest.",
                    "A hirtelen terhelésemelkedés ronthatja a frissességet és növelheti a következő napok terhelési kockázatát.",
                    "Érdemes figyelni a következő edzések intenzitását, illetve a játékosok egyéni reakcióit.",
                ))
            elif chg < -0.25:
                insights.append(Insight(
                    "Heti terheléscsökkenés", "INFORMÁCIÓ",
                    f"Az edzés terhelési pontértéke {abs(chg):.0%}-kal csökkent az előző héthez képest.",
                    "Ez lehet tudatos frissítés, de lehet nem kívánt terhelésvesztés is.",
                    "Érdemes kontextusba helyezni: meccs előtti könnyítés, hiányzók vagy edzéstartalom-váltás okozta-e.",
                ))

    # 3. Match intensity gap
    if not cur_train.empty and not cur_match.empty and "distance_per_min" in df.columns:
        train_int = cur_train["distance_per_min"].mean()
        match_int = cur_match["distance_per_min"].mean()
        if pd.notna(match_int) and match_int > 0:
            ratio = train_int / match_int
            if ratio < 0.85:
                insights.append(Insight(
                    "Meccsintenzitási eltérés", "FIGYELMEZTETÉS",
                    f"Az edzések átlagos táv/perc értéke a meccs kb. {ratio:.0%}-a.",
                    "A csapat edzésintenzitása elmaradhat a mérkőzés tempójától.",
                    "Érdemes lehet rövidebb, intenzívebb játékszituációkat vagy tudatos tempóváltásokat használni.",
                ))

    # 4. High deceleration load
    if not cur_train.empty and not prev_train.empty and "dec_count" in df.columns:
        cur_dec = cur_train["dec_count"].mean()
        prev_dec = prev_train["dec_count"].mean()
        chg = pct_change(cur_dec, prev_dec)
        if chg is not None and chg > 0.35:
            insights.append(Insight(
                "Magas lassítási terhelés", "FIGYELMEZTETÉS",
                f"Az átlagos lassításszám {chg:.0%}-kal nőtt az előző héthez képest.",
                "A lassítások jelentős neuromuszkuláris terhelést jelenthetnek.",
                "Érdemes figyelni a regenerációra és a következő edzés excentrikus terhelésére.",
            ))

    # 5. Max speed suppression
    if not cur_train.empty and not prev_train.empty and "max_speed" in df.columns:
        cur_speed = cur_train["max_speed"].max()
        prev_speed = prev_train["max_speed"].max()
        chg = pct_change(cur_speed, prev_speed)
        if chg is not None and chg < -0.05:
            insights.append(Insight(
                "Maximális sebesség visszaesése", "INFORMÁCIÓ",
                f"A heti legmagasabb maximális sebesség {abs(chg):.0%}-kal alacsonyabb az előző hétnél.",
                "Ez jelezhet alacsonyabb neuromuszkuláris frissességet, de lehet edzéstartalom-függő is.",
                "Érdemes megnézni, volt-e valódi maximális sebességű inger a héten.",
            ))

    # 6. Player outlier alerts
    if not cur_train.empty and "training_load" in cur_train.columns:
        player_load = cur_train.groupby("player_name")["training_load"].sum().dropna()
        if len(player_load) >= 5 and player_load.mean() > 0:
            mean = player_load.mean()
            high = player_load[player_load > mean * 1.25].sort_values(ascending=False)
            low = player_load[player_load < mean * 0.75].sort_values(ascending=True)
            if len(high) > 0:
                names = ", ".join(high.head(3).index.tolist())
                insights.append(Insight(
                    "Kiugró játékosterhelés", "FIGYELMEZTETÉS",
                    f"Néhány játékos jelentősen a csapatátlag felett terhelődött: {names}.",
                    "Egyéni terheléskülönbség alakult ki a héten.",
                    "Érdemes egyéni szinten ránézni a következő edzés terhelésére és a játékpercekre.",
                    scope="Játékos",
                ))
            if len(low) > 0:
                names = ", ".join(low.head(3).index.tolist())
                insights.append(Insight(
                    "Alacsony játékosterhelés", "INFORMÁCIÓ",
                    f"Néhány játékos jelentősen a csapatátlag alatt terhelődött: {names}.",
                    "Terheléslemaradás alakulhat ki, főleg ha ez több héten át fennáll.",
                    "Érdemes ellenőrizni a hiányzásokat, játékperceket és az egyéni kiegészítő munkát.",
                    scope="Játékos",
                ))

    if not insights:
        insights.append(Insight(
            "Stabil hét", "INFORMÁCIÓ",
            "Nem látható kiemelt negatív eltérés az aktuális hét fő mutatóiban.",
            "A csapat terhelési profilja stabilnak tűnik az elérhető adatok alapján.",
            "Érdemes tovább figyelni a sprint- és intenzitási trendeket, különösen meccs előtti héten.",
        ))

    return sorted(insights, key=lambda x: SEVERITY_RANK.get(x.severity, 9))[:8]



# -----------------------------------------------------------------------------
# V2 - Football Intelligence Layer
# -----------------------------------------------------------------------------
def pdf_safe_text(text: object) -> str:
    """PDF exporthoz stabil magyar szöveg.
    Cloud környezetben a hosszú ő/ű néha hibásan jelenik meg, ezért PDF-ben
    rövid párra normalizáljuk. UI, Word és Excel exportban marad az eredeti.
    """
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    text = str(text)
    replacements = {"ő": "ö", "Ő": "Ö", "ű": "ü", "Ű": "Ü"}
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def day_label_from_delta(delta_days: int) -> str:
    if delta_days == 0:
        return "MD"
    if delta_days < 0:
        return f"MD{delta_days}"
    return f"MD+{delta_days}"


def detect_match_day(week_df: pd.DataFrame) -> Optional[pd.Timestamp]:
    if week_df.empty:
        return None
    tmp = week_df.copy()
    tmp["session_date_dt"] = pd.to_datetime(tmp["session_date"], errors="coerce")
    matches = tmp[tmp["session_type"] == "Meccs"]
    if not matches.empty:
        # Ha több meccs van, a hét fő meccsének az utolsót vesszük.
        return pd.to_datetime(matches["session_date_dt"].max())
    return None


def build_microcycle_table(df: pd.DataFrame, selected_week: str) -> pd.DataFrame:
    week_df = df[df["week"] == selected_week].copy()
    if week_df.empty:
        return pd.DataFrame()
    match_day = detect_match_day(week_df)
    week_df["session_date_dt"] = pd.to_datetime(week_df["session_date"], errors="coerce")

    agg_spec = {
        "training_load": "sum",
        "total_distance": "sum",
        "sprint_distance": "sum",
        "hsr_distance": "sum",
        "distance_per_min": "mean",
        "max_speed": "max",
        "acc_count": "sum",
        "dec_count": "sum",
        "high_efforts": "sum",
        "player_name": "nunique",
    }
    usable = {k: v for k, v in agg_spec.items() if k in week_df.columns}
    daily = week_df.groupby(["session_date_dt", "session_type"], as_index=False).agg(usable)
    daily = daily.rename(columns={"player_name": "játékosok"})
    if match_day is not None:
        daily["md_delta"] = (daily["session_date_dt"] - match_day).dt.days
        daily["md_label"] = daily["md_delta"].apply(day_label_from_delta)
    else:
        daily["md_delta"] = np.nan
        daily["md_label"] = "Nincs meccs"

    # Napi load fallback: ahol nincs training_load, ott total_distance alapján értékelünk.
    if "training_load" in daily.columns and not daily["training_load"].isna().all():
        daily["load_index"] = daily["training_load"]
        daily["load_index_label"] = "Terhelési pont"
    elif "total_distance" in daily.columns:
        daily["load_index"] = daily["total_distance"]
        daily["load_index_label"] = "Össztáv"
    else:
        daily["load_index"] = np.nan
        daily["load_index_label"] = "Nincs load mutató"
    return daily.sort_values("session_date_dt")


def microcycle_insights(df: pd.DataFrame, selected_week: str) -> List[Insight]:
    insights: List[Insight] = []
    daily = build_microcycle_table(df, selected_week)
    if daily.empty:
        return insights
    if "MD" not in daily["md_label"].values:
        insights.append(Insight(
            "Mikrociklus kontextus hiányzik", "INFORMÁCIÓ",
            "Az aktuális héten nem található meccs típusú session, ezért az MD-napok nem értelmezhetők automatikusan.",
            "Meccsnap nélkül a heti struktúrát csak általános terhelési trendként lehet értékelni.",
            "Ha van mérkőzés, érdemes a session típusát 'Meccs'-ként jelölni, hogy a rendszer MD-1 / MD-2 / MD-3 logikával is tudjon gondolkodni.",
            scope="Mikrociklus",
        ))
        return insights

    train = daily[daily["session_type"] == "Edzés"].copy()
    match = daily[daily["session_type"] == "Meccs"].copy()

    # Maximális sebességű inger: történt-e értelmezhető sprintinger a meccs előtti napokban?
    if not train.empty and "sprint_distance" in daily.columns and not match.empty:
        match_sprint = match["sprint_distance"].mean()
        max_training_sprint = train["sprint_distance"].max()
        if pd.notna(match_sprint) and match_sprint > 0:
            ratio = max_training_sprint / match_sprint if pd.notna(max_training_sprint) else 0
            if ratio < 0.15:
                insights.append(Insight(
                    "Hiányzó maximális sebességű inger", "KRITIKUS",
                    f"A héten nem látszik érdemi sprintinger: a legmagasabb edzésnapi sprintterhelés a meccs kb. {ratio:.0%}-a.",
                    "Meccsigényhez képest alacsony lehetett a maximális sebességű inger, ami a felkészítés minőségét ronthatja.",
                    "Érdemes lehet egy rövid, kontrollált maximális sebességű inger blokkot betervezni a megfelelő napon, ha a heti cél és a játékosállapot engedi.",
                    scope="Mikrociklus",
                ))
            elif ratio < 0.30:
                insights.append(Insight(
                    "Alacsony maximális sebességű inger", "FIGYELMEZTETÉS",
                    f"A legmagasabb edzésnapi sprintterhelés a meccs kb. {ratio:.0%}-a.",
                    "Volt sprintinger, de a meccsigényhez képest visszafogott lehetett.",
                    "Érdemes ellenőrizni, hogy ez tudatos frissítés vagy nem kívánt intenzitáshiány volt-e.",
                    scope="Mikrociklus",
                ))

    # MD-2 túl magas load
    md2 = daily[daily["md_label"] == "MD-2"]
    md3_4 = daily[daily["md_label"].isin(["MD-3", "MD-4"])]
    if not md2.empty and not md3_4.empty:
        md2_load = md2["load_index"].sum()
        peak_early = md3_4["load_index"].max()
        if pd.notna(md2_load) and pd.notna(peak_early) and peak_early > 0 and md2_load > peak_early * 0.80:
            insights.append(Insight(
                "Magas MD-2 terhelés", "FIGYELMEZTETÉS",
                "Az MD-2 nap terhelése közel volt a hét korábbi fő terhelési napjához.",
                "A mérkőzés előtti 48 órában a túl magas load ronthatja a frissességet.",
                "Érdemes lehet az MD-2 napot jobban kontrollálni, és a fő terhelési ingert inkább MD-3 / MD-4 környékére helyezni.",
                scope="Mikrociklus",
            ))

    # MD-1 activation kontroll
    md1 = daily[daily["md_label"] == "MD-1"]
    if not md1.empty and not md2.empty:
        md1_load = md1["load_index"].sum()
        md2_load = md2["load_index"].sum()
        if pd.notna(md1_load) and pd.notna(md2_load) and md2_load > 0 and md1_load > md2_load * 0.85:
            insights.append(Insight(
                "MD-1 activation túl erős lehet", "FIGYELMEZTETÉS",
                "Az MD-1 load nem csökkent érdemben az MD-2 naphoz képest.",
                "A meccs előtti aktiváció célja általában a frissítés, nem egy újabb nagy terhelési inger.",
                "Érdemes lehet az MD-1 napot rövidebb, frissebb, idegrendszeri aktivációs jelleggel tartani.",
                scope="Mikrociklus",
            ))

    # Pozitív taper insight, ha van adat és nincs túl magas MD-1/MD-2
    if not md1.empty and not md3_4.empty:
        md1_load = md1["load_index"].sum()
        peak_early = md3_4["load_index"].max()
        if pd.notna(md1_load) and pd.notna(peak_early) and peak_early > 0 and md1_load < peak_early * 0.45:
            insights.append(Insight(
                "Megfelelő tapering jel", "INFORMÁCIÓ",
                "A meccs előtti nap terhelése jelentősen alacsonyabb volt a hét fő terhelési napjához képest.",
                "Ez támogathatja a mérkőzésnapi frissességet.",
                "Érdemes megtartani ezt a struktúrát, ha a mérkőzésnapi teljesítmény is visszaigazolja.",
                scope="Mikrociklus",
            ))

    return insights


def playstyle_insights(df: pd.DataFrame, selected_week: str, playstyle: str) -> List[Insight]:
    insights: List[Insight] = []
    if playstyle == "Kiegyensúlyozott":
        return insights
    current = df[df["week"] == selected_week]
    train = current[current["session_type"] == "Edzés"]
    match = current[current["session_type"] == "Meccs"]
    if train.empty:
        return insights

    def mean_ratio(metric: str) -> Optional[float]:
        if metric not in current.columns or match.empty:
            return None
        m = match[metric].mean()
        t = train[metric].mean()
        if pd.isna(m) or m == 0 or pd.isna(t):
            return None
        return t / m

    intensity_ratio = mean_ratio("distance_per_min")
    sprint_ratio = mean_ratio("sprint_distance")
    effort_ratio = mean_ratio("high_efforts")

    if playstyle == "Pressing":
        if intensity_ratio is not None and intensity_ratio < 0.90:
            insights.append(Insight(
                "Pressing profil: intenzitáshiány", "FIGYELMEZTETÉS",
                f"A heti edzésintenzitás a meccsintenzitás kb. {intensity_ratio:.0%}-a.",
                "Pressing játékmodellnél fontos, hogy a csapat rendszeresen találkozzon magas munkasűrűségű helyzetekkel.",
                "Érdemes lehet rövidebb, nagyobb nyomású játékokat vagy pressing-specifikus blokkokat használni.",
                scope="Játékmodell",
            ))
        if effort_ratio is not None and effort_ratio < 0.75:
            insights.append(Insight(
                "Pressing profil: kevés nagy intenzitású erőfeszítés", "FIGYELMEZTETÉS",
                f"A high effort profil a meccsigény kb. {effort_ratio:.0%}-a.",
                "A sok gyorsulás, lassítás és ismételt intenzív akció kulcs a pressing identitáshoz.",
                "Érdemes lehet növelni az ismételt intenzív akciókat tartalmazó gyakorlatok arányát.",
                scope="Játékmodell",
            ))

    elif playstyle == "Transition":
        if sprint_ratio is not None and sprint_ratio < 0.80:
            insights.append(Insight(
                "Transition profil: alacsony sprintinger", "FIGYELMEZTETÉS",
                f"A heti sprintprofil a meccsigény kb. {sprint_ratio:.0%}-a.",
                "Átmenetekre építő játékmodellben fontos a rendszeres nagysebességű inger.",
                "Érdemes célzott átmeneti játékokat vagy nagy területű sprinthelyzeteket beépíteni.",
                scope="Játékmodell",
            ))

    elif playstyle == "Possession":
        if intensity_ratio is not None and intensity_ratio > 1.15:
            insights.append(Insight(
                "Possession profil: magas edzésintenzitás", "INFORMÁCIÓ",
                f"Az edzésintenzitás meghaladta a meccsintenzitást: kb. {intensity_ratio:.0%}.",
                "Ez lehet tudatos túlterhelés, de possession modellnél a kontrollált terhelés is fontos.",
                "Érdemes ellenőrizni, hogy az intenzitás a játékelvek tanulását vagy inkább csak a fizikai terhelést szolgálta-e.",
                scope="Játékmodell",
            ))

    elif playstyle == "Low Block":
        if sprint_ratio is not None and sprint_ratio < 0.60:
            insights.append(Insight(
                "Low block profil: kevés átmeneti sprintinger", "FIGYELMEZTETÉS",
                f"A sprintprofil a meccsigény kb. {sprint_ratio:.0%}-a.",
                "Mélyebb védekezésnél is fontosak lehetnek a rövid, robbanékony átmenetek.",
                "Érdemes lehet kontrollált kontra- és visszarendeződési szituációkat alkalmazni.",
                scope="Játékmodell",
            ))
    return insights



def html_linebreaks(text: object) -> str:
    """Streamlit markdown/HTML megjelenítéshez: a literal \\n karaktereket valódi sortöréssé alakítja."""
    safe = str(text or "").replace("\\n", "\n").replace("\\r", "")
    return html.escape(safe).replace("\n", "<br>")


def week_label_short(week_value: object) -> str:
    """Hosszú pandas week labelből rövid, dashboard-barát hét címke."""
    txt = str(week_value or "")
    if "/" in txt:
        try:
            start = pd.to_datetime(txt.split("/")[0])
            return f"{start.strftime('%Y')}-W{int(start.isocalendar().week):02d}"
        except Exception:
            return txt.split("/")[0]
    return txt


def render_fpi_hero() -> None:
    st.markdown(
        """
        <div class="fpi-hero-wow">
          <h1>⚽ Football Performance Intelligence</h1>
          <p>GPS-terhelésből vezetői döntéstámogatás, edzői prioritások és exportálható performance riportok.</p>
          <div class="fpi-chip-row">
            <span class="fpi-chip-wow">⚡ Readiness</span>
            <span class="fpi-chip-wow">🎯 Coaching priorities</span>
            <span class="fpi-chip-wow">🧠 Smart mapper</span>
            <span class="fpi-chip-wow">📄 Executive export</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def clean_literal_newlines_for_display(text: object) -> str:
    raw = str(text or "")
    raw = raw.replace("\\r", "")
    raw = raw.replace("\\n", "\n")
    return raw


def render_leader_summary_direct(text: object) -> None:
    """Fixen olvasható vezetői összefoglaló fehér kártyán, sötét betűkkel."""
    raw = clean_literal_newlines_for_display(text)
    lines = [ln.strip().lstrip("-• ").strip() for ln in raw.splitlines() if ln.strip()]

    # Biztonsági javítás: ha a Játékmodell sorban maradtak benne literal \n részek.
    normalized = []
    for ln in lines:
        if "\\n" in ln:
            normalized.extend([p.strip().lstrip("-• ").strip() for p in ln.replace("\\n", "\n").splitlines() if p.strip()])
        else:
            normalized.append(ln)
    lines = normalized

    html_rows = []
    for ln in lines:
        esc = html.escape(ln)
        if esc.startswith("Hét:"):
            label, value = "📅 Hét", esc.replace("Hét:", "").strip()
        elif esc.startswith("Legfontosabb üzenet:"):
            label, value = "⚡ Legfontosabb üzenet", esc.replace("Legfontosabb üzenet:", "").strip()
        elif esc.startswith("Mit látunk?"):
            label, value = "🔎 Mit látunk?", esc.replace("Mit látunk?", "").strip()
        elif esc.startswith("Javaslat:"):
            label, value = "🎯 Javaslat", esc.replace("Javaslat:", "").strip()
        elif esc.startswith("Második fontos téma:"):
            label, value = "➕ Második fontos téma", esc.replace("Második fontos téma:", "").strip()
        elif esc.startswith("Játékmodell:"):
            label, value = "♟️ Játékmodell", esc.replace("Játékmodell:", "").strip()
        elif esc.startswith("Meccskészültség:"):
            label, value = "🚀 Meccskészültség", esc.replace("Meccskészültség:", "").strip()
        elif esc.startswith("Periodizációs besorolás:"):
            label, value = "📈 Periodizáció", esc.replace("Periodizációs besorolás:", "").strip()
        else:
            label, value = "", esc

        if label:
            html_rows.append(
                f"""
                <div style="display:grid;grid-template-columns:230px 1fr;gap:14px;padding:10px 0;border-bottom:1px solid #e2e8f0;">
                    <div style="color:#1e3a8a!important;font-weight:950!important;">{label}</div>
                    <div style="color:#0f172a!important;font-weight:800!important;line-height:1.45;">{value}</div>
                </div>
                """
            )
        else:
            html_rows.append(
                f"""
                <div style="padding:8px 0;color:#0f172a!important;font-weight:800!important;line-height:1.45;">{value}</div>
                """
            )

    st.markdown(
        f"""
        <div style="
            background:#ffffff!important;
            color:#0f172a!important;
            border:1px solid #bfdbfe;
            border-radius:22px;
            padding:20px 22px;
            margin:12px 0 22px 0;
            box-shadow:0 18px 44px rgba(15,23,42,.22);
        ">
            <div style="font-size:1.25rem;font-weight:950;color:#0f172a!important;margin-bottom:10px;">
                Heti vezetői összefoglaló
            </div>
            {''.join(html_rows)}
        </div>
        """,
        unsafe_allow_html=True,
    )






def create_sample_input_template_bytes() -> Optional[bytes]:
    """Minta Excel sablon: Adatok + Használati útmutató.
    Csak openpyxl-t használ, hogy Streamlit Cloudon ne kelljen xlsxwriter.
    """
    try:
        import io
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
        from openpyxl.worksheet.table import Table, TableStyleInfo
    except Exception:
        return None

    output = io.BytesIO()

    columns = [
        "Játékos neve",
        "Típus",
        "Szakasz neve",
        "Poszt",
        "Kezdési idő",
        "Befejezési idő",
        "Időtartam",
        "Teljes táv [m]",
        "Táv/perc [m/min]",
        "Maximális sebesség [km/h]",
        "Sprintek",
        "Táv a sebesség célzónában 4 [m] (19.80 - 24.99 km/h)",
        "Táv a sebesség célzónában 5 [m] (25.00- km/h)",
        "Edzési terhelési pontérték",
        "Izomterhelés",
        "Átlagos pulzus [bpm]",
        "Maximális pulzus [bpm]",
        "HRV (RMSSD)",
        "Gyorsulások száma (2.50 - 2.99 m/s²)",
        "Gyorsulások száma (3.00 - 50.00 m/s²)",
        "Gyorsulások száma (-2.99 - -2.50 m/s²)",
        "Gyorsulások száma (-50.00 - -3.00 m/s²)",
    ]

    sample_rows = [
        [
            "Minta Játékos 1", "Edzés", "MD-4 edzés", "CM",
            "2026-06-01 10:00", "2026-06-01 11:20", "01:20:00",
            7200, 90, 29.4, 12, 620, 180, 410, 58, 148, 188, 62, 22, 8, 20, 7
        ],
        [
            "Minta Játékos 1", "Meccs", "Bajnoki mérkőzés", "CM",
            "2026-06-07 17:00", "2026-06-07 18:45", "01:45:00",
            10600, 101, 31.2, 24, 1050, 690, 620, 84, 162, 194, 55, 34, 14, 31, 12
        ],
        [
            "Minta Játékos 2", "Edzés", "MD-4 edzés", "W",
            "2026-06-01 10:00", "2026-06-01 11:20", "01:20:00",
            7600, 95, 30.7, 15, 760, 260, 445, 63, 151, 190, 59, 25, 10, 22, 9
        ],
        [
            "Minta Játékos 2", "Meccs", "Bajnoki mérkőzés", "W",
            "2026-06-07 17:00", "2026-06-07 18:45", "01:45:00",
            11100, 106, 32.0, 29, 1200, 760, 650, 88, 165, 197, 53, 38, 16, 33, 13
        ],
    ]

    guide_rows = [
        ["Téma", "Leírás"],
        ["Cél", "Ez a sablon mutatja, milyen szerkezetű Excel tölthető fel a Performance Intelligence appba."],
        ["Fontos", "Az edzés- és meccsadatokat EGYMÁS ALÁ kell halmozni ugyanazon az Adatok munkalapon."],
        ["Egy sor jelentése", "Egy játékos egy edzésen vagy mérkőzésen mért adata."],
        ["Típus oszlop", "Csak ilyen értékeket használj: Edzés vagy Meccs."],
        ["Dátum/idő", "A Kezdési idő lehet például: 2026-06-01 10:00."],
        ["Időtartam", "Javasolt formátum: 01:20:00 vagy percben megadott szám."],
        ["Kötelező mezők", "Játékos neve, Típus, Kezdési idő."],
        ["Ajánlott fő mezők", "Teljes táv, Táv/perc, Maximális sebesség, Sprintek, sebességzónák, terhelési pont, gyorsulás/lassítás."],
        ["Ha más a GPS-export fejléce", "A Smart Excel Mapper segít felismerni és kézzel összepárosítani az oszlopokat."],
        ["Tipp", "Ne készíts külön munkalapot edzésenként. Minden esemény menjen az Adatok munkalapra egymás alá."],
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = "Adatok"
    guide = wb.create_sheet("Használati útmutató")

    ws.append(columns)
    for row in sample_rows:
        ws.append(row)

    guide.append(guide_rows[0])
    for row in guide_rows[1:]:
        guide.append(row)

    # Styles
    thin = Side(style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_fill = PatternFill("solid", fgColor="1E3A8A")
    guide_fill = PatternFill("solid", fgColor="166534")
    white_font = Font(bold=True, color="FFFFFF")
    dark_font = Font(color="0F172A")
    wrap = Alignment(wrap_text=True, vertical="top")
    center = Alignment(wrap_text=True, vertical="center", horizontal="center")

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = white_font
        cell.alignment = center
        cell.border = border

    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = dark_font
            cell.alignment = wrap
            cell.border = border

    for cell in guide[1]:
        cell.fill = guide_fill
        cell.font = white_font
        cell.alignment = center
        cell.border = border

    for row in guide.iter_rows(min_row=2):
        for cell in row:
            cell.font = dark_font
            cell.alignment = wrap
            cell.border = border

    # Widths
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 10
    ws.column_dimensions["E"].width = 20
    ws.column_dimensions["F"].width = 20
    ws.column_dimensions["G"].width = 14
    for col in range(8, len(columns) + 1):
        ws.column_dimensions[chr(64 + col) if col <= 26 else "Z"].width = 18

    guide.column_dimensions["A"].width = 26
    guide.column_dimensions["B"].width = 95

    ws.freeze_panes = "A2"
    guide.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    # Table if possible
    try:
        tab = Table(displayName="PerformanceInputTable", ref=ws.dimensions)
        style = TableStyleInfo(name="TableStyleMedium2", showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=False)
        tab.tableStyleInfo = style
        ws.add_table(tab)
    except Exception:
        pass

    try:
        tab2 = Table(displayName="PerformanceGuideTable", ref=guide.dimensions)
        style2 = TableStyleInfo(name="TableStyleMedium4", showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=False)
        tab2.tableStyleInfo = style2
        guide.add_table(tab2)
    except Exception:
        pass

    wb.save(output)
    output.seek(0)
    return output.getvalue()


def render_weekly_summary_card(summary_text: object) -> None:
    """Fixen olvasható heti vezetői összefoglaló.
    Fehér háttér + fekete szöveg + valódi sortörések.
    """
    raw = str(summary_text or "")
    raw = raw.replace("\\r", "").replace("\\n", "\n")
    raw = raw.replace("\r", "")
    safe = html.escape(raw)

    st.markdown(
        f"""
        <div style="
            background:#ffffff !important;
            color:#000000 !important;
            border-left:10px solid #2563eb;
            border-radius:18px;
            padding:24px 26px;
            margin:12px 0 22px 0;
            box-shadow:0 10px 28px rgba(0,0,0,.20);
        ">
            <div style="
                color:#000000 !important;
                font-size:1.25rem;
                font-weight:950;
                margin-bottom:14px;
            ">
                Heti vezetői összefoglaló
            </div>
            <pre style="
                color:#000000 !important;
                background:#ffffff !important;
                font-family:Segoe UI, Arial, sans-serif;
                font-size:16px;
                font-weight:700;
                line-height:1.7;
                white-space:pre-wrap;
                margin:0;
            ">{safe}</pre>
        </div>
        """,
        unsafe_allow_html=True,
    )



def build_weekly_summary(insights: List[Insight], selected_week: str, playstyle: str) -> str:
    if not insights:
        return (
            f"Hét: {week_label_short(selected_week)}\n\n"
            "Legfontosabb üzenet: Stabil hét\n"
            "- Mit látunk? Nem látható kiemelt negatív eltérés az aktuális hét fő mutatóiban.\n"
            "- Javaslat: Érdemes tovább figyelni a sprint- és intenzitási trendeket.\n"
            f"- Játékmodell: {playstyle}"
        )

    critical = [i for i in insights if i.severity == "KRITIKUS"]
    warning = [i for i in insights if i.severity == "FIGYELMEZTETÉS"]
    info = [i for i in insights if i.severity == "INFORMÁCIÓ"]
    main = critical[0] if critical else (warning[0] if warning else info[0])

    second = None
    for i in insights:
        if i.title != main.title:
            second = i
            break

    lines = [
        f"Hét: {week_label_short(selected_week)}",
        "",
        f"Legfontosabb üzenet: {main.title}",
        f"- Mit látunk? {main.observation}",
        f"- Javaslat: {main.recommendation}",
    ]
    if second is not None:
        lines.append(f"- Második fontos téma: {second.title}")
    lines.append(f"- Játékmodell: {playstyle}")
    return "\n".join(lines)

def top_coaching_priorities(insights: List[Insight], limit: int = 3) -> List[Dict[str, str]]:
    ordered = sorted(insights, key=lambda x: SEVERITY_RANK.get(x.severity, 9))
    selected = []
    seen = set()
    for ins in ordered:
        if ins.title in seen:
            continue
        seen.add(ins.title)
        selected.append({
            "Cím": ins.title,
            "Súlyosság": ins.severity,
            "Teendő": ins.recommendation,
            "Miért": ins.impact,
        })
        if len(selected) >= limit:
            break
    return selected


def render_coaching_priorities(priorities: List[Dict[str, str]]) -> None:
    if not priorities:
        st.info("Nincs kiemelt edzői teendő az aktuális szűrés alapján.")
        return
    for idx, item in enumerate(priorities, start=1):
        st.markdown(
            f"""
            <div class="priority-card">
                <div style="font-size:1.05rem;font-weight:850;">{idx}. {html.escape(item.get('Cím', ''))}</div>
                <div style="margin-top:6px;"><b>Teendő:</b><br>{html.escape(item.get('Teendő', ''))}</div>
                <div style="margin-top:6px;"><b>Miért:</b><br>{html.escape(item.get('Miért', ''))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )



# -----------------------------------------------------------------------------
# V2.5 - Performance Memory + Meccskészültség + Adaptive Intelligence
# -----------------------------------------------------------------------------
MEMORY_FILE = Path("performance_memory_v25.csv")


def score_to_label(score: float) -> str:
    if pd.isna(score):
        return "Nincs elég adat"
    if score >= 80:
        return "Jó meccskészültség"
    if score >= 65:
        return "Elfogadható, figyelendő"
    if score >= 50:
        return "Közepes kockázat"
    return "Alacsony readiness"


def score_to_color(score: float) -> str:
    if pd.isna(score):
        return "#94a3b8"
    if score >= 80:
        return "#22c55e"
    if score >= 65:
        return "#84cc16"
    if score >= 50:
        return "#f59e0b"
    return "#ef4444"


def trend_label(values: List[float], tolerance: float = 0.03) -> str:
    clean = [v for v in values if pd.notna(v)]
    if len(clean) < 3:
        return "nincs elég adat"
    first, last = clean[0], clean[-1]
    if first == 0:
        return "nincs elég adat"
    change = (last - first) / abs(first)
    if change > tolerance:
        return "emelkedő"
    if change < -tolerance:
        return "csökkenő"
    return "stabil"


def classify_week_context(weekly_row: pd.Series, history: pd.DataFrame) -> str:
    if history.empty or len(history) < 3:
        return "Tanuló hét"
    load = weekly_row.get("training_load", np.nan)
    sprint = weekly_row.get("sprint_distance", np.nan)
    intensity = weekly_row.get("distance_per_min", np.nan)

    hist_load = history["training_load"].dropna() if "training_load" in history.columns else pd.Series(dtype=float)
    hist_sprint = history["sprint_distance"].dropna() if "sprint_distance" in history.columns else pd.Series(dtype=float)

    if len(hist_load) >= 3 and pd.notna(load):
        load_mean = hist_load.mean()
        if load_mean > 0:
            load_ratio = load / load_mean
            if load_ratio > 1.18:
                return "Terhelésépítő / overload hét"
            if load_ratio < 0.82:
                return "Recovery / alulterhelt hét"

    if len(hist_sprint) >= 3 and pd.notna(sprint):
        sprint_mean = hist_sprint.mean()
        if sprint_mean > 0 and sprint / sprint_mean < 0.75:
            return "Intenzitáshiányos hét"

    if pd.notna(intensity) and "distance_per_min" in history.columns:
        int_hist = history["distance_per_min"].dropna()
        if len(int_hist) >= 3 and int_hist.mean() > 0 and intensity / int_hist.mean() > 1.12:
            return "Intenzitásfókuszú hét"

    return "Normál hét"


def build_weekly_fingerprints(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "week" not in df.columns:
        return pd.DataFrame()

    agg_spec = {
        "training_load": "sum",
        "total_distance": "sum",
        "sprint_distance": "sum",
        "hsr_distance": "sum",
        "distance_per_min": "mean",
        "max_speed": "max",
        "acc_count": "sum",
        "dec_count": "sum",
        "high_efforts": "sum",
        "duration_min": "sum",
        "hrv": "mean",
        "player_name": "nunique",
    }
    usable = {k: v for k, v in agg_spec.items() if k in df.columns}
    weekly = df.groupby("week", as_index=False).agg(usable)
    weekly = weekly.rename(columns={"player_name": "players"})

    # Csak edzésekből külön load profil, ha van elég adat.
    train = df[df["session_type"] == "Edzés"].copy()
    if not train.empty:
        train_agg = train.groupby("week", as_index=False).agg({
            k: v for k, v in usable.items() if k != "player_name"
        })
        train_agg = train_agg.add_prefix("train_")
        train_agg = train_agg.rename(columns={"train_week": "week"})
        weekly = weekly.merge(train_agg, on="week", how="left")

    # Meccsprofil külön.
    match = df[df["session_type"] == "Meccs"].copy()
    if not match.empty:
        match_agg = match.groupby("week", as_index=False).agg({
            k: v for k, v in usable.items() if k != "player_name"
        })
        match_agg = match_agg.add_prefix("match_")
        match_agg = match_agg.rename(columns={"match_week": "week"})
        weekly = weekly.merge(match_agg, on="week", how="left")

    weekly = weekly.sort_values("week").reset_index(drop=True)

    # Rolling baseline-ok.
    for metric in ["training_load", "sprint_distance", "distance_per_min", "max_speed", "dec_count", "high_efforts"]:
        if metric in weekly.columns:
            weekly[f"{metric}_rolling4"] = weekly[metric].rolling(4, min_periods=2).mean()
            weekly[f"{metric}_change"] = weekly[metric].pct_change()

    contexts = []
    for idx, row in weekly.iterrows():
        contexts.append(classify_week_context(row, weekly.iloc[:idx]))
    weekly["periodizacios_tipus"] = contexts
    return weekly


def calculate_readiness_score(df: pd.DataFrame, selected_week: str, playstyle: str) -> Tuple[int, Dict[str, float], List[str]]:
    daily = build_microcycle_table(df, selected_week)
    weekly = build_weekly_fingerprints(df)
    current_week = weekly[weekly["week"] == selected_week]
    if current_week.empty:
        return 50, {}, ["Nincs elég adat a readiness számításhoz."]

    score = 75.0
    components = {}
    reasons = []

    row = current_week.iloc[0]

    # 1. Load trend komponens
    load_change = row.get("training_load_change", np.nan)
    if pd.notna(load_change):
        if load_change > 0.25:
            score -= 12
            reasons.append("A heti terhelés jelentősen nőtt az előző héthez képest.")
        elif load_change < -0.30:
            score -= 6
            reasons.append("A heti terhelés jelentősen visszaesett, ami alulterheltséget is jelezhet.")
        else:
            score += 4
        components["load_trend"] = max(0, min(100, 80 - abs(load_change) * 60))
    else:
        components["load_trend"] = 55

    # 2. Maximális sebességű inger
    match = daily[daily["session_type"] == "Meccs"] if not daily.empty else pd.DataFrame()
    train = daily[daily["session_type"] == "Edzés"] if not daily.empty else pd.DataFrame()
    speed_component = 60
    if not match.empty and not train.empty and "sprint_distance" in daily.columns:
        match_sprint = match["sprint_distance"].mean()
        max_train_sprint = train["sprint_distance"].max()
        if pd.notna(match_sprint) and match_sprint > 0 and pd.notna(max_train_sprint):
            ratio = max_train_sprint / match_sprint
            speed_component = min(100, ratio / 0.35 * 100)
            if ratio < 0.15:
                score -= 15
                reasons.append("A héten alig látszik maximális sebességű inger a meccsigényhez képest.")
            elif ratio < 0.30:
                score -= 7
                reasons.append("A maximális sebességű inger visszafogott volt.")
            else:
                score += 5
    components["speed_exposure"] = max(0, min(100, speed_component))

    # 3. Taper / MD-1 / MD-2 kontroll
    taper_component = 65
    if not daily.empty and "MD" in daily["md_label"].values:
        md1 = daily[daily["md_label"] == "MD-1"]
        md2 = daily[daily["md_label"] == "MD-2"]
        md34 = daily[daily["md_label"].isin(["MD-3", "MD-4"])]
        if not md1.empty and not md34.empty:
            peak_early = md34["load_index"].max()
            md1_load = md1["load_index"].sum()
            if pd.notna(peak_early) and peak_early > 0 and pd.notna(md1_load):
                ratio = md1_load / peak_early
                taper_component = max(0, min(100, (1.0 - ratio) * 130))
                if ratio > 0.65:
                    score -= 10
                    reasons.append("Az MD-1 terhelés magas lehetett a frissességhez képest.")
                elif ratio < 0.45:
                    score += 6
        if not md2.empty and not md34.empty:
            peak_early = md34["load_index"].max()
            md2_load = md2["load_index"].sum()
            if pd.notna(peak_early) and peak_early > 0 and pd.notna(md2_load) and md2_load / peak_early > 0.80:
                score -= 8
                reasons.append("Az MD-2 terhelés közel volt a hét fő terhelési napjához.")
    components["tapering"] = max(0, min(100, taper_component))

    # 4. Játékmodell illeszkedés
    playstyle_component = 70
    current = df[df["week"] == selected_week]
    cur_train = current[current["session_type"] == "Edzés"]
    cur_match = current[current["session_type"] == "Meccs"]
    if not cur_train.empty and not cur_match.empty:
        def ratio(metric):
            if metric not in current.columns:
                return np.nan
            m = cur_match[metric].mean()
            t = cur_train[metric].mean()
            return t / m if pd.notna(m) and m > 0 and pd.notna(t) else np.nan

        int_ratio = ratio("distance_per_min")
        spr_ratio = ratio("sprint_distance")
        eff_ratio = ratio("high_efforts")

        if playstyle == "Pressing":
            vals = [v for v in [int_ratio / 0.90 if pd.notna(int_ratio) else np.nan,
                                eff_ratio / 0.75 if pd.notna(eff_ratio) else np.nan] if pd.notna(v)]
        elif playstyle == "Transition":
            vals = [spr_ratio / 0.80] if pd.notna(spr_ratio) else []
        elif playstyle == "Possession":
            vals = [1.0 - max(0, (int_ratio - 1.15)) if pd.notna(int_ratio) else np.nan]
            vals = [v for v in vals if pd.notna(v)]
        elif playstyle == "Low Block":
            vals = [spr_ratio / 0.60] if pd.notna(spr_ratio) else []
        else:
            vals = [1.0]

        if vals:
            playstyle_component = max(0, min(100, np.mean([min(1.15, v) for v in vals]) * 85))
            if playstyle_component < 60:
                score -= 8
                reasons.append(f"A heti profil nem illeszkedik elég jól a(z) {playstyle} játékmodellhez.")
            elif playstyle_component > 80:
                score += 3

    components["playstyle_fit"] = max(0, min(100, playstyle_component))

    # 5. Meccskészültség végső skála
    score = int(max(0, min(100, round(score))))
    if not reasons:
        reasons.append("A readiness fő komponensei stabilnak tűnnek.")
    return score, components, reasons


def build_pattern_insights(df: pd.DataFrame, selected_week: str) -> List[Insight]:
    insights: List[Insight] = []
    weekly = build_weekly_fingerprints(df)
    if weekly.empty or selected_week not in weekly["week"].values:
        return insights

    idx = weekly.index[weekly["week"] == selected_week][0]
    hist = weekly.iloc[max(0, idx-5):idx+1].copy()

    if len(hist) < 3:
        insights.append(Insight(
            "Kevés történeti adat", "INFORMÁCIÓ",
            "A multi-week mintázatokhoz legalább 3 hét adat szükséges.",
            "Kevesebb adat mellett a rendszer inkább óvatos heti következtetéseket tud adni.",
            "Érdemes több heti adatot egy fájlban feltölteni vagy használni a performance memória funkciót.",
            scope="Memory",
        ))
        return insights

    # Sprint trend
    if "sprint_distance" in hist.columns:
        label = trend_label(hist["sprint_distance"].tolist())
        if label == "csökkenő":
            insights.append(Insight(
                "Többhetes sprintcsökkenés", "FIGYELMEZTETÉS",
                "Az elmúlt hetek sprintprofilja csökkenő mintázatot mutat.",
                "A tartós maximális sebességű inger hiány hosszabb távon ronthatja a maximális sebesség és intenzitás fenntartását.",
                "Érdemes célzottan megvizsgálni, hogy tudatos terheléscsökkentésről vagy nem kívánt intenzitáshiányról van-e szó.",
                scope="Memory",
            ))

    # Load trend
    if "training_load" in hist.columns:
        label = trend_label(hist["training_load"].tolist())
        if label == "emelkedő":
            insights.append(Insight(
                "Többhetes terhelésnövekedés", "FIGYELMEZTETÉS",
                "Az elmúlt hetek terhelési profilja emelkedő mintázatot mutat.",
                "A folyamatos load növekedés hasznos lehet építő periódusban, de frissességi problémát is okozhat.",
                "Érdemes ellenőrizni, hogy a növekvő terhelés illeszkedik-e a periodizációs célhoz.",
                scope="Memory",
            ))

    # Max speed trend
    if "max_speed" in hist.columns:
        label = trend_label(hist["max_speed"].tolist(), tolerance=0.02)
        if label == "csökkenő":
            insights.append(Insight(
                "Max sebesség csökkenő trend", "INFORMÁCIÓ",
                "Az elmúlt hetek maximális sebességprofilja enyhén csökkenő mintázatot mutat.",
                "Ez lehet edzéstartalom-függő, de jelezhet neuromuszkuláris frissességi problémát is.",
                "Érdemes ellenőrizni, hogy volt-e megfelelő maximális sebességű inger a hetekben.",
                scope="Memory",
            ))

    return insights


def memory_file_exists() -> bool:
    return MEMORY_FILE.exists()


def load_memory_df() -> pd.DataFrame:
    if not MEMORY_FILE.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(MEMORY_FILE, parse_dates=["start_time"])
    except Exception:
        return pd.DataFrame()


def save_to_memory(df: pd.DataFrame) -> Tuple[bool, str]:
    try:
        existing = load_memory_df()
        combined = pd.concat([existing, df], ignore_index=True) if not existing.empty else df.copy()
        # Duplikáció minimalizálása.
        key_cols = [c for c in ["player_name", "start_time", "session_type", "session_name", "total_distance", "training_load"] if c in combined.columns]
        if key_cols:
            combined = combined.drop_duplicates(subset=key_cols, keep="last")
        combined.to_csv(MEMORY_FILE, index=False, encoding="utf-8-sig")
        return True, f"Memory mentve: {len(combined)} sor."
    except Exception as exc:
        return False, f"Memory mentés sikertelen: {exc}"


def merge_with_memory(current_df: pd.DataFrame, use_memory: bool) -> pd.DataFrame:
    if not use_memory:
        return current_df
    mem = load_memory_df()
    if mem.empty:
        return current_df
    combined = pd.concat([mem, current_df], ignore_index=True)
    key_cols = [c for c in ["player_name", "start_time", "session_type", "session_name", "total_distance", "training_load"] if c in combined.columns]
    if key_cols:
        combined = combined.drop_duplicates(subset=key_cols, keep="last")
    # Dátummezők visszaállítása.
    if "start_time" in combined.columns:
        combined["start_time"] = pd.to_datetime(combined["start_time"], errors="coerce")
        combined["session_date"] = combined["start_time"].dt.date
        combined["week"] = make_iso_week_series(combined["start_time"])
    return combined


def build_adaptive_recommendations(
    insights: List[Insight],
    readiness_score: int,
    periodization_type: str,
    pattern_insights: List[Insight],
    playstyle: str
) -> List[Dict[str, str]]:
    recs = []

    if readiness_score < 55:
        recs.append({
            "Cím": "Meccskészültség elsődleges figyelem",
            "Súlyosság": "KRITIKUS",
            "Teendő": "A következő edzésen érdemes óvatosan bánni a terheléssel, és külön figyelni, mennyire frissek a játékosok.",
            "Miért": "A meccskészültségi pontszám alacsony, vagyis több jel is arra utal, hogy a csapat nem teljesen friss.",
        })
    elif readiness_score < 70:
        recs.append({
            "Cím": "Meccskészültség kontroll",
            "Súlyosság": "FIGYELMEZTETÉS",
            "Teendő": "A következő 1–2 edzésen ne a plusz terhelés legyen a fő cél, hanem a frissesség stabil megtartása.",
            "Miért": "A csapat nincs rossz állapotban, de nem is tűnik teljesen frissnek. Ilyenkor a túl nagy változtatás visszaüthet.",
        })

    if "overload" in periodization_type.lower() or "terhelésépítő" in periodization_type.lower():
        recs.append({
            "Cím": "Overload hét kontrollja",
            "Súlyosság": "FIGYELMEZTETÉS",
            "Teendő": "Ellenőrizd, hogy a magasabb terhelés tervezett-e, és legyen meg a következő frissítő blokk.",
            "Miért": "Terhelésépítő héten a következő napok/frissítés minősége kulcsfontosságú.",
        })
    elif "recovery" in periodization_type.lower() or "alulterhelt" in periodization_type.lower():
        recs.append({
            "Cím": "Könnyebb hét értelmezése",
            "Súlyosság": "INFORMÁCIÓ",
            "Teendő": "Tisztázd, hogy ez szándékosan könnyebb hét volt-e. Ha igen, rendben lehet; ha nem, akkor hiányozhatott a megfelelő edzésinger.",
            "Miért": "Az alacsonyabb terhelés rövid távon frissíthet, de ha több héten át így marad, a csapat intenzitása visszaeshet.",
        })

    for ins in pattern_insights:
        if ins.severity in ["KRITIKUS", "FIGYELMEZTETÉS"]:
            recs.append({
                "Cím": ins.title,
                "Súlyosság": ins.severity,
                "Teendő": ins.recommendation,
                "Miért": ins.impact,
            })

    # Alap insightokból pótoljuk 3 elemre.
    for item in top_coaching_priorities(insights, limit=5):
        if len(recs) >= 3:
            break
        if item["Cím"] not in [r["Cím"] for r in recs]:
            recs.append(item)

    return recs[:3]


def render_score_card(title: str, score: int, subtitle: str, reasons: List[str]) -> None:
    color = score_to_color(score)
    reason_html = "<br>".join([f"• {html.escape(str(r))}" for r in reasons[:4]])
    st.markdown(
        f"""
        <div class="score-card">
            <div class="score-number" style="color:{color};">{score}/100</div>
            <div class="score-label">{html.escape(title)}</div>
            <div class="mini-muted">{html.escape(subtitle)}</div>
            <div class="mini-muted" style="margin-top:10px;">{reason_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def severity_icon(sev: str) -> str:
    if sev == "KRITIKUS":
        return "🔴"
    if sev == "FIGYELMEZTETÉS":
        return "🟠"
    return "🔵"


def severity_class(sev: str) -> str:
    if sev == "KRITIKUS":
        return "pill-critical"
    if sev == "FIGYELMEZTETÉS":
        return "pill-warning"
    return "pill-info"


def metric_card(label: str, value: object, help_text: str = ""):
    st.metric(label, value if value is not None else "—", help=help_text)


def _safe_filename_week(week: str) -> str:
    return re.sub(r"[^0-9A-Za-z_-]+", "_", str(week)).strip("_") or "het"


def build_insight_export_df(insights: List[Insight]) -> pd.DataFrame:
    df = pd.DataFrame([i.as_dict() for i in insights])
    if df.empty:
        return df
    order = {"KRITIKUS": 1, "FIGYELMEZTETÉS": 2, "INFORMÁCIÓ": 3}
    df.insert(0, "Prioritás", df["Súlyosság"].map(order).fillna(9).astype(int))
    df["Súlyosság"] = df["Súlyosság"].map({
        "KRITIKUS": "🔴 KRITIKUS",
        "FIGYELMEZTETÉS": "🟠 FIGYELMEZTETÉS",
        "INFORMÁCIÓ": "🔵 INFORMÁCIÓ",
    }).fillna(df["Súlyosság"])
    return df


def render_insight_cards(insights: List[Insight]) -> None:
    for ins in insights:
        pill = severity_class(ins.severity)
        st.markdown(
            f"""
            <div class="insight-card">
                <div>
                    <span class="pill {pill}">{severity_icon(ins.severity)} {html.escape(ins.severity)}</span>
                    <span class="pill pill-info">{html.escape(ins.scope)}</span>
                </div>
                <div class="insight-title">{html.escape(ins.title)}</div>
                <div class="insight-label">Mit látunk?</div>
                <div class="insight-text">{html.escape(ins.observation)}</div>
                <div class="insight-label">Miért fontos?</div>
                <div class="insight-text">{html.escape(ins.impact)}</div>
                <div class="insight-label">Javaslat</div>
                <div class="insight-text">{html.escape(ins.recommendation)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_wrapped_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Nincs megjeleníthető adat.")
        return
    table_html = ['<div class="wrap-table"><table>']
    table_html.append("<thead><tr>" + "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns) + "</tr></thead>")
    table_html.append("<tbody>")
    for _, row in df.iterrows():
        table_html.append("<tr>" + "".join(f"<td>{html.escape(str(row.get(c, '')))}</td>" for c in df.columns) + "</tr>")
    table_html.append("</tbody></table></div>")
    st.markdown("".join(table_html), unsafe_allow_html=True)


def insights_to_excel_bytes(insights_df: pd.DataFrame, selected_week: str) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        insights_df.to_excel(writer, index=False, sheet_name="Megállapítások", startrow=3)
        wb = writer.book
        ws = writer.sheets["Megállapítások"]

        from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
        from openpyxl.utils import get_column_letter

        max_col = max(1, len(insights_df.columns))
        ws["A1"] = "Performance megállapítások és javaslatok"
        ws["A2"] = f"Hét: {selected_week}"
        ws["A3"] = f"Generálva: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max_col)
        ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=max_col)
        ws["A1"].font = Font(bold=True, size=16)
        ws["A2"].font = Font(bold=True, size=11)
        ws["A3"].font = Font(italic=True, size=10)

        header_row = 4
        header_fill = PatternFill("solid", fgColor="1F4E78")
        header_font = Font(color="FFFFFF", bold=True)
        thin = Side(style="thin", color="D9E2F3")

        for cell in ws[header_row]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)

        widths = {
            "Prioritás": 10,
            "Súlyosság": 18,
            "Terület": 14,
            "Megállapítás": 28,
            "Mit látunk?": 58,
            "Miért fontos?": 58,
            "Javaslat": 68,
        }
        for idx, col_name in enumerate(insights_df.columns, start=1):
            ws.column_dimensions[get_column_letter(idx)].width = widths.get(str(col_name), 22)

        for row in ws.iter_rows(min_row=5, max_row=ws.max_row, max_col=ws.max_column):
            max_lines = 1
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
                cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
                text = str(cell.value or "")
                max_lines = max(max_lines, min(8, (len(text) // 50) + 1))
            ws.row_dimensions[row[0].row].height = max(26, max_lines * 17)

        ws.freeze_panes = "A5"
        ws.auto_filter.ref = ws.dimensions
    return output.getvalue()


def insights_to_word_bytes(insights_df: pd.DataFrame, selected_week: str) -> Optional[bytes]:
    if Document is None:
        return None
    doc = Document()
    section = doc.sections[0]
    section.left_margin = Inches(0.55)
    section.right_margin = Inches(0.55)
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.55)

    doc.add_heading("Performance megállapítások és javaslatok", level=1)
    p = doc.add_paragraph()
    p.add_run(f"Hét: {selected_week}\n").bold = True
    p.add_run(f"Generálva: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    for _, row in insights_df.iterrows():
        doc.add_heading(f"{row.get('Súlyosság', '')} · {row.get('Megállapítás', '')}", level=2)
        meta = doc.add_paragraph()
        meta.add_run("Terület: ").bold = True
        meta.add_run(str(row.get("Terület", "")))
        for label in ["Mit látunk?", "Miért fontos?", "Javaslat"]:
            para = doc.add_paragraph()
            para.add_run(f"{label}: ").bold = True
            para.add_run(str(row.get(label, "")))

    doc.add_page_break()
    doc.add_heading("Összesítő tábla", level=2)
    table = doc.add_table(rows=1, cols=len(insights_df.columns))
    table.style = "Table Grid"
    hdr_cells = table.rows[0].cells
    for i, col in enumerate(insights_df.columns):
        hdr_cells[i].text = str(col)
        for paragraph in hdr_cells[i].paragraphs:
            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(8)

    for _, row in insights_df.iterrows():
        cells = table.add_row().cells
        for i, col in enumerate(insights_df.columns):
            cells[i].text = str(row.get(col, ""))
            for paragraph in cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(8)

    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()


def _register_pdf_font() -> Tuple[str, str]:
    """ReportLab alapfontjai nem kezelik jól a magyar ékezeteket.
    Ezért megpróbálunk DejaVuSans betűtípust regisztrálni, ami Streamlit Cloudon
    és Linuxon általában elérhető. Ha nem található, visszaesünk Helvetica-ra.
    """
    if pdfmetrics is None or TTFont is None:
        return "Helvetica", "Helvetica-Bold"

    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    bold_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
        "/usr/local/share/fonts/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]

    normal_path = next((fp for fp in font_candidates if Path(fp).exists()), None)
    bold_path = next((fp for fp in bold_candidates if Path(fp).exists()), None)

    if not normal_path:
        return "Helvetica", "Helvetica-Bold"

    try:
        pdfmetrics.registerFont(TTFont("DejaVuSans", normal_path))
        if bold_path:
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold_path))
            return "DejaVuSans", "DejaVuSans-Bold"
        return "DejaVuSans", "DejaVuSans"
    except Exception:
        return "Helvetica", "Helvetica-Bold"


def insights_to_pdf_bytes(insights_df: pd.DataFrame, selected_week: str) -> Optional[bytes]:
    if SimpleDocTemplate is None:
        return None

    font_name, font_bold = _register_pdf_font()

    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=0.8 * cm,
        leftMargin=0.8 * cm,
        topMargin=0.8 * cm,
        bottomMargin=0.8 * cm,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "MagyarCim",
        parent=styles["Title"],
        fontName=font_bold,
        fontSize=17,
        leading=21,
        spaceAfter=10,
    )
    meta_style = ParagraphStyle(
        "MagyarMeta",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        leading=11,
    )
    normal = ParagraphStyle(
        "MagyarNormalWrapped",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=7,
        leading=9,
        wordWrap="CJK",
    )
    header = ParagraphStyle(
        "MagyarHeaderWrapped",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=7,
        leading=9,
        textColor=colors.white,
        wordWrap="CJK",
    )

    story = [
        Paragraph(pdf_safe_text("Performance megállapítások és javaslatok"), title_style),
        Paragraph(pdf_safe_text(f"Hét: {selected_week} · Generálva: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), meta_style),
        Spacer(1, 0.25 * cm),
    ]

    cols = ["Súlyosság", "Terület", "Megállapítás", "Mit látunk?", "Miért fontos?", "Javaslat"]
    cols = [c for c in cols if c in insights_df.columns]

    def safe_paragraph(value, style):
        text = "" if pd.isna(value) else str(value)
        text = pdf_safe_text(text)
        return Paragraph(html.escape(text).replace("\n", "<br/>",), style)

    table_data = [[safe_paragraph(c, header) for c in cols]]
    for _, row in insights_df.iterrows():
        table_data.append([safe_paragraph(row.get(c, ""), normal) for c in cols])

    col_widths_map = {
        "Súlyosság": 2.6 * cm,
        "Terület": 2.0 * cm,
        "Megállapítás": 3.8 * cm,
        "Mit látunk?": 6.0 * cm,
        "Miért fontos?": 6.0 * cm,
        "Javaslat": 7.2 * cm,
    }
    table = Table(table_data, colWidths=[col_widths_map.get(c, 3 * cm) for c in cols], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), font_bold),
        ("FONTNAME", (0, 1), (-1, -1), font_name),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BFBFBF")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)

    # V5 PDF pages - past/current/next split planning
    try:
        _past_review = globals().get("past_week_review_df", pd.DataFrame())
        _past_text = globals().get("past_week_review_text", "")
        _current_plan = globals().get("current_remaining_plan_df", pd.DataFrame())
        _current_text = globals().get("current_remaining_text", "")
        _next_week_plan = globals().get("next_week_plan_df", pd.DataFrame())
        _next_week_text = globals().get("next_week_plan_text", "")
        _player_actions = globals().get("player_next_actions_df", pd.DataFrame())

        try:
            from reportlab.platypus import PageBreak
        except Exception:
            PageBreak = None

        if PageBreak:
            story.append(PageBreak())
        story.append(P("Múlt hét / aktuális hét / jövő hét", title))
        story.append(P("Teljes múlt heti értékelés, aktuális hét hátralévő napjai, és jövő heti mikrociklus terv.", subtitle))

        story.append(section_bar("1) Múlt hét -> javaslat erre a hétre"))
        story.append(data_table([[P("Összefoglaló", header)], [P(_past_text, body)]], [27.7 * cm], header_bg="#1E3A8A", row_bgs=[colors.HexColor("#EFF6FF")]))
        if _past_review is not None and not _past_review.empty:
            cols = [c for c in ["Prioritás", "Múlt heti megállapítás", "Súlyosság", "Javaslat erre a hétre"] if c in _past_review.columns]
            pdata = [[P(c, header) for c in cols]]
            for _, rr in _past_review.head(6).iterrows():
                pdata.append([P(rr.get(c, ""), tiny) for c in cols])
            story.append(data_table(pdata, [1.7 * cm, 7.0 * cm, 3.0 * cm, 16.0 * cm][:len(cols)], header_bg="#0F172A", row_bgs=[colors.white, colors.HexColor("#F8FAFC")]))

        story += [Spacer(1, 0.25 * cm)]
        story.append(section_bar("2) Aktuális hét -> hátralévő napok"))
        story.append(data_table([[P("Összefoglaló", header)], [P(_current_text, body)]], [27.7 * cm], header_bg="#166534", row_bgs=[colors.HexColor("#ECFDF5")]))
        if _current_plan is not None and not _current_plan.empty:
            cols = [c for c in ["Hátralévő pont", "Fókusz", "Ajánlott terhelés", "Javaslat"] if c in _current_plan.columns]
            cdata = [[P(c, header) for c in cols]]
            for _, rr in _current_plan.head(6).iterrows():
                cdata.append([P(rr.get(c, ""), tiny) for c in cols])
            story.append(data_table(cdata, [3.2 * cm, 4.8 * cm, 3.5 * cm, 16.2 * cm][:len(cols)], header_bg="#166534", row_bgs=[colors.white, colors.HexColor("#ECFDF5")]))

        if PageBreak:
            story.append(PageBreak())
        story.append(P("Jövő heti mikrociklus terv", title))
        story.append(P(_next_week_text, subtitle))
        if _next_week_plan is not None and not _next_week_plan.empty:
            cols = [c for c in ["Nap", "Szerep", "Fő cél", "Ajánlott terhelés", "Javaslat", "Tervezési alap"] if c in _next_week_plan.columns]
            ndata = [[P(c, header) for c in cols]]
            for _, rr in _next_week_plan.head(8).iterrows():
                ndata.append([P(rr.get(c, ""), tiny) for c in cols])
            story.append(data_table(ndata, [1.7 * cm, 3.2 * cm, 4.0 * cm, 3.0 * cm, 8.8 * cm, 7.0 * cm][:len(cols)], header_bg="#312E81", row_bgs=[colors.white, colors.HexColor("#F5F3FF")]))

        if _player_actions is not None and not _player_actions.empty:
            story += [Spacer(1, 0.25 * cm)]
            story.append(section_bar("Játékosszintű következő teendők"))
            cols = [c for c in ["Játékos", "Prioritás", "Holnap / következő edzés", "Következő hét", "Indok"] if c in _player_actions.columns]
            adata = [[P(c, header) for c in cols]]
            for _, rr in _player_actions.head(8).iterrows():
                adata.append([P(rr.get(c, ""), tiny) for c in cols])
            story.append(data_table(adata, [3.3 * cm, 2.5 * cm, 7.0 * cm, 7.0 * cm, 7.9 * cm][:len(cols)], header_bg="#7F1D1D", row_bgs=[colors.white, colors.HexColor("#FFF7ED")]))
    except Exception:
        pass


    doc.build(story)
    return output.getvalue()



# -----------------------------------------------------------------------------
# V3 - Premium visualization + Player Risk + Positional layer + improved PDF
# -----------------------------------------------------------------------------
POSITION_GROUPS = {
    "Kapus": ["gk", "kapus", "goalkeeper"],
    "Belső védő": ["cb", "belső védő", "center back", "centre back"],
    "Szélső védő": ["fb", "wb", "szélső védő", "fullback", "wingback"],
    "Középpályás": ["cm", "dm", "am", "középpályás", "midfielder"],
    "Szélső": ["winger", "szélső", "wide"],
    "Csatár": ["st", "cf", "csatár", "striker", "forward"],
}

def infer_position_group(value: object) -> str:
    if value is None or pd.isna(value): return "Ismeretlen"
    text = str(value).lower().strip()
    for group, keys in POSITION_GROUPS.items():
        if any(k in text for k in keys): return group
    return str(value).strip() if str(value).strip() else "Ismeretlen"

def add_position_group(df: pd.DataFrame) -> pd.DataFrame:
    out=df.copy(); out["position_group"] = out["position"].apply(infer_position_group) if "position" in out.columns else "Ismeretlen"; return out

def calculate_player_risk(df: pd.DataFrame, selected_week: str) -> pd.DataFrame:
    pw=player_weekly(df)
    if pw.empty or selected_week not in pw["week"].values: return pd.DataFrame()
    weeks=sorted(pw["week"].dropna().unique().tolist()); idx=weeks.index(selected_week)
    cur=pw[pw["week"]==selected_week].copy(); hist=pw[pw["week"].isin(weeks[max(0,idx-4):idx])].copy(); rows=[]
    for _, row in cur.iterrows():
        player=row["player_name"]; hp=hist[hist["player_name"]==player]; score=20; reasons=[]
        is_gk = bool(row.get("is_goalkeeper", False))
        # Kapusnál nem büntetjük ugyanúgy az alacsony sprint/HSR profilt.
        # A risk fő fókusza nála a teljes load, high efforts, lassítás/gyorsulás és játékperc.
        metric_pack = [
            ("training_load", .35 if is_gk else .30, -0.40 if is_gk else -0.35, "Terhelési pont"),
            ("high_efforts", .45 if is_gk else .35, -0.45 if is_gk else -0.40, "High Efforts"),
            ("dec_count", .45 if is_gk else .35, -0.45 if is_gk else -0.40, "Lassítás"),
        ]
        if not is_gk:
            metric_pack.append(("sprint_distance", .45, -0.45, "Sprinttáv"))
        for metric, hi, lo, lab in metric_pack:
            if metric in row.index and metric in hp.columns:
                v=row.get(metric,np.nan); base=hp[metric].mean()
                if pd.notna(v) and pd.notna(base) and base!=0:
                    d=(v-base)/base
                    if d>hi: score+=18; reasons.append(f"{lab}: +{d:.0%} a saját átlaghoz képest")
                    elif d<lo: score+=8; reasons.append(f"{lab}: {d:.0%} a saját átlaghoz képest")
        if "player_minutes" in row.index and "player_minutes" in hp.columns:
            v=row.get("player_minutes",np.nan); base=hp["player_minutes"].mean()
            if pd.notna(v) and pd.notna(base) and base>0 and abs((v-base)/base)>.35:
                d=(v-base)/base; score+=8; reasons.append(f"Játékperc/exposure: {d:+.0%} a saját átlaghoz képest")
        if (not is_gk) and "max_speed" in row.index and "max_speed" in hp.columns:
            v=row.get("max_speed",np.nan); base=hp["max_speed"].max()
            if pd.notna(v) and pd.notna(base) and base>0 and (v-base)/base < -.06:
                score+=14; reasons.append(f"Max sebesség: {(v-base)/base:.0%} a saját csúcshoz képest")
        score=int(max(0,min(100,score))); level="Magas" if score>=70 else ("Közepes" if score>=45 else "Alacsony")
        role = "Kapus" if is_gk else "Mezőny"
        rows.append({"Játékos":player,"Szerep":role,"Típus":row.get("session_type",""),"Játékperc":round(row.get("player_minutes",0) or 0,1),"Kockázati pontszám":score,"Kockázati szint":level,"Fő okok":"; ".join(reasons[:3]) if reasons else "Nincs jelentős eltérés a saját előzményhez képest."})
    res=pd.DataFrame(rows); return res.sort_values("Kockázati pontszám",ascending=False) if not res.empty else res

def render_premium_kpi(label: str, value: str, note: str="", color: str="#22c55e") -> None:
    st.markdown(f"""<div class='premium-kpi'><div class='premium-kpi-label'>{html.escape(label)}</div><div class='premium-kpi-value' style='color:{color};'>{html.escape(str(value))}</div><div class='premium-kpi-note'>{html.escape(note)}</div></div>""", unsafe_allow_html=True)

def render_hero(selected_week: str, selected_playstyle: str, readiness_score: int, periodization_type: str) -> None:
    color=score_to_color(readiness_score) if "score_to_color" in globals() else "#22c55e"; label=score_to_label(readiness_score) if "score_to_label" in globals() else ""
    st.markdown(f"""<div class='hero-box'><div class='hero-title'>Football Performance Intelligence</div><div class='hero-sub'><span class='section-chip'>Hét: {html.escape(str(selected_week))}</span><span class='section-chip'>Játékmodell: {html.escape(str(selected_playstyle))}</span><span class='section-chip'>Meccskészültség: <b style='color:{color};'>{readiness_score}/100</b> - {html.escape(label)}</span><span class='section-chip'>Periodizáció: {html.escape(str(periodization_type))}</span></div></div>""", unsafe_allow_html=True)

def render_risk_cards(risk_df: pd.DataFrame, limit: int=5) -> None:
    if risk_df.empty: st.info("Nincs elég adat játékosszintű risk engine számításhoz."); return
    for _, row in risk_df.head(limit).iterrows():
        level=row.get("Kockázati szint","Alacsony"); css="risk-high" if level=="Magas" else ("risk-medium" if level=="Közepes" else "risk-low")
        st.markdown(f"""<div class='insight-card {css}'><div class='insight-title'>{html.escape(str(row.get('Játékos','')))} · {html.escape(str(level))} kockázat · {row.get('Kockázati pontszám',0)}/100</div><div class='insight-label'>Fő okok</div><div class='insight-text'>{html.escape(str(row.get('Fő okok','')))}</div></div>""", unsafe_allow_html=True)





# -----------------------------------------------------------------------------
# V5 - Past / current / next microcycle planning
# -----------------------------------------------------------------------------
def week_completeness_summary(df: pd.DataFrame, selected_week: str) -> Dict[str, object]:
    """Részleges hét értelmezése.
    Nem kell teljes hét: 1-2-3 edzés alapján is adunk folyamat közbeni visszajelzést.
    """
    if df is None or df.empty or "week" not in df.columns:
        return {
            "status": "Nincs adat",
            "sessions": 0,
            "train_days": 0,
            "match_days": 0,
            "days": 0,
            "last_day": None,
            "message": "Nincs értelmezhető heti adat.",
        }

    week_df = df[df["week"] == selected_week].copy()
    if week_df.empty:
        return {
            "status": "Nincs adat",
            "sessions": 0,
            "train_days": 0,
            "match_days": 0,
            "days": 0,
            "last_day": None,
            "message": "Az aktuális hétre nincs adat.",
        }

    week_df["session_date_dt"] = pd.to_datetime(week_df["session_date"], errors="coerce")
    sessions = len(week_df[["session_date_dt", "session_type"]].drop_duplicates()) if "session_type" in week_df.columns else week_df["session_date_dt"].nunique()
    train_days = week_df.loc[week_df["session_type"] == "Edzés", "session_date_dt"].dt.date.nunique() if "session_type" in week_df.columns else 0
    match_days = week_df.loc[week_df["session_type"] == "Meccs", "session_date_dt"].dt.date.nunique() if "session_type" in week_df.columns else 0
    days = week_df["session_date_dt"].dt.date.nunique()
    last_day = week_df["session_date_dt"].max()

    if match_days > 0:
        status = "Teljes / meccsel együtt értelmezhető hét"
    elif train_days <= 2:
        status = "Aktuális / folyamatban lévő hét - korai jelzés"
    elif train_days <= 4:
        status = "Aktuális / folyamatban lévő hét - tervezési pont"
    else:
        status = "Majdnem teljes edzéshet"

    message = (
        f"{status}. Eddig {train_days} edzésnap és {match_days} meccsnap látható. "
        "A javaslatokat a rendelkezésre álló adatokhoz igazítjuk, nem feltételezzük, hogy a hét teljes."
    )

    return {
        "status": status,
        "sessions": sessions,
        "train_days": train_days,
        "match_days": match_days,
        "days": days,
        "last_day": last_day,
        "message": message,
    }


def get_surrounding_week_context(df: pd.DataFrame, selected_week: str) -> Dict[str, Optional[str]]:
    weeks_sorted = sorted(df["week"].dropna().unique().tolist()) if df is not None and not df.empty and "week" in df.columns else []
    if selected_week not in weeks_sorted:
        return {"previous_week": None, "current_week": selected_week, "next_data_week": None}
    i = weeks_sorted.index(selected_week)
    return {
        "previous_week": weeks_sorted[i - 1] if i > 0 else None,
        "current_week": selected_week,
        "next_data_week": weeks_sorted[i + 1] if i < len(weeks_sorted) - 1 else None,
    }


def build_past_week_review(
    df: pd.DataFrame,
    selected_week: str,
    playstyle: str,
) -> Tuple[pd.DataFrame, str]:
    """Múlt hét teljes elemzése + javaslat az aktuális hétre."""
    ctx = get_surrounding_week_context(df, selected_week)
    prev_week = ctx.get("previous_week")
    if not prev_week:
        return pd.DataFrame(), "Nincs előző hét adat. Az aktuális javaslat csak a kiválasztott hét alapján készül."

    prev_insights = (
        team_insights(df, prev_week)
        + microcycle_insights(df, prev_week)
        + playstyle_insights(df, prev_week, playstyle)
        + build_pattern_insights(df, prev_week)
    )
    prev_insights = sorted(prev_insights, key=lambda x: SEVERITY_RANK.get(x.severity, 9))[:10]
    prev_readiness, _, _ = calculate_readiness_score(df, prev_week, playstyle)

    prev_fp = build_weekly_fingerprints(df)
    prev_period = "Nincs elég adat"
    if prev_fp is not None and not prev_fp.empty and "week" in prev_fp.columns:
        row = prev_fp[prev_fp["week"] == prev_week]
        if not row.empty and "periodizacios_tipus" in row.columns:
            prev_period = row["periodizacios_tipus"].iloc[0]

    rows = []
    for i, ins in enumerate(prev_insights, 1):
        rows.append({
            "Prioritás": i,
            "Múlt heti megállapítás": ins.title,
            "Súlyosság": ins.severity,
            "Mit láttunk?": ins.observation,
            "Javaslat erre a hétre": ins.recommendation,
        })

    if not rows:
        rows.append({
            "Prioritás": 1,
            "Múlt heti megállapítás": "Stabil hét",
            "Súlyosság": "INFORMÁCIÓ",
            "Mit láttunk?": "Nem látható kiemelt negatív eltérés.",
            "Javaslat erre a hétre": "A struktúra megtartható, de sprint/load/risk monitoring maradjon aktív.",
        })

    txt = (
        f"Múlt hét: {format_week_label(prev_week)}\n"
        f"Readiness: {prev_readiness}/100 ({score_to_label(prev_readiness)})\n"
        f"Periodizáció: {prev_period}\n\n"
        "Ebből erre a hétre a fő cél: a kritikus/figyelmeztető pontok kezelése, "
        "miközben a frissességet és az egyéni risket kontroll alatt tartjuk."
    )
    return pd.DataFrame(rows), txt


def build_current_remaining_days_plan(
    df: pd.DataFrame,
    selected_week: str,
    playstyle: str,
    readiness_score: int,
    periodization_type: str,
    player_risk_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, str]:
    """Aktuális hét: eddigi feltöltött napok alapján javaslat a hátralévő napokra."""
    week_df = df[df["week"] == selected_week].copy() if df is not None and "week" in df.columns else pd.DataFrame()
    if week_df.empty:
        return pd.DataFrame(), "Nincs aktuális heti adat."

    week_df["session_date_dt"] = pd.to_datetime(week_df["session_date"], errors="coerce")
    last_day = week_df["session_date_dt"].max()
    match_day = detect_match_day(week_df)
    has_match = match_day is not None
    ws = week_completeness_summary(df, selected_week)

    if has_match and pd.notna(last_day) and match_day is not None and last_day.date() >= match_day.date():
        md_slots = ["MD+1", "Következő edzés", "Jövő hét előkészítés"]
    elif has_match:
        md_slots = ["Hátralévő edzés", "MD-2", "MD-1", "MD"]
    else:
        if ws.get("train_days", 0) <= 1:
            md_slots = ["Holnap", "Következő 2. edzés", "Következő 3. edzés", "Hétvégi meccs / referencia"]
        elif ws.get("train_days", 0) <= 3:
            md_slots = ["Holnap", "Hátralévő fő edzés", "Meccs előtti aktiváció", "Hétvégi meccs / referencia"]
        else:
            md_slots = ["Következő edzés", "Aktiváció", "Meccs / referencia"]

    high_risk = []
    if player_risk_df is not None and not player_risk_df.empty and "Kockázati szint" in player_risk_df.columns:
        high_risk = player_risk_df.loc[player_risk_df["Kockázati szint"] == "Magas", "Játékos"].head(5).tolist() if "Játékos" in player_risk_df.columns else []

    low_sprint = False
    intensity_gap = False
    train = week_df[week_df["session_type"] == "Edzés"] if "session_type" in week_df.columns else pd.DataFrame()
    match = week_df[week_df["session_type"] == "Meccs"] if "session_type" in week_df.columns else pd.DataFrame()
    if not train.empty:
        if "sprint_distance" in train.columns and train["sprint_distance"].mean() < 250:
            low_sprint = True
        if not match.empty and "distance_per_min" in week_df.columns and match["distance_per_min"].mean() > 0:
            intensity_gap = (train["distance_per_min"].mean() / match["distance_per_min"].mean()) < 0.88

    rows = []
    for slot in md_slots:
        if "MD+1" in slot:
            focus = "Regeneráció / pótló terhelés"
            rec = "Sokat játszóknak regeneráció, keveset játszóknak kontrollált kiegészítő blokk."
            load = "egyéni"
        elif "MD-1" in slot or "aktiváció" in slot.lower():
            focus = "Frissesség"
            rec = "Rövid aktiváció, alacsony volumen. Ne legyen új fárasztó inger."
            load = "alacsony"
        elif "MD-2" in slot:
            focus = "Taktikai kontroll"
            rec = "Taktikai fókusz, kevés lassítás/excentrikus terhelés. Magas risk játékosoknál limit."
            load = "alacsony-közepes"
        elif low_sprint or intensity_gap:
            focus = "Hiányzó intenzitás pótlása"
            rec = "Rövid, kontrollált sprint/max sebesség vagy magas tempójú játékblokk, kis volumennel."
            load = "közepes"
        else:
            focus = "Struktúra megtartása"
            rec = "A heti terv tartható, de egyéni risk és readiness kontroll javasolt."
            load = "közepes"

        if high_risk and load != "alacsony":
            rec += " Magas risk játékosoknál egyéni csökkentés: " + ", ".join(high_risk[:3]) + "."

        rows.append({
            "Hátralévő pont": slot,
            "Fókusz": focus,
            "Ajánlott terhelés": load,
            "Javaslat": rec,
            "Miért?": f"Eddig feltöltve: {ws.get('train_days', 0)} edzésnap, {ws.get('match_days', 0)} meccsnap. Readiness: {readiness_score}/100.",
        })

    txt = (
        f"Aktuális hét állapota: {ws.get('status')}\n"
        f"{ws.get('message')}\n\n"
        "A hátralévő napokra a javaslat nem teljes heti minősítés, hanem folyamat közbeni döntéstámogatás."
    )
    return pd.DataFrame(rows), txt


def build_next_microcycle_plan(
    df: pd.DataFrame,
    selected_week: str,
    playstyle: str,
    readiness_score: int,
    periodization_type: str,
    player_risk_df: pd.DataFrame,
) -> pd.DataFrame:
    """Jövő hét / következő mikrociklus javaslat MD-bontásban az eddigiek alapján."""
    week_df = df[df["week"] == selected_week].copy() if df is not None and "week" in df.columns else pd.DataFrame()

    low_sprint = False
    intensity_gap = False
    high_risk_players = []
    if player_risk_df is not None and not player_risk_df.empty:
        high_risk_players = player_risk_df.loc[player_risk_df["Kockázati szint"] == "Magas", "Játékos"].head(5).tolist() if "Kockázati szint" in player_risk_df.columns and "Játékos" in player_risk_df.columns else []

    if not week_df.empty:
        train = week_df[week_df["session_type"] == "Edzés"] if "session_type" in week_df.columns else pd.DataFrame()
        match = week_df[week_df["session_type"] == "Meccs"] if "session_type" in week_df.columns else pd.DataFrame()
        if not train.empty and not match.empty:
            if "sprint_distance" in week_df.columns and match["sprint_distance"].mean() > 0:
                low_sprint = (train["sprint_distance"].mean() / match["sprint_distance"].mean()) < 0.75
            if "distance_per_min" in week_df.columns and match["distance_per_min"].mean() > 0:
                intensity_gap = (train["distance_per_min"].mean() / match["distance_per_min"].mean()) < 0.88
        elif not train.empty:
            if "sprint_distance" in train.columns and train["sprint_distance"].mean() < 250:
                low_sprint = True

    if readiness_score < 60:
        global_tone = "frissítés és terheléskontroll"
        volume = "alacsony-közepes"
    elif "alulterhelt" in str(periodization_type).lower() or low_sprint:
        global_tone = "kontrollált inger pótlása"
        volume = "közepes"
    else:
        global_tone = "struktúra megtartása és finomhangolás"
        volume = "közepes"

    md_structure = [
        ("MD-4", "Fő terhelési nap", "volumen + játékmodell-specifikus intenzitás"),
        ("MD-3", "Sebesség / intenzitás nap", "rövid maximális sebesség vagy high effort blokk"),
        ("MD-2", "Kontrollált taktikai nap", "alacsonyabb neuromuszkuláris teher, kevesebb lassítás"),
        ("MD-1", "Aktiváció", "rövid, frissítő, nem fárasztó inger"),
        ("MD", "Mérkőzés", "referencianap"),
        ("MD+1", "Regeneráció / pótlás", "játszók regeneráció, kevesebbet játszók kiegészítő munka"),
    ]

    rows = []
    for md, role, base_goal in md_structure:
        if md == "MD-4":
            recommendation = "Legyen ez a hét fő terhelési napja. Játékmodellhez illeszkedő játékok, nagyobb volumen."
            if readiness_score < 60:
                recommendation = "Csak óvatos fő nap: ne legyen nagy load spike, inkább kontrollált volumen."
        elif md == "MD-3":
            if low_sprint:
                recommendation = "Tegyél be rövid, kontrollált sprint/max sebesség blokkot. Kevés ismétlés, jó minőség."
            elif intensity_gap:
                recommendation = "Rövidebb, magasabb tempójú játékokkal közelítsd a meccsintenzitást."
            else:
                recommendation = "Tartsd meg a minőségi sebesség/intenzitás ingert, de ne volumenből oldd meg."
        elif md == "MD-2":
            recommendation = "Taktikai fókusz, kontrollált terhelés. Kerüld a túl sok lassítást és excentrikus terhet."
            if high_risk_players:
                recommendation += " Magas risk játékosoknál egyéni limit javasolt."
        elif md == "MD-1":
            recommendation = "Rövid aktiváció, frissesség megtartása. Ne legyen új terhelési inger."
        elif md == "MD":
            recommendation = "Mérkőzés referencia. A következő heti edzésterhelést ehhez viszonyítsd."
        else:
            recommendation = "Regeneráció a sokat játszóknak, kiegészítő kontrollált terhelés a kevesebbet játszóknak."

        rows.append({
            "Nap": md,
            "Szerep": role,
            "Fő cél": base_goal,
            "Ajánlott terhelés": volume if md in ["MD-4", "MD-3"] else "alacsony-közepes" if md in ["MD-2", "MD+1"] else "alacsony" if md == "MD-1" else "meccs",
            "Javaslat": recommendation,
            "Tervezési alap": f"A jelenlegi hét értelmezése: {global_tone}. Readiness: {readiness_score}/100, periodizáció: {periodization_type}.",
        })

    return pd.DataFrame(rows)


def build_player_next_actions(player_risk_df: pd.DataFrame, df: pd.DataFrame, selected_week: str) -> pd.DataFrame:
    """Játékosszintű holnapi/következő heti teendők."""
    if player_risk_df is None or player_risk_df.empty:
        return pd.DataFrame(columns=["Játékos", "Prioritás", "Holnap / következő edzés", "Következő hét", "Indok"])

    rows = []
    for _, r in player_risk_df.head(12).iterrows():
        name = r.get("Játékos", r.get("player_name", ""))
        level = str(r.get("Kockázati szint", ""))
        score = r.get("Kockázati pontszám", r.get("Risk score", ""))
        reason = r.get("Fő okok", r.get("Fő ok", ""))

        if level == "Magas":
            tomorrow = "Terheléskontroll, extra sprint/lassítás kerülése, frissességi check-in."
            next_week = "Egyéni limit MD-4/MD-3 napon; minőségi, de alacsony volumenű sebességinger."
            priority = "Magas"
        elif level == "Közepes":
            tomorrow = "Normál edzés, de sprint/lassítás mennyiség figyelése."
            next_week = "Fokozatos terhelés, ne legyen hirtelen load spike."
            priority = "Közepes"
        else:
            tomorrow = "Normál terhelés folytatható."
            next_week = "Csapatprogram szerint, egyéni monitoringgal."
            priority = "Alacsony"

        rows.append({
            "Játékos": name,
            "Prioritás": priority,
            "Holnap / következő edzés": tomorrow,
            "Következő hét": next_week,
            "Indok": f"Risk: {score}. {reason}",
        })

    return pd.DataFrame(rows)


def build_next_week_plan_v5(
    df: pd.DataFrame,
    selected_week: str,
    playstyle: str,
    readiness_score: int,
    periodization_type: str,
    player_risk_df: pd.DataFrame,
    past_review_df: pd.DataFrame,
    current_remaining_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, str]:
    """Jövő hét: múlt hét + aktuális részadat + risk alapján."""
    base_plan = build_next_microcycle_plan(df, selected_week, playstyle, readiness_score, periodization_type, player_risk_df)
    if base_plan is None or base_plan.empty:
        return base_plan, "Nincs elég adat következő hét tervhez."

    high_risk_count = 0
    if player_risk_df is not None and not player_risk_df.empty and "Kockázati szint" in player_risk_df.columns:
        high_risk_count = int((player_risk_df["Kockázati szint"] == "Magas").sum())

    past_warn = 0
    if past_review_df is not None and not past_review_df.empty and "Súlyosság" in past_review_df.columns:
        past_warn = int(past_review_df["Súlyosság"].astype(str).isin(["KRITIKUS", "FIGYELMEZTETÉS"]).sum())

    base_plan = base_plan.copy()
    base_plan["Tervezési alap"] = (
        f"Múlt heti figyelmeztetések: {past_warn}; aktuális readiness: {readiness_score}/100; "
        f"magas risk játékosok: {high_risk_count}; periodizáció: {periodization_type}."
    )

    txt = (
        "A jövő heti mikrociklus a múlt teljesebb értékelésére, az aktuális hét eddig feltöltött napjaira "
        "és a játékosszintű risk jelzésekre épül."
    )
    return base_plan, txt


def build_premium_pdf_bytes(
    insights_df: pd.DataFrame,
    selected_week: str,
    readiness_score: int,
    periodization_type: str,
    weekly_summary_text: str,
    coaching_priorities: List[Dict[str, str]],
    risk_df: pd.DataFrame,
    playstyle: str
) -> Optional[bytes]:
    """Éles, látványos Pro PDF riport valós feltöltött adatokból.
    A minta PDF vizuális és tartalmi logikáját követi.
    """
    if SimpleDocTemplate is None:
        return None

    try:
        from reportlab.platypus import PageBreak
    except Exception:
        PageBreak = None

    font_name, font_bold = _register_pdf_font()
    output = io.BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=0.7 * cm,
        leftMargin=0.7 * cm,
        topMargin=0.65 * cm,
        bottomMargin=0.65 * cm,
    )

    styles = getSampleStyleSheet()

    title = ParagraphStyle(
        "LiveReportTitle",
        parent=styles["Title"],
        fontName=font_bold,
        fontSize=23,
        leading=27,
        alignment=1,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=5,
    )
    subtitle = ParagraphStyle(
        "LiveReportSubtitle",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#475569"),
        spaceAfter=8,
    )
    h2 = ParagraphStyle(
        "LiveReportH2",
        parent=styles["Heading2"],
        fontName=font_bold,
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#1F4E78"),
        spaceBefore=7,
        spaceAfter=5,
    )
    body = ParagraphStyle(
        "LiveReportBody",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=8.2,
        leading=10.5,
        textColor=colors.HexColor("#111827"),
    )
    small = ParagraphStyle(
        "LiveReportSmall",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=7.1,
        leading=9,
        textColor=colors.HexColor("#111827"),
    )
    tiny = ParagraphStyle(
        "LiveReportTiny",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=6.5,
        leading=8.2,
        textColor=colors.HexColor("#111827"),
    )
    header = ParagraphStyle(
        "LiveReportHeader",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=7.2,
        leading=9,
        alignment=1,
        textColor=colors.white,
    )
    kpi_label = ParagraphStyle(
        "KpiLabel",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=7.2,
        leading=9,
        alignment=1,
        textColor=colors.white,
    )
    kpi_value = ParagraphStyle(
        "KpiValue",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=17,
        leading=20,
        alignment=1,
        textColor=colors.white,
    )
    kpi_note = ParagraphStyle(
        "KpiNote",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=7,
        leading=8.5,
        alignment=1,
        textColor=colors.white,
    )

    def clean_text(v: object) -> str:
        txt = pdf_safe_text(v)
        txt = str(txt or "")
        txt = txt.replace("\\r", "").replace("\\n", "\n")
        return txt

    def P(v, style=body):
        return Paragraph(html.escape(clean_text(v)).replace("\n", "<br/>"), style)

    def section_bar(text: str):
        t = Table([[P(text, h2)]], colWidths=[27.7 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#DFF2FF")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#93C5FD")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    def data_table(data, col_widths, header_bg="#0F172A", row_bgs=None):
        if row_bgs is None:
            row_bgs = [colors.white, colors.HexColor("#F8FAFC")]
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), row_bgs),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    def severity_count(label: str) -> int:
        if insights_df is None or insights_df.empty or "Súlyosság" not in insights_df.columns:
            return 0
        return int((insights_df["Súlyosság"].astype(str).str.upper() == label).sum())

    high_risk_count = 0
    medium_risk_count = 0
    if risk_df is not None and not risk_df.empty and "Kockázati szint" in risk_df.columns:
        high_risk_count = int((risk_df["Kockázati szint"].astype(str).str.lower() == "magas").sum())
        medium_risk_count = int((risk_df["Kockázati szint"].astype(str).str.lower() == "közepes").sum())

    critical_count = severity_count("KRITIKUS")
    warning_count = severity_count("FIGYELMEZTETÉS")
    insight_count = len(insights_df) if insights_df is not None else 0

    sprint_fit = "—"
    load_change = "—"
    try:
        full_text = " ".join(insights_df.astype(str).values.flatten().tolist()) if insights_df is not None and not insights_df.empty else ""
        m = re.search(r"kb\.\s*(\d+)%", full_text)
        if m:
            sprint_fit = f"{m.group(1)}%"
        m2 = re.search(r"(\d+)%[-–]kal nőtt", full_text)
        if m2:
            load_change = f"+{m2.group(1)}%"
    except Exception:
        pass

    readiness_label = score_to_label(readiness_score)
    top_risk_label = f"{high_risk_count} fő" if high_risk_count else "OK"

    story = []
    story.append(P("Football Performance Intelligence", title))
    story.append(P(
        f"Éles vezetői riport | Hét: {format_week_label(selected_week)} | Játékmodell: {playstyle} | Generálva: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        subtitle,
    ))

    # KPI strip
    kpis = [
        ("TEAM READINESS", f"{readiness_score}/100", readiness_label, "#166534" if readiness_score >= 75 else "#1E3A8A" if readiness_score >= 60 else "#991B1B"),
        ("LOAD CHANGE", load_change, "heti terhelési jel", "#8B2C13"),
        ("SPRINT FIT", sprint_fit, "edzés vs meccsigény", "#1E3A8A"),
        ("TOP RISK", top_risk_label, "magas egyéni kockázat", "#7F1D1D" if high_risk_count else "#166534"),
        ("INSIGHT", str(insight_count), "automatikus megállapítás", "#0F172A"),
    ]

    kpi_tables = []
    for label, value, note, color in kpis:
        kt = Table(
            [[P(label, kpi_label)], [P(value, kpi_value)], [P(note, kpi_note)]],
            colWidths=[5.1 * cm],
            rowHeights=[0.55 * cm, 0.9 * cm, 0.55 * cm],
        )
        kt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(color)),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.white),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        kpi_tables.append(kt)

    strip = Table([kpi_tables], colWidths=[5.25 * cm] * 5)
    strip.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [strip, Spacer(1, 0.28 * cm)]

    # Executive summary
    story.append(section_bar("Vezetői összefoglaló – mit kell tudni 30 másodperc alatt?"))

    summary_clean = clean_text(weekly_summary_text)
    summary_lines = [x.strip().lstrip("-• ").strip() for x in summary_clean.splitlines() if x.strip()]
    main_msg = ""
    observation = ""
    recommendation = ""
    second_topic = ""
    for line in summary_lines:
        if line.startswith("Legfontosabb üzenet:"):
            main_msg = line.replace("Legfontosabb üzenet:", "").strip()
        elif line.startswith("Mit látunk?"):
            observation = line.replace("Mit látunk?", "").strip()
        elif line.startswith("Javaslat:"):
            recommendation = line.replace("Javaslat:", "").strip()
        elif line.startswith("Második fontos téma:"):
            second_topic = line.replace("Második fontos téma:", "").strip()

    if not main_msg and summary_lines:
        main_msg = summary_lines[0]
    if not observation:
        observation = "A heti adatok alapján több automatikus performance jelzés készült."
    if not recommendation:
        recommendation = "A következő edzés tervezésénél a readiness, a sprintinger és az egyéni risk jelzések együtt értelmezendők."
    if not second_topic:
        second_topic = "Egyéni és mikrociklus kontroll"

    exec_data = [
        [P("Fő üzenet", header), P("Értelmezés", header), P("Azonnali döntés", header)],
        [
            P(main_msg, body),
            P(f"{observation}\nMeccskészültség: {readiness_score}/100 ({readiness_label}). Periodizáció: {periodization_type}.", body),
            P(recommendation, body),
        ],
        [
            P(second_topic, body),
            P(f"Magas risk: {high_risk_count} fő, közepes risk: {medium_risk_count} fő. Insightok száma: {insight_count}.", body),
            P("A top edzői teendőket és játékos risk sort érdemes stábértekezleten külön átvenni.", body),
        ],
    ]
    story.append(data_table(exec_data, [5.9 * cm, 9.9 * cm, 11.9 * cm], header_bg="#1E3A8A", row_bgs=[colors.HexColor("#F8FAFC"), colors.HexColor("#EFF6FF")]))
    story += [Spacer(1, 0.25 * cm)]

    # Top insights
    story.append(section_bar("Top automatikus megállapítások"))
    insight_cols = ["Megállapítás", "Súlyosság", "Mit látunk?", "Javaslat"]
    insight_cols = [c for c in insight_cols if insights_df is not None and c in insights_df.columns]
    top_data = [[P("#", header)] + [P(c, header) for c in insight_cols]]
    if insights_df is not None and not insights_df.empty and insight_cols:
        for i, (_, r) in enumerate(insights_df.head(6).iterrows(), 1):
            top_data.append([P(str(i), small)] + [P(r.get(c, ""), small) for c in insight_cols])
    else:
        top_data.append([P("1", small), P("Nincs kiemelt megállapítás", small), P("INFORMÁCIÓ", small), P("A feltöltött adatok alapján nincs kritikus jelzés.", small), P("Normál monitoring folytatható.", small)])

    widths = [0.8 * cm, 5.3 * cm, 3.0 * cm, 10.0 * cm, 8.6 * cm][:len(top_data[0])]
    story.append(data_table(top_data, widths, header_bg="#0F172A"))

    if PageBreak:
        story.append(PageBreak())
    else:
        story.append(Spacer(1, 1 * cm))

    # PAGE 2
    story.append(P("Edzői döntéstámogatás", title))
    story.append(P("Prioritások, játékos risk és gyakorlati javaslatok valós feltöltött adatok alapján.", subtitle))
    story.append(section_bar("Top edzői teendők"))

    pr_data = [[P("Prioritás", header), P("Teendő", header), P("Miért fontos?", header), P("Mikor?", header)]]
    if coaching_priorities:
        for i, item in enumerate(coaching_priorities[:6], 1):
            pr_data.append([
                P(str(i), small),
                P(item.get("Teendő", item.get("Cím", "")), small),
                P(item.get("Miért", ""), small),
                P(item.get("Mikor", "Következő edzés / heti review"), small),
            ])
    else:
        pr_data.append([P("1", small), P("Normál monitoring", small), P("Nincs kiemelt edzői beavatkozás.", small), P("Heti review", small)])

    story.append(data_table(pr_data, [1.8 * cm, 10.0 * cm, 10.0 * cm, 5.9 * cm], header_bg="#166534", row_bgs=[colors.HexColor("#ECFDF5"), colors.HexColor("#F8FAFC")]))
    story += [Spacer(1, 0.25 * cm)]

    story.append(section_bar("Játékos risk tábla – vezetői gyorsnézet"))
    risk_cols = ["Játékos", "Kockázati szint", "Kockázati pontszám", "Fő okok"]
    risk_cols = [c for c in risk_cols if risk_df is not None and c in risk_df.columns]
    risk_data = [[P(c, header) for c in risk_cols]]
    if risk_df is not None and not risk_df.empty and risk_cols:
        for _, r in risk_df.head(10).iterrows():
            risk_data.append([P(r.get(c, ""), small) for c in risk_cols])
    else:
        risk_cols = ["Játékos", "Kockázati szint", "Kockázati pontszám", "Fő okok"]
        risk_data = [[P(c, header) for c in risk_cols]]
        risk_data.append([P("Nincs magas risk", small), P("Alacsony", small), P("—", small), P("A feltöltött hét alapján nincs kiemelt egyéni kockázat.", small)])

    risk_widths = {
        "Játékos": 4.7 * cm,
        "Kockázati szint": 3.0 * cm,
        "Kockázati pontszám": 3.0 * cm,
        "Fő okok": 17.0 * cm,
    }
    story.append(data_table(risk_data, [risk_widths.get(c, 4 * cm) for c in risk_cols], header_bg="#7F1D1D", row_bgs=[colors.white, colors.HexColor("#FFF7ED")]))

    if PageBreak:
        story.append(PageBreak())
    else:
        story.append(Spacer(1, 1 * cm))

    # PAGE 3
    story.append(P("Mikrociklus és játékmodell illeszkedés", title))
    story.append(P("A riport nem csak adatot mutat, hanem edzői döntésre fordítja le a GPS-profilt.", subtitle))
    story.append(section_bar("Mikrociklus szerkezet – automatikus értelmezés"))

    micro_rows = [
        ["Komponens", "Aktuális jel", "Értékelés"],
        ["Readiness", f"{readiness_score}/100", readiness_label],
        ["Periodizáció", periodization_type, "A heti load és frissességi jelzések alapján."],
        ["Sprint fit", sprint_fit, "A meccsigényhez viszonyított sprintinger becsült jele."],
        ["Magas risk", f"{high_risk_count} fő", "Egyéni kontroll szükséges, ha 1 főnél több magas risk van."],
        ["Insight súlyosság", f"{critical_count} kritikus / {warning_count} figyelmeztetés", "A heti fő fókusz a kritikus és figyelmeztető jelzésekből jön."],
    ]
    story.append(data_table([[P(c, header) for c in micro_rows[0]]] + [[P(c, small) for c in row] for row in micro_rows[1:]], [5.8 * cm, 6.8 * cm, 15.1 * cm], header_bg="#1E3A8A", row_bgs=[colors.HexColor("#EFF6FF"), colors.white]))
    story += [Spacer(1, 0.25 * cm)]

    story.append(section_bar(f"Játékmodell illeszkedés – {playstyle} profil"))

    if str(playstyle).lower() == "pressing":
        components = [
            ["Táv/perc", "Meccsprofil 90%+", "Ellenőrizendő", "Pressing modellhez magas munkasűrűség kell."],
            ["High effort", "Meccsprofil 75%+", "Ellenőrizendő", "Ismételt intenzív akciók kulcsfontosságúak."],
            ["Sprintprofil", "Meccsprofil 80%+", sprint_fit, "Célzott sprintinger javasolt, ha alacsony."],
            ["Lassítási terhelés", "Kontrollált", "Risk alapján", "Excentrikus/regenerációs kockázatot jelezhet."],
        ]
    else:
        components = [
            ["Táv/perc", "Játékmodellhez illeszkedő", "Ellenőrizendő", "A heti tempó illeszkedjen a meccsigényhez."],
            ["Sprintprofil", "Meccsprofilhoz közeli", sprint_fit, "A gyors munka ne maradjon tartósan alacsony."],
            ["Load kontroll", "Ne legyen nagy kiugrás", load_change, "A hirtelen terhelésemelkedés readiness kockázatot adhat."],
            ["Játékos risk", "Egyéni eltérések kontrollja", top_risk_label, "A csapatátlag elfedhet egyéni problémákat."],
        ]

    jd = [[P("Komponens", header), P("Cél", header), P("Aktuális hét", header), P("Értékelés", header)]]
    for row in components:
        jd.append([P(c, small) for c in row])

    story.append(data_table(jd, [5.4 * cm, 6.2 * cm, 4.6 * cm, 11.5 * cm], header_bg="#312E81", row_bgs=[colors.white, colors.HexColor("#F5F3FF")]))
    story += [Spacer(1, 0.25 * cm)]

    story.append(section_bar("Vizuális gyorsjelentés – vezetői dashboard nézet"))
    dash_kpis = [
        ("READINESS", f"{readiness_score}%", "meccskészültség", "#166534" if readiness_score >= 75 else "#1E3A8A"),
        ("SPRINT FIT", sprint_fit, "sebességkitettség", "#1E3A8A"),
        ("LOAD", load_change, "heti terhelésjel", "#8B2C13"),
        ("PLAYER RISK", top_risk_label, "egyéni kontroll", "#7F1D1D" if high_risk_count else "#166534"),
        ("COACHING", f"{len(coaching_priorities[:6])} task", "automatikus teendő", "#0F172A"),
    ]

    mini_tables = []
    for label, val, note, color in dash_kpis:
        mt = Table(
            [[P(label, kpi_label)], [P(val, kpi_value)], [P(note, kpi_note)]],
            colWidths=[5.1 * cm],
            rowHeights=[0.5 * cm, 0.8 * cm, 0.5 * cm],
        )
        mt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(color)),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.white),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        mini_tables.append(mt)
    story.append(Table([mini_tables], colWidths=[5.25 * cm] * 5))

    if PageBreak:
        story.append(PageBreak())
    else:
        story.append(Spacer(1, 1 * cm))

    # PAGE 4
    story.append(P("Teljes Pro riport – részletes insight tábla", title))
    story.append(P("A Pro export célja, hogy a vezetői összkép mellett a szakmai stáb részletes megállapításokat is megkapjon.", subtitle))
    story.append(section_bar("Mit kap ebből a stáb?"))

    pro_rows = [
        ["Modul", "Mit ad?", "Kinek hasznos?"],
        ["Vezetői riport", "30 másodperces összefoglaló, readiness, top risk, top teendő.", "sportigazgató, vezetőedző"],
        ["Mikrociklus", "MD-logika, tapering, sprintinger, frissességi jelzések.", "vezetőedző, erőnléti edző"],
        ["Játékos risk motor", "Egyéni terhelési eltérések, sprint, lassítás, load kiugrás.", "erőnléti edző, rehabilitáció"],
        ["Játékmodell illeszkedés", "Fizikai profil összevetése a választott játékmodellel.", "szakmai stáb"],
        ["Export központ", "PDF, Word, Excel riportok vezetői és szakmai felhasználásra.", "klubvezetés, stáb"],
    ]

    story.append(data_table([[P(c, header) for c in pro_rows[0]]] + [[P(c, small) for c in row] for row in pro_rows[1:]], [5.0 * cm, 14.5 * cm, 8.2 * cm], header_bg="#0F172A", row_bgs=[colors.white, colors.HexColor("#F8FAFC")]))
    story += [Spacer(1, 0.25 * cm)]

    story.append(section_bar("Részletes insight tábla"))
    if insights_df is not None and not insights_df.empty:
        detail_cols = ["Súlyosság", "Terület", "Megállapítás", "Mit látunk?", "Javaslat"]
        detail_cols = [c for c in detail_cols if c in insights_df.columns]
        detail_data = [[P(c, header) for c in detail_cols]]
        for _, r in insights_df.head(12).iterrows():
            detail_data.append([P(r.get(c, ""), tiny) for c in detail_cols])
        detail_widths = {
            "Súlyosság": 3.2 * cm,
            "Terület": 2.4 * cm,
            "Megállapítás": 4.8 * cm,
            "Mit látunk?": 8.6 * cm,
            "Javaslat": 8.7 * cm,
        }
        story.append(data_table(detail_data, [detail_widths.get(c, 4 * cm) for c in detail_cols], header_bg="#1F4E78", row_bgs=[colors.white, colors.HexColor("#F7F9FC")]))
    else:
        story.append(P("Nincs részletes insight adat.", body))

    doc.build(story)
    output.seek(0)
    return output.getvalue()


# -----------------------------------------------------------------------------
# V3.1 - Magyar demo oldal + Executive Export Center
# -----------------------------------------------------------------------------
def render_system_intro_page() -> None:
    st.markdown(
        """
        <div class="intro-card">
            <h2>⚽ Football Performance Intelligence Platform</h2>
            <div class="hero-sub">
                Automatikus heti teljesítményintelligencia futballcsapatok számára.
                Ez nem egyszerű GPS dashboard, hanem egy döntéstámogató performance engine,
                amely football kontextusban értelmezi a terhelési adatokat.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Mit csinálunk?")
    st.markdown(
        """
        A rendszer a feltöltött GPS / terhelési adatokat automatikusan feldolgozza, majd
        edzői nyelvre fordítja: kiemeli a legfontosabb heti megállapításokat,
        figyelmeztet a problémás mintázatokra, és javaslatokat ad a következő döntésekhez.
        """
    )

    st.markdown("### Mitől extra?")
    st.markdown(
        """
        Nem csak számokat és grafikonokat mutat. A rendszer figyelembe veszi a mikrociklust,
        a meccsnaphoz viszonyított terhelést, a játékmodellt, a többhetes mintázatokat,
        a játékosok egyéni eltéréseit és a match readiness állapotot.
        """
    )

    st.markdown(
        """
        <div class="intro-grid">
            <div class="feature-box">
                <div class="feature-title">1. Mikrociklus intelligencia</div>
                <div class="feature-text">MD-4 / MD-3 / MD-2 / MD-1 logika, tapering, maximális sebességű inger és heti struktúra értékelése.</div>
            </div>
            <div class="feature-box">
                <div class="feature-title">2. Meccskészültség score</div>
                <div class="feature-text">0–100-as meccskészültségi pontszám load trend, frissesség, maximális sebességű inger és játékmodell alapján.</div>
            </div>
            <div class="feature-box">
                <div class="feature-title">3. Játékos kockázati motor</div>
                <div class="feature-text">Automatikusan jelzi, ha egy játékos terhelése, sprintprofilja vagy max sebessége eltér a saját múltjától.</div>
            </div>
            <div class="feature-box">
                <div class="feature-title">4. Performance memória</div>
                <div class="feature-text">Többhetes történetet épít, trendeket keres, és nem csak az aktuális hetet nézi elszigetelten.</div>
            </div>
            <div class="feature-box">
                <div class="feature-title">5. Coaching priorities</div>
                <div class="feature-text">Nem 40 figyelmeztetést ad, hanem kiemeli a hét 3 legfontosabb edzői teendőjét.</div>
            </div>
            <div class="feature-box">
                <div class="feature-title">6. Executive export</div>
                <div class="feature-text">Egy kattintással vezetőedzői PDF / Word / Excel riport készül magyar nyelven.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Kinek készült?")
    st.markdown(
        """
        Elsősorban NB2 / NB3 kluboknak, akadémiáknak, utánpótlás elitműhelyeknek
        és olyan stáboknak, ahol van GPS adat, de nincs külön analyst vagy sport scientist csapat.
        """
    )

    st.markdown("### Egy mondatban")
    st.success("A rendszer analyst gondolkodást ad a stábnak, de nem kell hozzá külön analyst csapat.")

    st.markdown("### Egyszerű nyelven a fő fogalmak")
    render_wrapped_table(build_plain_language_explanation())


def build_executive_summary_df(
    selected_week: str,
    selected_playstyle: str,
    readiness_score: int,
    periodization_type: str,
    weekly_summary_text: str,
    high_risk_count: int,
    medium_risk_count: int,
) -> pd.DataFrame:
    return pd.DataFrame([
        {"Elem": "Hét", "Érték": selected_week},
        {"Elem": "Játékmodell", "Érték": selected_playstyle},
        {"Elem": "Meccskészültség", "Érték": f"{readiness_score}/100 – {score_to_label(readiness_score)}"},
        {"Elem": "Periodizáció", "Érték": periodization_type},
        {"Elem": "Magas kockázatos játékosok", "Érték": str(high_risk_count)},
        {"Elem": "Közepes kockázatos játékosok", "Érték": str(medium_risk_count)},
        {"Elem": "Heti vezetői összefoglaló", "Érték": weekly_summary_text},
    ])


def build_executive_excel_bytes(
    executive_df: pd.DataFrame,
    insights_df: pd.DataFrame,
    priorities_df: pd.DataFrame,
    risk_df: pd.DataFrame,
    weekly_fingerprints: pd.DataFrame,
) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        executive_df.to_excel(writer, index=False, sheet_name="Vezetői összefoglaló")
        insights_df.to_excel(writer, index=False, sheet_name="Insightok")
        priorities_df.to_excel(writer, index=False, sheet_name="Edzői teendők")
        if risk_df is not None and not risk_df.empty:
            risk_df.to_excel(writer, index=False, sheet_name="Játékos risk")
        if weekly_fingerprints is not None and not weekly_fingerprints.empty:
            weekly_fingerprints.to_excel(writer, index=False, sheet_name="Memory trendek")

        from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
        from openpyxl.utils import get_column_letter

        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            header_fill = PatternFill("solid", fgColor="0F172A")
            header_font = Font(color="FFFFFF", bold=True)
            thin = Side(style="thin", color="CBD5E1")
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)

            for row in ws.iter_rows(min_row=2):
                max_lines = 1
                for cell in row:
                    cell.alignment = Alignment(vertical="top", wrap_text=True)
                    cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
                    text = str(cell.value or "")
                    max_lines = max(max_lines, min(8, len(text) // 45 + 1))
                ws.row_dimensions[row[0].row].height = max(24, max_lines * 16)

            for idx, col_cells in enumerate(ws.columns, start=1):
                values = [str(c.value or "") for c in col_cells[:80]]
                width = min(68, max(14, max(len(v) for v in values[:80]) + 2))
                if ws.title in ["Insightok", "Edzői teendők"]:
                    width = min(60, max(width, 28))
                ws.column_dimensions[get_column_letter(idx)].width = width

    return output.getvalue()


def build_executive_word_bytes(
    executive_df: pd.DataFrame,
    priorities_df: pd.DataFrame,
    insights_df: pd.DataFrame,
    risk_df: pd.DataFrame,
    selected_week: str,
) -> Optional[bytes]:
    if Document is None:
        return None
    doc = Document()
    section = doc.sections[0]
    section.left_margin = Inches(0.6)
    section.right_margin = Inches(0.6)
    section.top_margin = Inches(0.6)
    section.bottom_margin = Inches(0.6)

    doc.add_heading("Football Performance Intelligence – vezetői riport", level=1)
    doc.add_paragraph(f"Hét: {selected_week}")
    doc.add_paragraph(f"Generálva: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    doc.add_heading("Vezetői összefoglaló", level=2)
    for _, row in executive_df.iterrows():
        p = doc.add_paragraph()
        p.add_run(f"{row.get('Elem', '')}: ").bold = True
        p.add_run(str(row.get("Érték", "")))

    doc.add_heading("Top edzői teendők", level=2)
    for idx, row in priorities_df.iterrows():
        doc.add_heading(f"{idx + 1}. {row.get('Cím', '')}", level=3)
        p = doc.add_paragraph()
        p.add_run("Teendő: ").bold = True
        p.add_run(str(row.get("Teendő", "")))
        p = doc.add_paragraph()
        p.add_run("Miért fontos: ").bold = True
        p.add_run(str(row.get("Miért", "")))

    if risk_df is not None and not risk_df.empty:
        doc.add_heading("Top játékos kockázat", level=2)
        for _, row in risk_df.head(8).iterrows():
            p = doc.add_paragraph()
            p.add_run(f"{row.get('Játékos', '')} – {row.get('Kockázati szint', '')} ({row.get('Kockázati pontszám', '')}/100): ").bold = True
            p.add_run(str(row.get("Fő okok", "")))

    doc.add_heading("Insightok", level=2)
    for _, row in insights_df.iterrows():
        doc.add_heading(str(row.get("Megállapítás", "")), level=3)
        for label in ["Súlyosság", "Terület", "Mit látunk?", "Miért fontos?", "Javaslat"]:
            if label in insights_df.columns:
                p = doc.add_paragraph()
                p.add_run(f"{label}: ").bold = True
                p.add_run(str(row.get(label, "")))

    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()



# -----------------------------------------------------------------------------
# V3.2 - Magyar, edzői nyelvű kommunikációs réteg
# -----------------------------------------------------------------------------
def coach_friendly_phrase(text: object) -> str:
    """Analyst-jellegű megfogalmazásokat fordít edzőbarát magyar nyelvre."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    s = str(text)

    replacements = {
        "A következő 1–2 edzésen ne a plusz terhelés legyen a fő cél, hanem a frissesség stabil megtartása.": 
            "A következő 1–2 edzésen ne a plusz terhelés legyen a fő cél, hanem a frissesség stabil megtartása. Ha hiányzik valamilyen inger, azt röviden és célzottan érdemes pótolni.",
        "A csapat nincs rossz állapotban, de nem is tűnik teljesen frissnek. Ilyenkor a túl nagy változtatás visszaüthet.": 
            "A csapat nincs rossz állapotban, de nem is tűnik teljesen frissnek. Ilyenkor a túl nagy változtatás könnyen visszaüthet.",
        "Tisztázd, hogy ez szándékosan könnyebb hét volt-e. Ha igen, rendben lehet; ha nem, akkor hiányozhatott a megfelelő edzésinger.": 
            "Érdemes tisztázni, hogy ez a hét szándékosan volt-e könnyebb. Ha igen, rendben lehet; ha nem, akkor hiányozhatott a megfelelő edzésinger.",
        "Az alacsonyabb terhelés rövid távon frissíthet, de ha több héten át így marad, a csapat intenzitása visszaeshet.": 
            "Az alacsonyabb terhelés rövid távon frissíthet, de ha több héten át így marad, a csapat intenzitása visszaeshet.",
        "Érdemes célzottan megvizsgálni, hogy tudatos terheléscsökkentésről vagy nem kívánt intenzitáshiányról van-e szó.": 
            "Nézd meg, hogy szándékosan csökkent-e a gyors munka. Ha nem, akkor érdemes visszatenni egy rövid, kontrollált maximális sebességű blokkot.",
        "A tartós speed exposure hiány hosszabb távon ronthatja a maximális sebesség és intenzitás fenntartását.": 
            "Ha hetekig kevés a maximális sebességű inger, a játékosok nehezebben tudják fenntartani a meccshez szükséges gyorsaságot és intenzitást.",
        "Meccskészültség kontroll": "Meccskészültség kontroll",
        "Könnyebb hét értelmezése": "Könnyebb hét értelmezése",
        "Többhetes sprintcsökkenés": "Több hete csökken a gyors munka",
        "speed exposure": "maximális sebességű inger",
        "Speed exposure": "Maximális sebességű inger",
        "load": "terhelés",
        "Load": "Terhelés",
        "readiness": "meccskészültség",
        "Readiness": "Meccskészültség",
        "risk": "kockázat",
        "Risk": "Kockázat",
        "player": "játékos",
        "Player": "Játékos",
        "overload": "túlterhelés",
        "Overload": "Túlterhelés",
        "recovery": "regeneráció",
        "Recovery": "Regeneráció",
    }

    for old, new in replacements.items():
        s = s.replace(old, new)

    return s


def humanize_insight(insight: Insight) -> Insight:
    """Insight objektum edzőbarát magyarítása."""
    return Insight(
        title=coach_friendly_phrase(insight.title),
        severity=insight.severity,
        observation=coach_friendly_phrase(insight.observation),
        impact=coach_friendly_phrase(insight.impact),
        recommendation=coach_friendly_phrase(insight.recommendation),
        scope=coach_friendly_phrase(insight.scope),
    )


def humanize_insights(insights: List[Insight]) -> List[Insight]:
    return [humanize_insight(i) for i in insights]


def humanize_priority_item(item: Dict[str, str]) -> Dict[str, str]:
    return {k: coach_friendly_phrase(v) for k, v in item.items()}


def humanize_priority_list(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [humanize_priority_item(i) for i in items]


def build_plain_language_explanation() -> pd.DataFrame:
    """Rövid magyarázó tábla a vezetőedzőnek: mit jelent egy-egy fogalom."""
    return pd.DataFrame([
        {
            "Fogalom": "Meccskészültség",
            "Egyszerű jelentés": "Mennyire tűnik késznek a csapat a következő meccsterhelésre.",
            "Mit nézünk?": "Terhelési trend, frissesség, MD-1/MD-2 terhelés, sprintinger, játékmodellhez való illeszkedés.",
        },
        {
            "Fogalom": "Könnyebb hét",
            "Egyszerű jelentés": "A hét terhelése alacsonyabb volt a megszokottnál.",
            "Mit nézünk?": "Ez lehet tudatos frissítés, de lehet nem kívánt alulterhelés is.",
        },
        {
            "Fogalom": "Maximális sebességű inger",
            "Egyszerű jelentés": "Kapott-e a csapat/játékos elég nagy sebességű futást a héten.",
            "Mit nézünk?": "Sprinttáv, max sebesség, meccsigényhez viszonyított arány.",
        },
        {
            "Fogalom": "Többhetes sprintcsökkenés",
            "Egyszerű jelentés": "Hetek óta csökken a gyors futások mennyisége.",
            "Mit nézünk?": "Sprinttáv trend, nagy sebességű táv, maximális sebesség.",
        },
        {
            "Fogalom": "Játékos kockázat",
            "Egyszerű jelentés": "Egy játékos mennyire tér el a saját megszokott terhelési profiljától.",
            "Mit nézünk?": "Terhelési ugrás, lassítások, sprinttáv, max sebesség-visszaesés.",
        },
    ])





# -----------------------------------------------------------------------------
# Marketing / demo minta PDF riport - V4.2
# -----------------------------------------------------------------------------
def build_marketing_sample_pdf_bytes() -> Optional[bytes]:
    """Látványos, többoldalas, kamu adatokkal készült teljes vezetői riport.
    Nem függ feltöltött adattól, ezért a kezdőoldalon is letölthető.
    """
    if SimpleDocTemplate is None:
        return None

    from reportlab.platypus import PageBreak, KeepTogether
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    font_name, font_bold = _register_pdf_font()
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=.85*cm,
        leftMargin=.85*cm,
        topMargin=.75*cm,
        bottomMargin=.75*cm,
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle("FPITitle", parent=styles["Title"], fontName=font_bold, fontSize=23, leading=27, textColor=colors.HexColor("#0f172a"), spaceAfter=8)
    subtitle = ParagraphStyle("FPISub", parent=styles["BodyText"], fontName=font_name, fontSize=9, leading=11, textColor=colors.HexColor("#475569"))
    h2 = ParagraphStyle("FPIH2", parent=styles["Heading2"], fontName=font_bold, fontSize=14, leading=17, textColor=colors.HexColor("#1e3a8a"), spaceBefore=6, spaceAfter=6)
    h3 = ParagraphStyle("FPIH3", parent=styles["Heading3"], fontName=font_bold, fontSize=11, leading=13, textColor=colors.HexColor("#0f172a"), spaceBefore=4, spaceAfter=4)
    body = ParagraphStyle("FPIBody", parent=styles["BodyText"], fontName=font_name, fontSize=8.3, leading=10.2, textColor=colors.HexColor("#111827"))
    body_white = ParagraphStyle("FPIBodyWhite", parent=styles["BodyText"], fontName=font_name, fontSize=8.2, leading=10.2, textColor=colors.white)
    small = ParagraphStyle("FPISmall", parent=styles["BodyText"], fontName=font_name, fontSize=7.3, leading=9, textColor=colors.HexColor("#64748b"))
    header = ParagraphStyle("FPIHeader", parent=styles["BodyText"], fontName=font_bold, fontSize=7.7, leading=9.2, textColor=colors.white, alignment=TA_CENTER)
    kpi_label = ParagraphStyle("KPILabel", parent=styles["BodyText"], fontName=font_bold, fontSize=7, leading=8, textColor=colors.HexColor("#bfdbfe"), alignment=TA_CENTER)
    kpi_value = ParagraphStyle("KPIValue", parent=styles["BodyText"], fontName=font_bold, fontSize=18, leading=21, textColor=colors.white, alignment=TA_CENTER)

    def P(text, style=body):
        return Paragraph(html.escape(pdf_safe_text(text)).replace("\n", "<br/>"), style)

    def section(title_text):
        return Table([[P(title_text, h2)]], colWidths=[27.2*cm], style=[
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#e0f2fe")),
            ("BOX", (0,0), (-1,-1), .5, colors.HexColor("#93c5fd")),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
            ("RIGHTPADDING", (0,0), (-1,-1), 8),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ])

    def kpi_card(label, value, note, color="#1e3a8a"):
        data = [[P(label, kpi_label)], [P(value, kpi_value)], [P(note, body_white)]]
        t = Table(data, colWidths=[5.15*cm], rowHeights=[.55*cm, 1.0*cm, .8*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor(color)),
            ("BOX", (0,0), (-1,-1), .6, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        return t

    def styled_table(data, widths, header_color="#0f172a", body_bg="#ffffff", alt_bg="#f8fafc"):
        t = Table(data, colWidths=widths, repeatRows=1)
        style = [
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor(header_color)),
            ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 5),
            ("RIGHTPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("BACKGROUND", (0,1), (-1,-1), colors.HexColor(body_bg)),
        ]
        for r in range(2, len(data), 2):
            style.append(("BACKGROUND", (0,r), (-1,r), colors.HexColor(alt_bg)))
        t.setStyle(TableStyle(style))
        return t

    story = []

    # PAGE 1 - Executive cover/dashboard
    story.append(P("Football Performance Intelligence", title))
    story.append(P("Teljes minta vezetői riport | Demo FC U19 | 2026-W22 | Játékmodell: Pressing | Minta GPS/terhelési adatok", subtitle))
    story.append(Spacer(1, 7))

    story.append(Table([[
        kpi_card("TEAM READINESS", "78/100", "elfogadható, figyelendő", "#14532d"),
        kpi_card("LOAD CHANGE", "+27%", "heti terhelési növekedés", "#7c2d12"),
        kpi_card("SPRINT FIT", "72%", "edzés vs meccsigény", "#1e3a8a"),
        kpi_card("TOP RISK", "2 fő", "magas egyéni kockázat", "#7f1d1d"),
        kpi_card("MD-1 TAPER", "OK", "frissességi jel pozitív", "#064e3b"),
    ]], colWidths=[5.35*cm]*5))
    story.append(Spacer(1, 8))

    story.append(KeepTogether([
        section("Vezetői összefoglaló - mit kell tudni 30 másodperc alatt?"),
        Spacer(1, 4),
        styled_table([
            [P("Fő üzenet", header), P("Értelmezés", header), P("Azonnali döntés", header)],
            [P("A csapat alapvetően mérkőzésképes, de a hét nem teljesen tiszta."), P("A readiness 78/100, miközben két játékosnál magasabb risk észlelhető. A heti load +27%, a sprintprofil pedig csak 72%-a a meccsigénynek."), P("A következő edzés fő célja ne a plusz terhelés, hanem a frissesség megtartása és az egyéni terheléskontroll legyen.")],
            [P("A mikrociklus struktúrája részben jó."), P("Az MD-1 taper pozitív jel, de az MD-2 terhelése közel került a hét fő terhelési napjához."), P("MD-2 napon kisebb neuromuszkuláris terhelés, MD-1-en rövid aktiváció javasolt.")],
        ], [5.8*cm, 13.0*cm, 8.4*cm], header_color="#1e3a8a", body_bg="#eff6ff")
    ]))
    story.append(Spacer(1, 7))

    story.append(KeepTogether([
        section("Top 5 automatikus megállapítás"),
        Spacer(1, 4),
        styled_table([
            [P("#", header), P("Megállapítás", header), P("Súlyosság", header), P("Mit látunk?", header), P("Javaslat", header)],
            [P("1"), P("Heti terhelési kiugrás"), P("FIGYELMEZTETÉS"), P("A heti edzés terhelési pontértéke 27%-kal nőtt az előző héthez képest."), P("Következő edzésen terheléskontroll és egyéni reakciók figyelése.")],
            [P("2"), P("Alacsony sprintinger"), P("FIGYELMEZTETÉS"), P("A heti sprintprofil a meccsigény kb. 72%-a."), P("Rövid, kontrollált maximális sebességű blokk, ha a heti cél engedi.")],
            [P("3"), P("MD-2 terhelés magas lehet"), P("FIGYELMEZTETÉS"), P("Az MD-2 load közel volt a hét fő terhelési napjához."), P("Meccs előtt 48 órával alacsonyabb neuromuszkuláris terhelés.")],
            [P("4"), P("Két játékos magas risk zónában"), P("KRITIKUS"), P("Nagy D. és Varga L. egyéni terhelése eltér a csapatprofiltól."), P("Egyéni terheléskorrekció és regenerációs visszajelzés ellenőrzése.")],
            [P("5"), P("Pozitív tapering jel"), P("INFORMÁCIÓ"), P("Az MD-1 terhelés alacsonyabb volt a hét fő napjához képest."), P("A struktúra megtartható, ha a meccsteljesítmény visszaigazolja.")],
        ], [1.0*cm, 5.0*cm, 3.0*cm, 9.0*cm, 9.2*cm], header_color="#0f172a")
    ]))

    story.append(PageBreak())

    # PAGE 2 - Coaching priorities and player risk
    story.append(P("Edzői döntéstámogatás", title))
    story.append(P("Prioritások, játékos risk és gyakorlati javaslatok", subtitle))
    story.append(Spacer(1, 6))

    story.append(KeepTogether([
        section("Top 6 edzői teendő"),
        Spacer(1, 4),
        styled_table([
            [P("Prioritás", header), P("Teendő", header), P("Miért fontos?", header), P("Mikor?", header)],
            [P("1. Sprintterhelés kontroll"), P("Nagy D. és Varga L. kapjon kontrollált nagysebességű ingert, de ne újabb volumennövelő blokkot."), P("Mindkét játékosnál magasabb sprinttáv és terhelési löket látható."), P("Következő edzés")],
            [P("2. MD-2 frissesség"), P("A mérkőzés előtti 48 órában csökkenteni kell a teljes loadot és a lassítási terhelést."), P("A túl magas MD-2 terhelés ronthatja a meccsnapi frissességet."), P("Meccs előtt 2 nap")],
            [P("3. Alacsony terhelésű játékosok"), P("Kiss R. és Farkas Z. részére kiegészítő egyéni munka vagy fokozatos visszaterhelés."), P("Két hete csapatátlag alatti load, lemaradó inger alakulhat ki."), P("Következő 2 edzés")],
            [P("4. High effort monitoring"), P("A nagy intenzitású erőfeszítéseket játékosonként kell figyelni, nem csak csapatszinten."), P("A csapatátlag elfedhet egyéni neuromuszkuláris kockázatot."), P("Minden edzés után")],
            [P("5. Posztcsoport összevetés"), P("Szélsők és középpályások sprint/HSR arányát külön értékelni."), P("A játékmodell más fizikai profilt vár el posztonként."), P("Heti review")],
            [P("6. Frissességi kérdőív"), P("A két magas risk játékosnál rövid szubjektív frissességi check-in."), P("A GPS nem mutatja önmagában a belső terhelésérzetet."), P("Edzés előtt")],
        ], [4.7*cm, 10.0*cm, 9.2*cm, 3.3*cm], header_color="#14532d", body_bg="#f0fdf4")
    ]))
    story.append(Spacer(1, 7))

    story.append(KeepTogether([
        section("Játékos risk tábla - vezetői gyorsnézet"),
        Spacer(1, 4),
        styled_table([
            [P("Játékos", header), P("Poszt", header), P("Risk", header), P("Fő eltérés", header), P("Ajánlott lépés", header)],
            [P("Nagy D."), P("CM"), P("Magas - 82"), P("Sprinttáv +55%, összterhelés +18%"), P("Load kontroll, regenerációs monitor, következő edzésen limitált extra munka.")],
            [P("Varga L."), P("W"), P("Magas - 79"), P("High effort és lassítás kiugrás"), P("Excentrikus terhelés csökkentése, frissesség ellenőrzés.")],
            [P("Farkas Z."), P("DM"), P("Közepes - 63"), P("Max sebesség trend csökkenő"), P("Rövid, kontrollált max sebességű inger.")],
            [P("Kiss R."), P("GK"), P("Közepes - 61"), P("Alacsony heti load"), P("Pozícióspecifikus kiegészítő blokk.")],
            [P("Tóth B."), P("CB"), P("Alacsony - 38"), P("Stabil terhelés, nincs kiugrás"), P("Normál terhelés folytatható.")],
            [P("Mészáros P."), P("ST"), P("Alacsony - 34"), P("Jó sprint kitettség, kontrollált load"), P("Jelenlegi struktúra megtartható.")],
        ], [3.4*cm, 2.0*cm, 2.8*cm, 8.2*cm, 10.8*cm], header_color="#7f1d1d", body_bg="#fff7ed")
    ]))

    story.append(PageBreak())

    # PAGE 3 - Microcycle and model fit
    story.append(P("Mikrociklus és játékmodell illeszkedés", title))
    story.append(P("A riport nem csak adatot mutat, hanem edzői döntésre fordítja le a GPS-profilt.", subtitle))
    story.append(Spacer(1, 6))

    story.append(KeepTogether([
        section("Mikrociklus szerkezet - MD logika"),
        Spacer(1, 4),
        styled_table([
            [P("Nap", header), P("Load index", header), P("Sprint", header), P("HSR", header), P("Értelmezés", header)],
            [P("MD-4"), P("Magas"), P("Közepes"), P("Magas"), P("Fő terhelési nap, megfelelő helyen a mikrociklusban.")],
            [P("MD-3"), P("Közepes"), P("Magas"), P("Közepes"), P("Jó nap maximális sebességű ingerre.")],
            [P("MD-2"), P("Közepesen magas"), P("Alacsony"), P("Közepes"), P("Kicsit magas a meccshez közel, frissességi kockázat.")],
            [P("MD-1"), P("Alacsony"), P("Minimális"), P("Alacsony"), P("Pozitív tapering jel, aktivációs napként megfelelő.")],
            [P("MD"), P("Meccs"), P("Referencia"), P("Referencia"), P("A hét értékelése ehhez viszonyítva történik.")],
        ], [3.0*cm, 3.2*cm, 3.2*cm, 3.2*cm, 14.6*cm], header_color="#1e3a8a", body_bg="#eff6ff")
    ]))
    story.append(Spacer(1, 7))

    story.append(KeepTogether([
        section("Játékmodell illeszkedés - Pressing profil"),
        Spacer(1, 4),
        styled_table([
            [P("Komponens", header), P("Cél", header), P("Aktuális hét", header), P("Értékelés", header)],
            [P("Táv/perc"), P("Meccsprofil 90%+"), P("88%"), P("Közel jó, de még figyelendő.")],
            [P("High effort"), P("Meccsprofil 75%+"), P("69%"), P("Pressing modellhez kissé kevés ismételt intenzív akció.")],
            [P("Sprintprofil"), P("Meccsprofil 80%+"), P("72%"), P("Transition/pressing elemekhez célzott sprintinger kell.")],
            [P("Lassítási terhelés"), P("Kontrollált, ne kiugró"), P("+31%"), P("Regenerációs és excentrikus terhelési kockázat.")],
        ], [5.5*cm, 6.2*cm, 5.0*cm, 10.5*cm], header_color="#312e81", body_bg="#f5f3ff")
    ]))
    story.append(Spacer(1, 7))

    story.append(KeepTogether([
        section("Vizuális gyorsjelentés - mit látna a vezető az appban?"),
        Spacer(1, 4),
        Table([
            [kpi_card("PRESSING FIT", "71%", "játékmodell illeszkedés", "#312e81"),
             kpi_card("MAX SPEED EXP.", "64%", "sebességkitettség", "#1e3a8a"),
             kpi_card("TAPERING", "84%", "meccs előtti frissesség", "#14532d"),
             kpi_card("PLAYER RISK", "2 high", "egyéni kontroll szükséges", "#7f1d1d"),
             kpi_card("COACHING", "6 task", "automatikus teendő", "#0f172a")]
        ], colWidths=[5.35*cm]*5)
    ]))

    story.append(PageBreak())

    # PAGE 4 - What Pro gives
    story.append(P("Mit kap a klub a Pro verzióban?", title))
    story.append(P("A minta riport célja, hogy megmutassa: a rendszer nem táblázatot ad, hanem döntéstámogató vezetői anyagot.", subtitle))
    story.append(Spacer(1, 7))

    story.append(KeepTogether([
        section("Pro riport tartalom"),
        Spacer(1, 4),
        styled_table([
            [P("Modul", header), P("Mit ad?", header), P("Kinek hasznos?", header)],
            [P("Vezetői riport"), P("30 másodperces vezetői összefoglaló, readiness, top risk, top teendő."), P("sportigazgató, vezetőedző")],
            [P("📅 Mikrociklus"), P("MD-4/MD-3/MD-2/MD-1 logika, tapering, sprintinger, frissességi jelzések."), P("vezetőedző, erőnléti edző")],
            [P("Játékos risk motor"), P("Egyéni terhelési eltérések, high effort, sprint, lassítás, load kiugrás."), P("erőnléti edző, rehabilitáció")],
            [P("Játékmodell illeszkedés"), P("Pressing, transition, possession vagy low block fizikai profil összevetése."), P("szakmai stáb")],
            [P("Export központ"), P("PDF, Word, Excel riportok vezetői és szakmai felhasználásra."), P("klubvezetés, stáb")],
            [P("Performance memory"), P("Több hét/szezon trendjei, periodizációs mintázatok, hosszú távú terhelésprofil."), P("klubszintű monitoring")],
        ], [5.1*cm, 14.5*cm, 7.6*cm], header_color="#0f172a", body_bg="#f8fafc")
    ]))
    story.append(Spacer(1, 7))

    story.append(KeepTogether([
        section("Demo vs Pro"),
        Spacer(1, 4),
        styled_table([
            [P("Funkció", header), P("Demo", header), P("Pro", header)],
            [P("Saját adat feltöltése"), P("Igen, korlátozott: max 8 játékos / 3 hét / 5000 sor"), P("Korlátlan")],
            [P("Vezetői riport"), P("Igen, preview"), P("Teljes")],
            [P("PDF / Word / Excel export"), P("Minta PDF és vízjeles előnézet"), P("Teljes export")],
            [P("Performance memory"), P("Nem"), P("Igen")],
            [P("Több szezon"), P("Nem"), P("Igen")],
            [P("Saját benchmark"), P("Nem"), P("Igen")],
        ], [9.0*cm, 9.0*cm, 9.0*cm], header_color="#14532d", body_bg="#f0fdf4")
    ]))

    doc.build(story)
    output.seek(0)
    return output.read()



# -----------------------------------------------------------------------------
# V4.3 - Productized Demo / Pro layer - unique Streamlit export keys
# -----------------------------------------------------------------------------
DEMO_PLAYER_LIMIT = 8
DEMO_WEEK_LIMIT = 3
DEMO_ROW_LIMIT = 5000

# -----------------------------------------------------------------------------
# V4.5 - Emailhez kötött aktiváló kód koncepció
# -----------------------------------------------------------------------------
# Éles verzióban ezt nem a kódban tároljuk, hanem Supabase táblában:
# licenses(email, activation_code_hash, plan, is_active, expires_at, max_users, club_name)
# A felhasználó megadja: email + aktiváló kód.
# Az app lekéri / ellenőrzi a hash-t, és ha aktív, Pro módot ad.
# Mostani MVP-ben marad az egyszerű tesztkód: .


# -----------------------------------------------------------------------------
# Supabase license layer
# -----------------------------------------------------------------------------
def get_secret_value(name: str, default: str = "") -> str:
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name, default)


def get_supabase_client():
    url = get_secret_value("SUPABASE_URL")
    key = get_secret_value("SUPABASE_ANON_KEY")
    if not url or not key or create_client is None:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


def hash_license_key(raw_key: str) -> str:
    salt = get_secret_value("LICENSE_SALT", "performance-intelligence")
    return hashlib.sha256((salt + "::" + str(raw_key).strip()).encode("utf-8")).hexdigest()


def validate_license_supabase(email: str, license_key: str) -> Dict[str, object]:
    email = str(email or "").strip().lower()
    license_key = str(license_key or "").strip()
    if not email or not license_key:
        return {"ok": False, "message": "Add meg az e-mail címet és az aktiváló kódot."}

    fallback = get_secret_value("FALLBACK_PRO_CODE")
    if fallback and license_key == fallback:
        return {
            "ok": True,
            "email": email,
            "plan": "pro",
            "club_name": "Pro klub",
            "team_name": "Pro csapat",
            "license_id": "fallback",
            "message": "Pro hozzáférés aktív.",
        }

    client = get_supabase_client()
    if client is None:
        return {"ok": False, "message": "Supabase kapcsolat nincs beállítva. Demo módban folytatható."}

    try:
        key_hash = hash_license_key(license_key)
        resp = client.rpc("validate_license", {
            "p_email": email,
            "p_license_hash": key_hash,
        }).execute()
        data = resp.data
        if isinstance(data, list):
            data = data[0] if data else None

        if not data:
            return {"ok": False, "message": "Nem található aktív licenc ehhez az e-mailhez és kódhoz."}

        if data.get("ok"):
            return {
                "ok": True,
                "email": data.get("email", email),
                "plan": data.get("plan", "pro"),
                "club_name": data.get("club_name", ""),
                "team_name": data.get("team_name", ""),
                "license_id": data.get("license_id", ""),
                "message": "Pro hozzáférés aktív.",
            }

        return {"ok": False, "message": data.get("message", "A licenc nem aktív vagy lejárt.")}
    except Exception as exc:
        return {"ok": False, "message": f"Licencellenőrzési hiba: {exc}"}


def is_pro_mode() -> bool:
    lic = st.session_state.get("license_status", {})
    return bool(lic.get("ok"))


def is_demo_mode() -> bool:
    return not is_pro_mode()


def render_mode_badge() -> None:
    if is_pro_mode():
        lic = st.session_state.get("license_status", {})
        st.sidebar.success("Pro hozzáférés aktív")
        club = lic.get("club_name") or lic.get("email")
        if club:
            st.sidebar.caption(str(club))
        if lic.get("team_name"):
            st.sidebar.caption(f"Csapat: {lic.get('team_name')}")
    else:
        st.sidebar.success("Demo mód")
        st.sidebar.caption(f"Demo limit: max {DEMO_PLAYER_LIMIT} játékos · max {DEMO_WEEK_LIMIT} hét · max {DEMO_ROW_LIMIT} sor")


def render_license_panel() -> None:
    st.sidebar.markdown("### Belépés")
    if is_pro_mode():
        render_mode_badge()
        if st.sidebar.button("Kijelentkezés", use_container_width=True, key="logout_license"):
            st.session_state.pop("license_status", None)
            st.rerun()
        return

    email = st.sidebar.text_input("E-mail", value=st.session_state.get("user_email", ""), placeholder="nev@klub.hu", key="license_email")
    if email:
        st.session_state["user_email"] = email

    license_key = st.sidebar.text_input("Aktiváló kód", type="password", help="A klubhoz kapott aktiváló kód.", key="license_key")
    if st.sidebar.button("Pro aktiválása", use_container_width=True, key="activate_license"):
        result = validate_license_supabase(email, license_key)
        if result.get("ok"):
            st.session_state["license_status"] = result
            st.sidebar.success("Pro hozzáférés aktiválva.")
            st.rerun()
        else:
            st.sidebar.warning(result.get("message", "Sikertelen aktiválás."))

    render_mode_badge()


def pro_locked_box(feature: str) -> None:
    st.markdown(
        f"""
        <div class="export-panel">
            <h3 style="margin-top:0;">🔒 {html.escape(feature)}</h3>
            <p style="color:#e0f2fe;">
                Ez a funkció a Pro verzió része. A demo célja, hogy saját adaton is lásd az értéket,
                de a teljes riport/export és hosszabb trendek Pro módban érhetők el.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def apply_demo_limits(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, object]]:
    """Demo verzióban saját feltöltés limitálása: 8 játékos, 3 hét, 5000 sor."""
    info = {"limited": False, "original_rows": len(df), "original_players": 0, "original_weeks": 0}
    if df.empty or is_pro_mode():
        return df, info

    out = df.copy()
    players = sorted(out["player_name"].dropna().astype(str).unique().tolist()) if "player_name" in out.columns else []
    weeks = sorted(out["week"].dropna().astype(str).unique().tolist()) if "week" in out.columns else []
    info["original_players"] = len(players)
    info["original_weeks"] = len(weeks)

    keep_players = players[:DEMO_PLAYER_LIMIT]
    keep_weeks = weeks[-DEMO_WEEK_LIMIT:]
    if keep_players and "player_name" in out.columns:
        out = out[out["player_name"].isin(keep_players)]
    if keep_weeks and "week" in out.columns:
        out = out[out["week"].isin(keep_weeks)]
    if len(out) > DEMO_ROW_LIMIT:
        out = out.head(DEMO_ROW_LIMIT)

    info.update({
        "limited": len(out) != len(df) or len(players) > DEMO_PLAYER_LIMIT or len(weeks) > DEMO_WEEK_LIMIT,
        "visible_rows": len(out),
        "visible_players": out["player_name"].nunique() if "player_name" in out.columns else 0,
        "visible_weeks": out["week"].nunique() if "week" in out.columns else 0,
    })
    return out, info


def render_demo_limit_notice(info: Dict[str, object]) -> None:
    if not info or not info.get("limited"):
        return
    st.warning(
        "Demo limit aktív: "
        f"játékosok {info.get('original_players', 0)} → {info.get('visible_players', 0)}, "
        f"hetek {info.get('original_weeks', 0)} → {info.get('visible_weeks', 0)}, "
        f"sorok {info.get('original_rows', 0)} → {info.get('visible_rows', 0)}. "
        "A teljes keret Pro módban érhető el."
    )


@st.cache_data(show_spinner=False)
def build_demo_performance_data() -> pd.DataFrame:
    """Beépített mintaadat: 8 játékos, 3 hét, edzések + meccsek.
    Direkt olyan mintákkal, amelyekből működő readiness, mikrociklus és risk riport készül.
    """
    rng = np.random.default_rng(42)
    players = ["Kovács M.", "Nagy D.", "Szabó B.", "Tóth Á.", "Varga L.", "Farkas Z.", "Balogh P.", "Kiss R."]
    positions = ["CB", "FB", "CM", "AM", "W", "F", "DM", "GK"]
    start = pd.Timestamp("2026-05-18")
    rows = []
    for w in range(3):
        week_start = start + pd.Timedelta(days=7*w)
        # MD-4, MD-3, MD-2, MD-1, MD sessions
        sessions = [
            (week_start + pd.Timedelta(days=1), "Edzés", "MD-4 nagyobb terhelés", 1.08),
            (week_start + pd.Timedelta(days=2), "Edzés", "MD-3 intenzív játék", 1.00),
            (week_start + pd.Timedelta(days=3), "Edzés", "MD-2 taktikai", 0.78 + 0.10*w),
            (week_start + pd.Timedelta(days=4), "Edzés", "MD-1 aktiváció", 0.46 + 0.08*w),
            (week_start + pd.Timedelta(days=5), "Meccs", "Bajnoki mérkőzés", 1.28),
        ]
        for date, typ, sess, factor in sessions:
            for idx, (player, pos) in enumerate(zip(players, positions)):
                role_factor = 1.0 + (idx % 4) * 0.04
                noise = rng.normal(1.0, 0.08)
                base_dist = 5600 if typ == "Edzés" else 9200
                total_distance = max(1200, base_dist * factor * role_factor * noise)
                duration = 75 if typ == "Edzés" else 95
                dpm = total_distance / duration
                sprint_dist = max(20, (180 if typ == "Edzés" else 520) * factor * role_factor * rng.normal(1, .18))
                # direkt kiugrók: 2 játékos magas risk a 3. héten
                if w == 2 and player in ["Nagy D.", "Varga L."]:
                    sprint_dist *= 1.55
                    total_distance *= 1.18
                acc_high = max(0, rng.normal(14, 4) * factor)
                dec_high = max(0, rng.normal(13, 4) * factor)
                rows.append({
                    "Játékos neve": player,
                    "Típus": typ,
                    "Szakasz neve": sess,
                    "Poszt": pos,
                    "Kezdési idő": date + pd.Timedelta(hours=10),
                    "Időtartam": duration,
                    "Teljes táv [m]": round(total_distance, 0),
                    "Táv/perc [m/min]": round(dpm, 1),
                    "Maximális sebesség [km/h]": round(rng.normal(28.5 if typ == "Meccs" else 27.0, 1.2), 1),
                    "Sprintek": int(max(1, sprint_dist / 45)),
                    "Táv a sebesség célzónában 4 [m] (19.80 - 24.99 km/h)": round(sprint_dist * 1.7, 0),
                    "Táv a sebesség célzónában 5 [m] (25.00- km/h)": round(sprint_dist, 0),
                    "Edzési terhelési pontérték": round(total_distance / 80 + sprint_dist / 5 + acc_high * 2 + dec_high * 2, 0),
                    "Kardióterhelés": round(total_distance / 100, 0),
                    "Regenerálódási idő [h]": round(18 + factor * 8 + rng.normal(0, 2), 1),
                    "Izomterhelés": round(45 + factor * 15 + rng.normal(0, 4), 1),
                    "Átlagos pulzus [bpm]": round(136 + factor * 12 + rng.normal(0, 5), 0),
                    "Maximális pulzus [bpm]": round(178 + factor * 6 + rng.normal(0, 4), 0),
                    "HRV (RMSSD)": round(55 - factor * 8 + rng.normal(0, 5), 1),
                    "Gyorsulások száma (2.50 - 2.99 m/s²)": round(acc_high * 1.6, 0),
                    "Gyorsulások száma (3.00 - 50.00 m/s²)": round(acc_high, 0),
                    "Gyorsulások száma (-2.99 - -2.50 m/s²)": round(dec_high * 1.5, 0),
                    "Gyorsulások száma (-50.00 - -3.00 m/s²)": round(dec_high, 0),
                })
    return pd.DataFrame(rows)



# -----------------------------------------------------------------------------
# V5.8 - Product report pack: vezetői / erőnléti / mikrociklus PDF + minta PDF-ek
# -----------------------------------------------------------------------------

def _fpi_to_standard_if_needed(data: pd.DataFrame) -> pd.DataFrame:
    """Bármely támogatott Excelből vagy már standardizált DF-ből riportképes DF-et készít."""
    if data is None or data.empty:
        return pd.DataFrame()
    if {"player_name", "week", "start_time"}.issubset(set(data.columns)):
        out = data.copy()
    else:
        out, _, missing = standardize_dataframe(data.copy())
        if missing:
            return pd.DataFrame()
    try:
        out = add_position_group(out)
    except Exception:
        pass
    return out


def _fpi_latest_week(df: pd.DataFrame, selected_week: Optional[str] = None) -> Optional[str]:
    if df is None or df.empty or "week" not in df.columns:
        return selected_week
    weeks = sorted(df["week"].dropna().astype(str).unique().tolist())
    if selected_week in weeks:
        return selected_week
    return weeks[-1] if weeks else selected_week


def _fpi_report_context(data: pd.DataFrame, selected_week: Optional[str] = None, playstyle: str = "Kiegyensúlyozott") -> Dict[str, object]:
    """Riportok közös számítási magja. Ugyanezt használja a minta PDF és az éles PDF."""
    df = _fpi_to_standard_if_needed(data)
    week = _fpi_latest_week(df, selected_week)
    if df.empty or not week:
        return {"df": df, "selected_week": week, "error": "Nincs riportképes adat."}
    try:
        base = team_insights(df, week)
        micro = microcycle_insights(df, week)
        style = playstyle_insights(df, week, playstyle)
        pattern = build_pattern_insights(df, week)
        readiness_score, readiness_components, readiness_reasons = calculate_readiness_score(df, week, playstyle)
        fingerprints = build_weekly_fingerprints(df)
        current_fp = fingerprints[fingerprints["week"].astype(str) == str(week)] if not fingerprints.empty and "week" in fingerprints.columns else pd.DataFrame()
        periodization_type = current_fp["periodizacios_tipus"].iloc[0] if not current_fp.empty and "periodizacios_tipus" in current_fp.columns else "Nincs elég adat"
        insights = sorted(base + micro + style + pattern, key=lambda x: SEVERITY_RANK.get(x.severity, 9))[:18]
        summary = build_weekly_summary(insights, week, playstyle)
        insights = humanize_insights(insights)
        priorities = humanize_priority_list(build_adaptive_recommendations(insights, readiness_score, periodization_type, pattern, playstyle))
        summary = coach_friendly_phrase(summary)
        risk = calculate_player_risk(df, week)
        past_df, past_text = build_past_week_review(df, week, playstyle)
        current_df, current_text = build_current_remaining_days_plan(df, week, playstyle, readiness_score, periodization_type, risk)
        next_df, next_text = build_next_week_plan_v5(df, week, playstyle, readiness_score, periodization_type, risk, past_df, current_df)
        player_actions = build_player_next_actions(risk, df, week)
        weekly = aggregate_weekly(df) if "week" in df.columns else pd.DataFrame()
        player_week = player_weekly(df) if "week" in df.columns else pd.DataFrame()
        return {
            "df": df,
            "selected_week": week,
            "playstyle": playstyle,
            "readiness_score": readiness_score,
            "readiness_components": readiness_components,
            "readiness_reasons": readiness_reasons,
            "periodization_type": periodization_type,
            "insights": insights,
            "insights_df": build_insight_export_df(insights),
            "priorities": priorities,
            "summary": summary + f"\n\nMeccskészültség: {readiness_score}/100 ({score_to_label(readiness_score)})\nPeriodizációs besorolás: {periodization_type}",
            "risk_df": risk,
            "past_df": past_df,
            "past_text": past_text,
            "current_df": current_df,
            "current_text": current_text,
            "next_df": next_df,
            "next_text": next_text,
            "player_actions_df": player_actions,
            "weekly": weekly,
            "player_week": player_week,
            "fingerprints": fingerprints,
        }
    except Exception as exc:
        return {"df": df, "selected_week": week, "error": str(exc)}


def build_fpi_product_pdf_bytes(
    data: pd.DataFrame,
    selected_week: Optional[str] = None,
    playstyle: str = "Kiegyensúlyozott",
    report_type: str = "full",
    demo_label: str = "",
    tactical_context: Optional[Dict[str, object]] = None,
) -> Optional[bytes]:
    """Egységes PDF motor.

    report_type:
    - executive: 1-2 oldalas vezetőedzői / sportigazgatói riport
    - fitness: részletes erőnléti riport
    - microcycle: múlt hét / aktuális hét / jövő hét terv
    - full: teljes döntéstámogató csomag
    """
    if SimpleDocTemplate is None:
        return None
    from reportlab.platypus import PageBreak

    ctx = _fpi_report_context(data, selected_week, playstyle)
    if ctx.get("error"):
        return None
    tactical_context = tactical_context if tactical_context is not None else st.session_state.get("tactical_pro_context", None)

    df = ctx["df"]
    week = ctx["selected_week"]
    readiness = int(ctx["readiness_score"])
    risk_df = ctx["risk_df"] if isinstance(ctx.get("risk_df"), pd.DataFrame) else pd.DataFrame()
    priorities = ctx.get("priorities", []) or []
    insights_df = ctx["insights_df"] if isinstance(ctx.get("insights_df"), pd.DataFrame) else pd.DataFrame()
    weekly = ctx["weekly"] if isinstance(ctx.get("weekly"), pd.DataFrame) else pd.DataFrame()
    player_week = ctx["player_week"] if isinstance(ctx.get("player_week"), pd.DataFrame) else pd.DataFrame()
    player_actions = ctx["player_actions_df"] if isinstance(ctx.get("player_actions_df"), pd.DataFrame) else pd.DataFrame()
    next_df = ctx["next_df"] if isinstance(ctx.get("next_df"), pd.DataFrame) else pd.DataFrame()
    current_df = ctx["current_df"] if isinstance(ctx.get("current_df"), pd.DataFrame) else pd.DataFrame()
    high_risk = int((risk_df.get("Kockázati szint", pd.Series(dtype=str)).astype(str) == "Magas").sum()) if not risk_df.empty else 0
    med_risk = int((risk_df.get("Kockázati szint", pd.Series(dtype=str)).astype(str) == "Közepes").sum()) if not risk_df.empty else 0

    font_name, font_bold = _register_pdf_font()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=0.9*cm, leftMargin=0.9*cm, topMargin=0.7*cm, bottomMargin=0.7*cm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("FPI58Title", parent=styles["Title"], fontName=font_bold, fontSize=20, leading=23, textColor=colors.HexColor("#0F172A"))
    sub = ParagraphStyle("FPI58Sub", parent=styles["Normal"], fontName=font_name, fontSize=8.8, leading=11, textColor=colors.HexColor("#334155"))
    h2 = ParagraphStyle("FPI58H2", parent=styles["Heading2"], fontName=font_bold, fontSize=11.2, leading=14, textColor=colors.HexColor("#0F172A"))
    body = ParagraphStyle("FPI58Body", parent=styles["Normal"], fontName=font_name, fontSize=8.0, leading=10.2, textColor=colors.HexColor("#111827"))
    small = ParagraphStyle("FPI58Small", parent=styles["Normal"], fontName=font_name, fontSize=7.0, leading=8.6, textColor=colors.HexColor("#111827"))
    head = ParagraphStyle("FPI58Head", parent=styles["Normal"], fontName=font_bold, fontSize=7.2, leading=8.8, alignment=1, textColor=colors.white)
    white_big = ParagraphStyle("FPI58WhiteBig", parent=styles["Normal"], fontName=font_bold, fontSize=16, leading=18, alignment=1, textColor=colors.white)
    white_small = ParagraphStyle("FPI58WhiteSmall", parent=styles["Normal"], fontName=font_name, fontSize=7.0, leading=8.5, alignment=1, textColor=colors.white)

    def clean(v: object) -> str:
        return pdf_safe_text(v).replace("\r", "").strip()

    def P(v, style=body):
        return Paragraph(html.escape(clean(v)).replace("\n", "<br/>"), style)

    def section(text: str, color: str = "#DBEAFE"):
        t = Table([[P(text, h2)]], colWidths=[27.7*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor(color)),
            ("BOX", (0,0), (-1,-1), 0.4, colors.HexColor("#93C5FD")),
            ("LEFTPADDING", (0,0), (-1,-1), 7), ("RIGHTPADDING", (0,0), (-1,-1), 7),
            ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        return t

    def table(rows, widths, header_bg="#0F172A", row_bgs=None):
        if row_bgs is None:
            row_bgs = [colors.white, colors.HexColor("#F8FAFC")]
        t = Table(rows, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor(header_bg)),
            ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), row_bgs),
            ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        return t

    def kpi(label, value, note, color):
        t = Table([[P(label, white_small)], [P(value, white_big)], [P(note, white_small)]], colWidths=[5.25*cm], rowHeights=[0.5*cm, 0.85*cm, 0.5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor(color)),
            ("BOX", (0,0), (-1,-1), 0.4, colors.white),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ]))
        return t

    story = []
    label_prefix = f"{demo_label} | " if demo_label else ""
    report_names = {
        "executive": "Vezetői riport",
        "fitness": "Erőnléti szakmai riport",
        "microcycle": "Mikrociklus döntéstámogató riport",
        "full": "Teljes stáb riportcsomag",
    }

    def add_cover():
        story.append(P("Football Performance Intelligence", title))
        story.append(P(f"{label_prefix}{report_names.get(report_type, 'Riport')} | Hét: {format_week_label(str(week))} | Játékmodell: {playstyle} | Generálva: {datetime.now().strftime('%Y-%m-%d %H:%M')}", sub))
        story.append(Spacer(1, 0.25*cm))
        kpis = [
            kpi("READINESS", f"{readiness}/100", score_to_label(readiness), "#166534" if readiness >= 75 else "#1E3A8A" if readiness >= 60 else "#991B1B"),
            kpi("HIGH RISK", f"{high_risk} fő", "egyéni kontroll", "#7F1D1D" if high_risk else "#166534"),
            kpi("MEDIUM RISK", f"{med_risk} fő", "figyelendő játékos", "#92400E" if med_risk else "#166534"),
            kpi("INSIGHT", str(len(insights_df)), "automatikus megállapítás", "#0F172A"),
            kpi("HETEK", str(df['week'].nunique()) if 'week' in df.columns else "—", "elemzett adatbázis", "#1E3A8A"),
        ]
        story.append(Table([kpis], colWidths=[5.45*cm]*5))
        story.append(Spacer(1, 0.25*cm))

    def add_executive_page():
        story.append(section("1. Vezetői oldal – 30 másodperces döntési kép", "#DBEAFE"))
        summary_lines = [x.strip() for x in str(ctx.get("summary", "")).splitlines() if x.strip()]
        summary_text = "\n".join(summary_lines[:9]) if summary_lines else "Nincs automatikus összefoglaló."
        rows = [[P("Fő üzenet", head), P("Mit jelent ez a stábnak?", head), P("Következő döntés", head)]]
        first_priority = priorities[0] if priorities else {}
        rows.append([
            P(summary_text, body),
            P(f"Meccskészültség: {readiness}/100 ({score_to_label(readiness)}). Magas risk: {high_risk} fő, közepes risk: {med_risk} fő. Periodizáció: {ctx.get('periodization_type', '—')}.", body),
            P(first_priority.get("Teendő", "Heti terhelés és egyéni risk áttekintése a következő edzés előtt."), body),
        ])
        story.append(table(rows, [9.2*cm, 9.2*cm, 9.3*cm], header_bg="#1E3A8A", row_bgs=[colors.HexColor("#EFF6FF")]))
        story.append(Spacer(1, 0.22*cm))
        story.append(section("Top edzői teendők", "#DCFCE7"))
        pr = [[P("#", head), P("Teendő", head), P("Miért fontos?", head), P("Mikor?", head)]]
        for i, item in enumerate(priorities[:5], 1):
            pr.append([P(i, small), P(item.get("Teendő", item.get("Cím", "")), small), P(item.get("Miért", ""), small), P(item.get("Mikor", "Következő edzés"), small)])
        if len(pr) == 1:
            pr.append([P("1", small), P("Normál monitoring", small), P("Nincs kritikus jelzés.", small), P("Heti review", small)])
        story.append(table(pr, [1.0*cm, 11.4*cm, 10.5*cm, 4.8*cm], header_bg="#166534", row_bgs=[colors.HexColor("#ECFDF5"), colors.white]))
        story.append(Spacer(1, 0.22*cm))
        story.append(section("Játékos risk gyorsnézet", "#FEE2E2"))
        risk_cols = [c for c in ["Játékos", "Kockázati szint", "Risk score", "Kockázati pontszám", "Fő ok", "Fő okok"] if c in risk_df.columns]
        if not risk_cols:
            risk_cols = ["Játékos", "Kockázati szint", "Fő ok"]
            rrows = [[P(c, head) for c in risk_cols], [P("Nincs kiemelt risk", small), P("Alacsony", small), P("A hét alapján nincs azonnali beavatkozási jelzés.", small)]]
        else:
            rrows = [[P(c, head) for c in risk_cols]]
            for _, r in risk_df.head(8).iterrows():
                rrows.append([P(r.get(c, ""), small) for c in risk_cols])
        story.append(table(rrows, [27.7*cm/len(rrows[0])]*len(rrows[0]), header_bg="#7F1D1D", row_bgs=[colors.white, colors.HexColor("#FEF2F2")]))

    def add_fitness_page():
        story.append(section("2. Erőnléti szakmai oldal – GPS terhelés, trend és játékosszint", "#E0F2FE"))
        # heti csapatösszegzés
        wk = weekly.copy()
        if not wk.empty:
            wk = wk[wk["week"].astype(str) == str(week)].copy()
        cols = [c for c in ["session_type", "total_distance", "duration_min", "distance_per_min", "hsr_distance", "sprint_distance", "sprints", "high_efforts", "training_load", "max_speed"] if c in wk.columns]
        rows = [[P("Típus", head), P("Össztáv", head), P("Perc", head), P("m/perc", head), P("HSR", head), P("Sprint táv", head), P("Sprint", head), P("High Eff.", head), P("Load", head), P("Max seb.", head)]]
        if not wk.empty:
            for _, r in wk.head(8).iterrows():
                rows.append([
                    P(r.get("session_type", ""), small),
                    P(f"{r.get('total_distance', 0):.0f}", small),
                    P(f"{r.get('duration_min', 0):.0f}", small),
                    P(f"{r.get('distance_per_min', 0):.1f}", small),
                    P(f"{r.get('hsr_distance', 0):.0f}", small),
                    P(f"{r.get('sprint_distance', 0):.0f}", small),
                    P(f"{r.get('sprints', 0):.0f}", small),
                    P(f"{r.get('high_efforts', 0):.0f}", small),
                    P(f"{r.get('training_load', 0):.0f}", small),
                    P(f"{r.get('max_speed', 0):.1f}", small),
                ])
        else:
            rows.append([P("Nincs adat", small)] + [P("—", small)]*9)
        story.append(table(rows, [2.8*cm, 3.0*cm, 2.5*cm, 2.5*cm, 3.0*cm, 3.0*cm, 2.4*cm, 2.5*cm, 2.5*cm, 3.0*cm], header_bg="#0369A1"))
        story.append(Spacer(1, 0.25*cm))
        story.append(section("Top játékosok – heti terhelési profil", "#F0FDFA"))
        pw = player_week.copy()
        if not pw.empty and "week" in pw.columns:
            pw = pw[pw["week"].astype(str) == str(week)].copy()
            sort_col = "training_load" if "training_load" in pw.columns else "total_distance"
            pw = pw.sort_values(sort_col, ascending=False)
        prows = [[P("Játékos", head), P("Össztáv", head), P("HSR", head), P("Sprint táv", head), P("High Efforts", head), P("Load", head), P("Max seb.", head), P("Értelmezés", head)]]
        if not pw.empty:
            for _, r in pw.head(12).iterrows():
                interp = "Magas heti load – regeneráció kontroll" if float(r.get("training_load", 0) or 0) >= float(pw.get("training_load", pd.Series([0])).quantile(.75) or 0) else "Normál monitoring"
                prows.append([P(r.get("player_name", ""), small), P(f"{r.get('total_distance',0):.0f}", small), P(f"{r.get('hsr_distance',0):.0f}", small), P(f"{r.get('sprint_distance',0):.0f}", small), P(f"{r.get('high_efforts',0):.0f}", small), P(f"{r.get('training_load',0):.0f}", small), P(f"{r.get('max_speed',0):.1f}", small), P(interp, small)])
        else:
            prows.append([P("Nincs játékosszintű adat", small)] + [P("—", small)]*7)
        story.append(table(prows, [4.5*cm, 3.0*cm, 3.0*cm, 3.0*cm, 3.0*cm, 3.0*cm, 2.8*cm, 5.4*cm], header_bg="#0F766E", row_bgs=[colors.white, colors.HexColor("#F0FDFA")]))
        story.append(Spacer(1, 0.2*cm))
        story.append(section("Erőnléti edzői értelmezés", "#FEF3C7"))
        notes = [
            "A riport nem váltja ki az erőnléti edző döntését: előkészíti a heti review-t, kiemeli az eltéréseket és egységes PDF-et ad a stábnak.",
            "A High Efforts külön mezőként szerepel; ha nincs külön oszlop, az app gyorsulás/lassítás alapon becsli.",
            "A 4-es és 5-ös sebességzóna külön is kezelhető, de összevont 4+5 export esetén is használható HSR-ként.",
        ]
        story.append(table([[P("Megjegyzés", head), P("Használat", head)]] + [[P(n, small), P("Heti review / stábmegbeszélés", small)] for n in notes], [20*cm, 7.7*cm], header_bg="#92400E", row_bgs=[colors.HexColor("#FFFBEB"), colors.white]))

    def add_micro_page():
        story.append(section("3. Mikrociklus oldal – múlt hét / aktuális hét / jövő hét", "#EDE9FE"))
        blocks = [
            ("Múlt hét teljes értékelése", ctx.get("past_text", ""), "#312E81"),
            ("Aktuális hét – hátralévő napok javaslata", ctx.get("current_text", ""), "#1E3A8A"),
            ("Jövő heti MD-bontású terv", ctx.get("next_text", ""), "#166534"),
        ]
        bdata = [[P("Szekció", head), P("Automatikus értékelés / javaslat", head)]]
        for name, txt, _ in blocks:
            bdata.append([P(name, body), P(txt or "Nincs elegendő adat a részletes szöveghez.", small)])
        story.append(table(bdata, [6.5*cm, 21.2*cm], header_bg="#312E81", row_bgs=[colors.HexColor("#F5F3FF"), colors.white]))
        story.append(Spacer(1, 0.25*cm))
        if not next_df.empty:
            story.append(section("Jövő hét – strukturált napi terv", "#DCFCE7"))
            cols = [c for c in next_df.columns if c in ["Nap", "MD", "Fókusz", "Terhelés", "Javaslat", "Megjegyzés", "Cél"]]
            if not cols:
                cols = list(next_df.columns[:5])
            nd = [[P(c, head) for c in cols]]
            for _, r in next_df.head(8).iterrows():
                nd.append([P(r.get(c, ""), small) for c in cols])
            story.append(table(nd, [27.7*cm/len(cols)]*len(cols), header_bg="#166534", row_bgs=[colors.HexColor("#ECFDF5"), colors.white]))
        if not player_actions.empty:
            story.append(Spacer(1, 0.25*cm))
            story.append(section("Játékosszintű teendők", "#FEE2E2"))
            cols = list(player_actions.columns[:5])
            ad = [[P(c, head) for c in cols]]
            for _, r in player_actions.head(12).iterrows():
                ad.append([P(r.get(c, ""), small) for c in cols])
            story.append(table(ad, [27.7*cm/len(cols)]*len(cols), header_bg="#7F1D1D", row_bgs=[colors.HexColor("#FEF2F2"), colors.white]))


    def add_tactical_executive_page():
        def _pdf_tactical_key_numbers_summary(metrics: Dict[str, float]) -> str:
            """PDF-safe local helper. Avoids NameError if the UI helper is defined later or not available."""
            if not metrics:
                return "Nincs értelmezhető taktikai csapat KPI."
            label_map = {
                "possession_pct": "Labdabirtoklás",
                "shots": "Lövések",
                "xg": "xG",
                "entries_box": "Box entries",
                "key_passes": "Kulcspasszok",
                "corners": "Szögletek",
                "ppda": "PPDA",
                "pressing_success_pct": "Pressing %",
                "counterattacks": "Kontrák",
                "recoveries": "Labdaszerzések",
                "lost_balls": "Labdavesztések",
                "crosses": "Beadások",
            }
            parts = []
            for k, lab in label_map.items():
                v = metrics.get(k)
                if v not in [None, 0, 0.0, ""]:
                    try:
                        parts.append(f"{lab}: {float(v):.1f}")
                    except Exception:
                        parts.append(f"{lab}: {v}")
            return " | ".join(parts[:8]) if parts else "Nincs kiemelkedő taktikai KPI."

        story.append(section("Tactical Pro+ – saját csapat + ellenfél döntéselőkészítés", "#E0F2FE"))
        if not tactical_context:
            story.append(Paragraph(pdf_safe_text(
                "Ehhez a riporthoz nem volt taktikai PDF/Excel feltöltve. A vezetői értékelés GPS-only módban készült. "
                "Taktikai anyag feltöltése esetén ezen az oldalon megjelenik a saját csapat és ellenfél összevetése, "
                "a felismert taktikai témák, a Match Plan és az MD-terv taktikai indoklása."
            ), body))
            return

        status_rows = [
            [P("Elemzési szint", head), P(str(tactical_context.get("analysis_level", "n.a.")), small)],
            [P("Saját anyag", head), P(f"PDF: {'igen' if tactical_context.get('has_own_pdf') else 'nem'} | Team Excel: {'igen' if tactical_context.get('has_own_team_excel') else 'nem'} | Player Excel: {'igen' if tactical_context.get('has_own_player_excel') else 'nem'}", small)],
            [P("Ellenfél anyag", head), P(f"PDF: {'igen' if tactical_context.get('has_opp_pdf') else 'nem'} | Team Excel: {'igen' if tactical_context.get('has_opp_team_excel') else 'nem'} | Player Excel: {'igen' if tactical_context.get('has_opp_player_excel') else 'nem'}", small)],
            [P("Plan A", head), P(str(tactical_context.get("plan_a", "n.a.")), small)],
        ]
        story.append(table(status_rows, [6.0*cm, 21.7*cm], header_bg="#1E3A8A", row_bgs=[colors.HexColor("#EFF6FF"), colors.white]))
        story.append(Spacer(1, 0.20*cm))

        story.append(section("Fő taktikai kockázatok / fókuszok", "#FEE2E2"))
        risk_rows = [[P("#", head), P("Kockázat / fókusz", head)]]
        for i, r in enumerate((tactical_context.get("risks") or [])[:6], 1):
            risk_rows.append([P(str(i), small), P(str(r), small)])
        if len(risk_rows) == 1:
            risk_rows.append([P("1", small), P("Nincs taktikai input; GPS-alapú monitoring.", small)])
        story.append(table(risk_rows, [1.2*cm, 26.5*cm], header_bg="#7F1D1D", row_bgs=[colors.HexColor("#FEF2F2"), colors.white]))
        story.append(Spacer(1, 0.20*cm))

        story.append(section("Saját vs ellenfél – PDF témák és KPI-k", "#DCFCE7"))
        def _topic_names(rows):
            out = []
            for r in rows[:5]:
                out.append(str(r.get("Téma", r.get("label", ""))))
            return ", ".join([x for x in out if x]) or "n.a."
        rows = [
            [P("Oldal", head), P("Felismert PDF témák", head), P("Csapat KPI-k", head)],
            [P("Saját", small), P(_topic_names(tactical_context.get("own_topics", []) or []), small), P(_pdf_tactical_key_numbers_summary(tactical_context.get("own_team_metrics", {}) or {}), small)],
            [P("Ellenfél", small), P(_topic_names(tactical_context.get("opp_topics", []) or []), small), P(_pdf_tactical_key_numbers_summary(tactical_context.get("opp_team_metrics", {}) or {}), small)],
        ]
        story.append(table(rows, [3.0*cm, 12.5*cm, 12.2*cm], header_bg="#166534", row_bgs=[colors.HexColor("#ECFDF5"), colors.white]))
        story.append(Spacer(1, 0.20*cm))

        if tactical_context.get("md_plan"):
            story.append(section("Taktikailag támogatott MD-terv", "#EDE9FE"))
            md_rows = [[P("Nap", head), P("Fókusz", head), P("Indoklás", head)]]
            for a, b, c in (tactical_context.get("md_plan") or [])[:6]:
                md_rows.append([P(a, small), P(b, small), P(c, small)])
            story.append(table(md_rows, [4.0*cm, 9.5*cm, 14.2*cm], header_bg="#312E81", row_bgs=[colors.HexColor("#F5F3FF"), colors.white]))

    def add_methodology_page():
        story.append(section("Módszertani összefoglaló – hogyan számol az FPI?", "#DBEAFE"))
        intro = (
            "Az FPI döntéstámogató rendszer: a GPS-exportokból egységesíti a heti terhelési képet, "
            "kiemeli a kockázatokat és edzői/erőnléti javaslatokat ad. Nem helyettesíti a szakmai stábot; "
            "a végső döntés mindig edzői, erőnléti és orvosi kontroll mellett történik."
        )
        story.append(Paragraph(pdf_safe_text(intro), body))
        story.append(Spacer(1, 0.20*cm))

        meth_rows = [
            [P("Terület", head), P("FPI metodika", head)],
            [P("Adatimport", small), P("A Data/Adat lap elsődleges. A segédlapokat az app igyekszik kizárni. A Smart Mapper magyar és angol GPS oszlopneveket is kezel.", small)],
            [P("Dátum és hét", small), P("A Week Rescue Engine a dátumot időponttal vagy extra szöveggel együtt is értelmezi, majd ISO hétre csoportosít. Rövid dátumtartományból képződő irreálisan sok hét esetén védelmi újraértelmezést alkalmaz.", small)],
            [P("Kapusok", small), P("Ha van Poszt/Position oszlop, a kapusok automatikusan felismerhetők. Ha nincs, az app kézi kapusválasztást kér. A kapusok sprint/HSR értelmezése csökkentett súlyú.", small)],
            [P("Játékpercek", small), P("A meccsterhelésnél az app figyelembe veszi, hogy nem minden játékos játszik 90 percet. Ahol elérhető, per90 és csapatperc alapú normalizálást alkalmaz.", small)],
            [P("Edzés-meccs normalizálás", small), P("Az összevetés nem csak nyers csapatösszeg alapján történik, mert edzésen és meccsen eltérhet a játékosszám és a játékidő. A résztvevők száma és az időtartam is számít.", small)],
            [P("Sebességzónák", small), P("A 4-es és 5-ös zóna külön vagy összevont 4+5 exportként is kezelhető. Összevont oszlopnál az app HSR-ként használja az értéket.", small)],
            [P("High Efforts", small), P("Ha külön High Efforts oszlop van, azt használja. Ha nincs, gyorsulás/lassítás jellegű mutatókból becsült nagy intenzitású akciót képez.", small)],
            [P("Benchmark", small), P("A jelenlegi benchmark általános referencia. Későbbi verzióban korosztály, szint, poszt és játékmodell szerint finomíthető.", small)],
            [P("Mikrociklus", small), P("A múlt hét, aktuális hét és következő hét javaslatai a volumen, HSR, sprint, High Efforts, readiness és játékosszintű risk jelzések alapján készülnek.", small)],
            [P("Korlátok", small), P("Az eredmények adatminőségtől, GPS-exporttól és mappingtől függenek. Hibás vagy hiányos input esetén szakmai ellenőrzés szükséges.", small)],
        ]
        story.append(table(meth_rows, [5.2*cm, 22.5*cm], header_bg="#1E3A8A", row_bgs=[colors.HexColor("#EFF6FF"), colors.white]))
        story.append(Spacer(1, 0.20*cm))
        story.append(Paragraph(pdf_safe_text(f"Technikai státusz: {FPI_IMPORT_ENGINE_VERSION} | Smart Mapper: aktív | Week Rescue: aktív | Keeper Logic: aktív | Minutes Normalization: aktív | Microcycle Engine: aktív"), small))


    add_cover()
    if report_type in ["executive", "full"]:
        add_executive_page()
        story.append(PageBreak())
        add_tactical_executive_page()
    if report_type == "executive":
        pass
    elif report_type == "fitness":
        add_fitness_page()
    elif report_type == "microcycle":
        add_micro_page()
    elif report_type == "full":
        story.append(PageBreak()); add_fitness_page()
        story.append(PageBreak()); add_micro_page()
    else:
        add_executive_page()

    story.append(PageBreak())
    add_methodology_page()

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def _build_demo_tactical_context() -> Dict[str, object]:
    return {
        "version": "DEMO_TACTICAL_CONTEXT_V1",
        "analysis_level": "Level 4 – Full Intelligence DEMO",
        "has_own_pdf": True,
        "has_opp_pdf": True,
        "has_own_team_excel": True,
        "has_opp_team_excel": True,
        "has_own_player_excel": True,
        "has_opp_player_excel": True,
        "own_topics": [
            {"Téma": "Labdakihozatal / támadásépítés", "Bizonyosság": 88},
            {"Téma": "Presszing / letámadás", "Bizonyosság": 82},
        ],
        "opp_topics": [
            {"Téma": "Támadó átmenet / kontrák", "Bizonyosság": 91},
            {"Téma": "Szélső játék / oldali dominancia", "Bizonyosság": 78},
            {"Téma": "Pontrúgások", "Bizonyosság": 72},
        ],
        "own_team_metrics": {"possession_pct": 54, "shots": 12, "entries_box": 18, "pressing_success_pct": 62},
        "opp_team_metrics": {"counterattacks": 8, "crosses": 21, "corners": 6, "shots": 10},
        "plan_a": "BAT – középső blokk + gyors átmenet, jobb oldali biztosítással",
        "risks": [
            "Ellenfél-kontrák / gyors átmenetek kezelése",
            "Szélső játék és beadások elleni védekezés",
            "Pontrúgás-védekezés és második labdák",
        ],
        "md_plan": [
            ("MD-4", "Volumen + saját játékmodell", "Saját build-up és presszing trigger ismétlése."),
            ("MD-3", "HSR / sprint exponálás + átmenetek", "Ellenfél kontraveszély miatt átmeneti futások kontrollált terheléssel."),
            ("MD-2", "Kontrák elleni biztosítás + rest defense", "Ellenfél gyors átmeneti profilja miatt."),
            ("MD-1", "Aktiváció + pontrúgás", "Pontrúgás-veszély és frissesség kezelése."),
        ],
        "player_focus": ["Jobb oldali védő: beadások elleni 1v1 fókusz", "6-os: rest defense pozíció", "9-es: second ball célpont"],
    }


def build_fpi_sample_pdf_bytes(report_type: str = "full") -> Optional[bytes]:
    demo_raw = build_demo_performance_data()
    demo_df, _, missing = standardize_dataframe(demo_raw)
    if missing:
        return None
    demo_df = add_position_group(demo_df)
    latest = _fpi_latest_week(demo_df)
    return build_fpi_product_pdf_bytes(demo_df, latest, "Pressing", report_type=report_type, demo_label="MINTA RIPORT / Demo FC U19", tactical_context=_build_demo_tactical_context())

# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------
render_fpi_hero()


sample_pdf_bytes = build_fpi_sample_pdf_bytes("full")
sample_exec_pdf_bytes = build_fpi_sample_pdf_bytes("executive")
sample_fitness_pdf_bytes = build_fpi_sample_pdf_bytes("fitness")
sample_micro_pdf_bytes = build_fpi_sample_pdf_bytes("microcycle")
with st.container():
    st.markdown(
        """
        <div class="export-panel">
            <h3 style="margin-top:0;">📄 Minta riportcsomag klubdemóhoz</h3>
            <p style="color:#e0f2fe;">
                Ugyanaz a logika készíti, mint az éles exportot: vezetői 1-2 oldal, erőnléti szakmai PDF,
                mikrociklus PDF és teljes stábcsomag. Kamu játékosnevekkel, minta GPS-adatokkal.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if sample_pdf_bytes is not None:
        c_a, c_b, c_c, c_d = st.columns(4)
        with c_a:
            st.download_button(
                "⬇️ Minta vezetői PDF",
                data=sample_exec_pdf_bytes,
                file_name="fpi_minta_vezetoi_riport.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_sample_executive_v58",
            )
        with c_b:
            st.download_button(
                "⬇️ Minta erőnléti PDF",
                data=sample_fitness_pdf_bytes,
                file_name="fpi_minta_eronleti_riport.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_sample_fitness_v58",
            )
        with c_c:
            st.download_button(
                "⬇️ Minta mikrociklus PDF",
                data=sample_micro_pdf_bytes,
                file_name="fpi_minta_mikrociklus_riport.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_sample_micro_v58",
            )
        with c_d:
            st.download_button(
                "⬇️ Minta teljes csomag",
                data=sample_pdf_bytes,
                file_name="fpi_minta_teljes_stab_riportcsomag.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_sample_full_v58",
            )
    else:
        st.info("A minta PDF exporthoz a reportlab csomag szükséges.")



with st.sidebar:
    render_license_panel()
    st.divider()

    st.header("Adatfeltöltés")
    template_bytes = create_sample_input_template_bytes()
    if template_bytes is not None:
        st.download_button(
            "⬇️ Minta Excel sablon letöltése",
            data=template_bytes,
            file_name="performance_input_sablon.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="download_performance_input_template",
        )

    use_demo_data = st.toggle("Minta riport mintaadatokkal", value=st.session_state.get("use_demo_data", uploaded is None if 'uploaded' in globals() else True))
    uploaded = st.file_uploader("Saját GPS/terhelési Excel feltöltése", type=["xlsx", "xls"])
    if uploaded is not None:
        # Új fájl feltöltésekor ne maradjon bent a régi mapping vagy régi mapped dataframe.
        try:
            _bytes = uploaded.getvalue()
            _sig = hashlib.md5(_bytes).hexdigest()
        except Exception:
            _sig = str(getattr(uploaded, "name", "uploaded"))
        if st.session_state.get("active_upload_signature") != _sig:
            for _k in ["mapped_df_override", "manual_mapping", "mapper_selected_sheet", "last_raw_df", "manual_keeper_players", "manual_keeper_players_no_pos", "keeper_manual_override", "has_goalkeepers_without_position"]:
                st.session_state.pop(_k, None)
            st.session_state["active_upload_signature"] = _sig
    else:
        st.session_state.pop("active_upload_signature", None)
    st.caption("Demo módban saját adat is feltölthető, de limitált: 8 játékos / 3 hét / 5000 sor.")
    st.divider()
    st.markdown("**Fókusz:** vezetői riport, readiness, risk, edzői teendők.")

if uploaded is None and not use_demo_data:
    st.info("Tölts fel GPS/terhelési Excel fájlt, vagy kapcsold be a minta riportot.")
    st.stop()

if use_demo_data and uploaded is None:
    raw_df = build_demo_performance_data()
    selected_sheet = "Mintaadatok"
else:
    sheets = read_excel_all(uploaded)
    sheets = prepare_uploaded_sheets(sheets)
    sheet_names = list(sheets.keys())
    with st.sidebar:
        selected_sheet = st.selectbox("Melyik munkalapot használjuk?", sheet_names, index=0)
    if st.session_state.get("mapper_selected_sheet") != selected_sheet:
        st.session_state.pop("mapped_df_override", None)
        st.session_state.pop("manual_mapping", None)
        st.session_state["mapper_selected_sheet"] = selected_sheet
    raw_df = sheets[selected_sheet]

# Ha a felhasználó a mapperrel már alkalmazott kézi mappinget, azt használjuk.
if "mapped_df_override" in st.session_state and isinstance(st.session_state["mapped_df_override"], pd.DataFrame) and not st.session_state["mapped_df_override"].empty:
    df = st.session_state["mapped_df_override"].copy()
    mapping = st.session_state.get("manual_mapping", {})
    missing_core = []
else:
    df, mapping, missing_core = standardize_dataframe(raw_df)

st.session_state['last_raw_df'] = raw_df

if missing_core:
    st.error(f"Hiányzó alapmezők: {', '.join(missing_core)}")
    st.write("Oszlopmapping:", mapping)
    st.info("Nyisd le lent a Smart Excel Mappert. Most már nem állítjuk meg az appot, hogy kézzel javítható legyen a mapping.")
    # Minimális üres standard df, hogy a mapper és a nyers adatnézet elérhető maradjon.
    df = pd.DataFrame(columns=["player_name", "session_type", "start_time", "session_date", "week"])

df = add_position_group(df)
df = render_keeper_controls_and_apply(df)
df, demo_limit_info = apply_demo_limits(df)

if df.empty or "week" not in df.columns or df["week"].dropna().empty:
    st.warning("A fájl még nem értelmezhető elemzésre. Javítsd a kötelező mezőket a Smart Excel Mapperben.")
    render_emergency_mapper(raw_df, mapping, missing_core if "missing_core" in globals() else [])
    st.stop()

render_demo_limit_notice(demo_limit_info if 'demo_limit_info' in globals() else {})

weeks = sorted(df["week"].dropna().unique().tolist()) if "week" in df.columns else []
players = sorted(df["player_name"].dropna().unique().tolist()) if "player_name" in df.columns else []
session_types = sorted(df["session_type"].dropna().unique().tolist()) if "session_type" in df.columns else []

if not weeks or not players:
    render_emergency_mapper(raw_df, mapping if "mapping" in globals() else {}, missing_core if "missing_core" in globals() else [])
    st.stop()

with st.sidebar:
    if st.session_state.get("week_rescue_applied"):
        with st.expander("Hétfelismerés diagnosztika V6.2", expanded=False):
            st.json(st.session_state.get("week_rescue_applied"))

with st.sidebar:
    st.header("Szűrők")
    selected_week = st.selectbox("Hét", weeks, index=len(weeks) - 1 if weeks else 0, format_func=week_label_short)
    selected_playstyle = st.selectbox("Játékmodell", list(PLAYSTYLE_OPTIONS.keys()), index=0)
    st.caption(PLAYSTYLE_OPTIONS[selected_playstyle])
    selected_types = st.multiselect("Típus", session_types, default=session_types)
    selected_players = st.multiselect("Játékosok", players, default=players)

    st.header("Performance memória")
    if is_pro_mode():
        use_memory = st.checkbox("Korábbi mentett adatok bevonása", value=False)
        save_current_to_memory = st.button("Aktuális feltöltés mentése memoryba", use_container_width=True)
    else:
        use_memory = False
        save_current_to_memory = False
        st.caption("🔒 Performance memória Pro funkció.")

filtered = df[
    (df["week"] == selected_week)
    & (df["session_type"].isin(selected_types))
    & (df["player_name"].isin(selected_players))
]

if save_current_to_memory:
    ok, msg = save_to_memory(df)
    if ok:
        st.sidebar.success(msg)
    else:
        st.sidebar.error(msg)

analysis_df_full = merge_with_memory(df, use_memory)
analysis_base_df = analysis_df_full[analysis_df_full["player_name"].isin(selected_players)]
base_insights = team_insights(analysis_base_df, selected_week)
micro_insights = microcycle_insights(analysis_base_df, selected_week)
style_insights = playstyle_insights(analysis_base_df, selected_week, selected_playstyle)
pattern_insights = build_pattern_insights(analysis_base_df, selected_week)
readiness_score, readiness_components, readiness_reasons = calculate_readiness_score(analysis_base_df, selected_week, selected_playstyle)
weekly_fingerprints = build_weekly_fingerprints(analysis_base_df)
current_fp = weekly_fingerprints[weekly_fingerprints["week"] == selected_week]
periodization_type = current_fp["periodizacios_tipus"].iloc[0] if not current_fp.empty and "periodizacios_tipus" in current_fp.columns else "Nincs elég adat"
all_insights = sorted(base_insights + micro_insights + style_insights + pattern_insights, key=lambda x: SEVERITY_RANK.get(x.severity, 9))[:16]
coaching_priorities = build_adaptive_recommendations(all_insights, readiness_score, periodization_type, pattern_insights, selected_playstyle)
weekly_summary_text = build_weekly_summary(all_insights, selected_week, selected_playstyle)
all_insights = humanize_insights(all_insights)
coaching_priorities = humanize_priority_list(coaching_priorities)
weekly_summary_text = coach_friendly_phrase(weekly_summary_text)
weekly_summary_text += (
    f"\n\nMeccskészültség: {readiness_score}/100 ({score_to_label(readiness_score)})"
    f"\nPeriodizációs besorolás: {periodization_type}"
)
player_risk_df = calculate_player_risk(analysis_base_df, selected_week)
high_risk_count = int((player_risk_df["Kockázati szint"] == "Magas").sum()) if not player_risk_df.empty else 0
medium_risk_count = int((player_risk_df["Kockázati szint"] == "Közepes").sum()) if not player_risk_df.empty else 0
week_status_info = week_completeness_summary(analysis_base_df, selected_week)
past_week_review_df, past_week_review_text = build_past_week_review(
    analysis_base_df,
    selected_week,
    selected_playstyle,
)
current_remaining_plan_df, current_remaining_text = build_current_remaining_days_plan(
    analysis_base_df,
    selected_week,
    selected_playstyle,
    readiness_score,
    periodization_type,
    player_risk_df,
)
next_week_plan_df, next_week_plan_text = build_next_week_plan_v5(
    analysis_base_df,
    selected_week,
    selected_playstyle,
    readiness_score,
    periodization_type,
    player_risk_df,
    past_week_review_df,
    current_remaining_plan_df,
)
next_microcycle_plan_df = next_week_plan_df
player_next_actions_df = build_player_next_actions(player_risk_df, analysis_base_df, selected_week)
forward_summary_text = (
    "MÚLT HÉT -> ERRE A HÉTRE\n"
    + str(past_week_review_text)
    + "\n\nAKTUÁLIS HÉT -> HÁTRALÉVŐ NAPOK\n"
    + str(current_remaining_text)
    + "\n\nJÖVŐ HÉT\n"
    + str(next_week_plan_text)
)


def render_methodology_tab() -> None:
    """FPI V6.3 metodikai oldal – transzparens számítási és értelmezési logika."""
    st.markdown("## 📚 FPI metodika")
    st.markdown(
        """
        <div class="fpi-summary-card">
            <h3>Football Performance Intelligence – módszertani áttekintés</h3>
            <p>
            Az FPI döntéstámogató rendszer. Célja, hogy a GPS-exportokból gyorsan értelmezhető,
            edzői és erőnléti döntéseket támogató riportot készítsen. Nem helyettesíti a szakmai stábot,
            hanem rendszerezi az adatokat, kiemeli az eltéréseket és javaslatokat ad.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            """
            <div class="fpi-kpi-panel">
                <div class="label">Smart Mapper</div>
                <div class="value">Aktív</div>
                <div class="note">Magyar és angol GPS exportok oszlopfelismerése.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div class="fpi-kpi-panel">
                <div class="label">Week Rescue Engine</div>
                <div class="value">Aktív</div>
                <div class="note">Robusztus dátum- és hétfelismerés időponttal vagy extra szöveggel is.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            """
            <div class="fpi-kpi-panel">
                <div class="label">Keeper + Minutes Logic</div>
                <div class="value">Aktív</div>
                <div class="note">Kapusok, játékpercek, per90 és edzés-meccs normalizálás kezelése.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### 1. Adatimport és Smart Mapper")
    st.info(
        "Az app a Data/Adat lapot preferálja, a segédlapokat igyekszik kizárni az összesített adatból. "
        "A Smart Mapper magyar és angol oszlopneveket is kezel, például: Játékos neve / Player, "
        "Kezdési idő / Start Time, Teljes táv / Total Distance, High Efforts."
    )

    st.markdown("### 2. Dátum- és hétfelismerés")
    st.write(
        "A rendszer a dátumoszlopot robusztusan értelmezi. Támogatott példák: "
        "`2025-07-16`, `2025-07-16 09:38:13`, `16.07.2025`, `Training - 2025-07-16 17:00`. "
        "A csoportosítás ISO hét alapján történik, például `2025-W29`."
    )
    st.warning(
        "Ha rövid, néhány napos dátumtartományból irreálisan sok hét keletkezne, a Week Rescue Engine "
        "védelmi logikája újraértelmezi a heteket, és diagnosztikát ad az oldalsávban."
    )

    st.markdown("### 3. Kapuskezelés")
    st.write(
        "Ha van Poszt/Position oszlop, az app automatikusan keresi a kapusokat "
        "(`GK`, `Goalkeeper`, `Kapus`, `KAPUS`). Ha nincs posztoszlop, az oldalsávban kézzel lehet megadni, "
        "hogy vannak-e kapusok, és ki(k) azok."
    )
    st.write(
        "A kapusok nem ugyanazzal a logikával értékelendők, mint a mezőnyjátékosok. "
        "A sprint- és HSR-alapú mutatók csökkentett súllyal szerepelnek, míg a teljes terhelés, "
        "High Efforts és Training Load értelmezése megmarad."
    )

    st.markdown("### 4. Játékpercek és per90 normalizálás")
    st.write(
        "A rendszer figyelembe veszi, hogy egy meccsen nem minden játékos 90 percet játszik. "
        "A 14 pályára lépő játékos terhelése nem `14×90 perc`. Ahol elérhető az időtartam/játékperc, "
        "az app per90 és csapatperc alapú normalizálást is használ."
    )

    st.markdown("### 5. Edzés–meccs összevetés")
    st.write(
        "Az edzés és a meccs összehasonlítása nem pusztán nyers csapatösszeg alapján történik, "
        "mert edzésen 18–22 játékos, meccsen pedig 13–16 játékos is szerepelhet eltérő percekkel. "
        "Az FPI ezért figyelembe veszi a résztvevők számát, az időtartamot és az egy főre jutó terhelést."
    )

    st.markdown("### 6. Sebességzónák és High Efforts")
    st.write(
        "A 4-es és 5-ös sebességzónát az app külön kezeli, de összevont `4+5` export esetén is használható. "
        "Ha a High Efforts mező külön szerepel az exportban, azt használja; ha nem, gyorsulás/lassítás jellegű "
        "mutatókból becsült nagy intenzitású terhelést képez."
    )

    st.markdown("### 7. Benchmarkok és readiness")
    st.write(
        "A benchmarkok jelenleg általános referenciaértékek. Későbbi verzióban korosztály, szint, poszt és "
        "játékmodell szerint finomíthatók. A readiness és risk pontszámok döntéstámogatók, nem orvosi diagnózisok."
    )

    st.markdown("### 8. Mikrociklus motor")
    st.write(
        "A mikrociklus modul három szintet kezel: múlt hét értékelése, aktuális hét eddig feltöltött napjai, "
        "és jövő heti MD-bontású javaslat. A javaslatok a heti volumenből, HSR/sprint terhelésből, High Effortsből, "
        "játékosszintű eltérésekből és kockázati jelzésekből épülnek."
    )

    st.markdown("### 9. Korlátok")
    st.error(
        "Az FPI nem helyettesíti a vezetőedzőt, erőnléti edzőt, orvosi stábot vagy a klub szakmai döntéseit. "
        "Az app adatminőségtől függ: hibás GPS-export, rossz mapping vagy hiányzó játékpercek esetén az értelmezést "
        "szakmai kontrollal kell kezelni."
    )

    st.markdown("### 10. Technikai státusz")
    st.json({
        "FPI_VERSION": FPI_IMPORT_ENGINE_VERSION,
        "Smart Mapper": "aktív",
        "Week Rescue Engine": "aktív",
        "Keeper Logic": "aktív",
        "Minutes Normalization": "aktív",
        "Microcycle Engine": "aktív",
        "Benchmark Engine": "aktív",
        "Tactical Pro+": "aktív",
    })


# =========================================================
# TACTICAL PRO+ MERGE MODULE V7.0
# PDF: automatikus HU/EN témakinyerés
# Excel: Smart Tactical Mapper csapat- és játékosstatisztikákra
# Adaptive Intelligence: ha van taktikai adat, figyelembe veszi; ha nincs, GPS-only módban fut
# =========================================================

TACTICAL_PRO_VERSION = "TACTICAL_PRO_MERGED_V070_2026_06_17"

TACTICAL_TOPIC_TAGS_FPI = {
    "formation": {"label": "Formáció / alapfelállás", "keywords": ["formation", "shape", "system", "line-up", "lineup", "starting xi", "formáció", "felállás", "játékrendszer", "4-4-2", "4-2-3-1", "4-3-3", "3-5-2", "3-4-3", "5-3-2", "5-4-1"]},
    "build_up": {"label": "Labdakihozatal / támadásépítés", "keywords": ["build-up", "build up", "first phase", "second phase", "goal kick", "short goal kick", "progression", "progressive pass", "third man", "pivot", "half-space", "switch of play", "labdakihozatal", "támadásépítés", "építkezés", "kirúgás", "progresszív passz", "harmadik ember", "félterület", "oldalváltás"]},
    "direct_play": {"label": "Direkt játék / hosszú labda", "keywords": ["direct play", "long ball", "long pass", "second ball", "aerial duel", "target man", "vertical", "direct attack", "direkt játék", "hosszú labda", "második labda", "felívelés", "fejpárbaj", "céljátékos", "vertikális"]},
    "pressing": {"label": "Letámadás / presszing", "keywords": ["press", "pressing", "high press", "mid press", "low press", "counterpress", "ppda", "pressure", "pressing trigger", "trap", "high recovery", "letámadás", "presszing", "magas letámadás", "visszatámadás", "nyomás", "trigger", "csapda", "magas labdaszerzés"]},
    "defensive_block": {"label": "Védekezési blokk / blokkmagasság", "keywords": ["low block", "mid block", "middle block", "high block", "defensive block", "compact", "defensive line", "line height", "deep defending", "mély blokk", "középső blokk", "magas blokk", "védekezési blokk", "kompakt", "védelmi vonal", "blokkmagasság", "mély védekezés"]},
    "transition_attack": {"label": "Támadó átmenet / kontrák", "keywords": ["transition", "attacking transition", "counterattack", "counter attack", "counter-attacks", "fast attack", "quick attack", "after regain", "after winning", "átmenet", "támadó átmenet", "kontra", "kontratámadás", "gyors támadás", "labdaszerzés után", "labdanyerés után"]},
    "transition_defense": {"label": "Védekező átmenet / rest defense", "keywords": ["defensive transition", "after losing", "after loss", "rest defense", "counter prevention", "cover behind", "védekező átmenet", "labdavesztés után", "kontrák elleni védekezés", "átmeneti védekezés", "biztosítás", "visszarendeződés"]},
    "chance_creation": {"label": "Helyzetkialakítás / támadóharmad", "keywords": ["chance creation", "key pass", "shot assist", "box entry", "penalty area", "final third", "through ball", "cutback", "cross", "xg", "expected goals", "helyzetkialakítás", "kulcspassz", "box entry", "tizenhatos", "támadóharmad", "mélységi passz", "visszagurítás", "beadás", "várható gól"]},
    "wide_play": {"label": "Szélső játék / oldali dominancia", "keywords": ["wide play", "wing", "flank", "left side", "right side", "overlap", "underlap", "fullback", "crossing", "side dominance", "szélső játék", "szél", "bal oldal", "jobb oldal", "átfedés", "aláfutás", "beadás", "oldali dominancia"]},
    "central_play": {"label": "Középső játék / félterületek", "keywords": ["central", "middle", "half-space", "between the lines", "pocket", "zone 14", "inside channel", "central overload", "középen", "középső", "félterület", "vonalak között", "zseb", "14-es zóna", "belső csatorna"]},
    "set_pieces": {"label": "Pontrúgások", "keywords": ["set piece", "set pieces", "corner", "corner kick", "free kick", "throw-in", "attacking corner", "defensive corner", "near post", "far post", "aerial", "header", "pontrúgás", "pontrúgások", "szöglet", "szabadrúgás", "bedobás", "rövid oldal", "hosszú oldal", "fejpárbaj", "fejes"]},
    "key_players": {"label": "Kulcsjátékosok", "keywords": ["key player", "danger man", "main threat", "top scorer", "creator", "playmaker", "progressor", "target man", "dribbler", "1v1", "finisher", "kulcsjátékos", "veszélyes játékos", "fő veszély", "gólkirály", "kreatív játékos", "irányító", "progresszor", "céljátékos", "cselező", "egy az egy", "befejező"]},
    "weakness_risk": {"label": "Gyengeségek / kockázatok", "keywords": ["weakness", "weaknesses", "risk", "risks", "vulnerable", "vulnerability", "exposed", "space behind", "gap", "mistake", "error", "turnover", "lost balls", "danger", "threat", "gyengeség", "gyengeségek", "kockázat", "sebezhető", "sebezhetőség", "nyitott terület", "mögötti terület", "rés", "hiba", "labdavesztés", "veszély"]},
    "strength": {"label": "Erősségek", "keywords": ["strength", "strengths", "strong", "advantage", "edge", "dominant", "effective", "efficient", "erősség", "erősségek", "erős", "előny", "domináns", "hatékony", "kiemelkedő"]},
    "recommendation": {"label": "Javaslat / meccsterv", "keywords": ["recommendation", "recommend", "should", "game plan", "match plan", "plan a", "plan b", "solution", "exploit", "avoid", "focus", "priority", "target", "javaslat", "ajánlás", "meccsterv", "mérkőzésterv", "terv a", "terv b", "megoldás", "kihasználni", "elkerülni", "fókusz", "prioritás"]},
}

TACTICAL_TEAM_ALIASES_FPI = {
    "possession_pct": ["ball possession", "possession", "possession %", "labdabirtoklás", "labdabirtoklás %", "birtoklás"],
    "shots": ["shots", "total shots", "attempts", "lövés", "lövések", "összes lövés"],
    "xg": ["xg", "expected goals", "várható gól", "várható gólok"],
    "entries_box": ["box entries", "entries into box", "penalty box entries", "tizenhatosba belépés", "büntetőterület", "16-osba belépés"],
    "final_third_entries": ["final third entries", "entries to final third", "támadóharmad belépések", "utolsó harmad"],
    "key_passes": ["key passes", "shot assists", "chances created", "kulcspassz", "helyzetkialakítás", "lövést előkészítő"],
    "corners": ["corners", "corner kicks", "szögletek", "szöglet"],
    "ppda": ["ppda", "passes allowed per defensive action", "passz engedett védekező akciónként"],
    "pressing_success_pct": ["pressing success", "successful pressing", "team pressing successful", "letámadás sikeresség", "presszing sikeresség"],
    "passes_accurate_pct": ["pass accuracy", "passes accurate", "passing accuracy", "passzpontosság", "átadáspontosság"],
    "crosses": ["crosses", "successful crosses", "beadások", "beadás"],
    "recoveries": ["recoveries", "ball recoveries", "regains", "labdaszerzések", "visszaszerzések"],
    "lost_balls": ["lost balls", "losses", "turnovers", "labdavesztések", "elvesztett labdák"],
    "counterattacks": ["counterattacks", "counter attacks", "fast attacks", "kontrák", "kontratámadások", "gyors támadások"],
}

TACTICAL_PLAYER_ALIASES_FPI = {
    "player": ["player", "player name", "name", "játékos", "játékos neve", "név"],
    "position": ["position", "pos", "role", "poszt", "pozíció"],
    "minutes_played": ["minutes played", "minutes", "mins", "played", "játékperc", "percek", "játszott perc"],
    "passes": ["passes", "pass", "passzok", "passz"],
    "progressive_passes": ["progressive passes", "progressive pass", "progresszív passz", "előrehaladó passz"],
    "key_passes": ["key passes", "shot assists", "kulcspassz", "helyzetkialakítás"],
    "shots": ["shots", "attempts", "lövések", "lövés"],
    "xg": ["xg", "expected goals", "várható gól"],
    "assists": ["assists", "assist", "gólpassz"],
    "recoveries": ["recoveries", "ball recoveries", "labdaszerzések"],
    "interceptions": ["interceptions", "interception", "közbelépés", "labdaszerzés"],
    "defensive_challenges": ["defensive challenges", "defensive duels", "védekező párharc", "párharc"],
    "crosses": ["crosses", "beadások", "beadás"],
}

def _fpi_tactical_norm(x: object) -> str:
    s = unicodedata.normalize("NFKD", str(x or "").lower().replace("\u00ad", " "))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9%]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def _fpi_tactical_score(col: object, aliases: List[str], field: str = "") -> int:
    src = _fpi_tactical_norm(col)
    if not src:
        return 0
    best = 0
    for alias in aliases + [field]:
        a = _fpi_tactical_norm(alias)
        if not a:
            continue
        if src == a:
            best = max(best, 100)
        elif src.replace(" ", "") == a.replace(" ", ""):
            best = max(best, 96)
        elif a in src or src in a:
            best = max(best, 86 if len(a) >= 4 else 70)
        else:
            stoks, atoks = set(src.split()), set(a.split())
            if stoks and atoks:
                best = max(best, int(len(stoks & atoks) / max(1, len(atoks)) * 78))
    return int(best)

def _fpi_tactical_suggest_mapping(df: pd.DataFrame, aliases: Dict[str, List[str]]) -> Dict[str, Optional[str]]:
    mapping, used = {}, set()
    for field, als in aliases.items():
        scored = sorted([(_fpi_tactical_score(c, als, field), c) for c in df.columns if c not in used], reverse=True, key=lambda x: x[0])
        if scored and scored[0][0] >= 58:
            mapping[field] = scored[0][1]
            used.add(scored[0][1])
        else:
            mapping[field] = None
    return mapping

def _fpi_tactical_detect_header(raw: pd.DataFrame, aliases: Dict[str, List[str]]) -> int:
    all_aliases = [a for als in aliases.values() for a in als]
    best_i, best = 0, -999
    for i in range(min(40, len(raw))):
        cells = [str(v).strip() for v in raw.iloc[i].tolist() if str(v).strip().lower() not in ["", "nan", "none"]]
        if not cells:
            continue
        joined = _fpi_tactical_norm(" | ".join(cells))
        score = sum(4 for a in all_aliases if _fpi_tactical_norm(a) and _fpi_tactical_norm(a) in joined)
        numeric_like = sum(1 for c in cells if re.fullmatch(r"-?\d+(?:[.,]\d+)?%?", c))
        text_like = len(cells) - numeric_like
        if text_like >= 3:
            score += 8
        if numeric_like > text_like:
            score -= 8
        if score > best:
            best_i, best = i, score
    return best_i

def _fpi_tactical_read_best_excel(file_bytes: bytes, aliases: Dict[str, List[str]]) -> Tuple[pd.DataFrame, str, List[dict]]:
    debug = []
    try:
        xls = pd.ExcelFile(io.BytesIO(file_bytes))
    except Exception as e:
        st.warning(f"Taktikai Excel nem olvasható: {e}")
        return pd.DataFrame(), "", debug
    best_df, best_sheet, best_score = pd.DataFrame(), "", -999
    for sheet in xls.sheet_names:
        try:
            raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet, header=None)
        except Exception:
            continue
        if raw.empty:
            continue
        h = _fpi_tactical_detect_header(raw, aliases)
        cols = [str(x).strip() if str(x).strip().lower() not in ["", "nan", "none"] else f"col_{j+1}" for j, x in enumerate(raw.iloc[h].tolist())]
        df2 = raw.iloc[h + 1:].copy()
        df2.columns = cols
        df2 = df2.dropna(how="all")
        score = 0
        for field, als in aliases.items():
            if max([_fpi_tactical_score(c, als, field) for c in df2.columns] or [0]) >= 58:
                score += 10
        if "main statistics" in _fpi_tactical_norm(sheet):
            score += 20
        if score > best_score:
            best_df, best_sheet, best_score = df2, sheet, score
        debug.append({"sheet": sheet, "header_row": h, "score": score, "columns": cols[:25]})
    return best_df, best_sheet, debug

def _fpi_tactical_mapper_ui(uploaded_file, aliases: Dict[str, List[str]], state_prefix: str, title: str) -> Tuple[pd.DataFrame, Dict[str, Optional[str]]]:
    if uploaded_file is None:
        return pd.DataFrame(), {}
    file_bytes = uploaded_file.getvalue()
    df2, sheet_name, debug = _fpi_tactical_read_best_excel(file_bytes, aliases)
    if df2.empty:
        return df2, {}
    signature = hashlib.md5(file_bytes).hexdigest()[:12]
    map_key = f"{state_prefix}_tactical_mapping"
    sig_key = f"{state_prefix}_tactical_sig"
    if st.session_state.get(sig_key) != signature:
        st.session_state[sig_key] = signature
        st.session_state[map_key] = _fpi_tactical_suggest_mapping(df2, aliases)
    mapping = dict(st.session_state.get(map_key, _fpi_tactical_suggest_mapping(df2, aliases)))
    cols = [""] + [str(c) for c in df2.columns]
    with st.expander(f"🧭 {title} – Smart Tactical Mapper", expanded=False):
        st.caption(f"Felismert munkalap: {sheet_name or 'n.a.'}")
        grid = st.columns(3)
        for i, field in enumerate(aliases.keys()):
            default = mapping.get(field) or ""
            with grid[i % 3]:
                mapping[field] = st.selectbox(field, cols, index=cols.index(default) if default in cols else 0, key=f"{state_prefix}_{field}_{signature}") or None
        st.session_state[map_key] = mapping
        q = [{"Mező": k, "Oszlop": v or "", "Bizonyosság": _fpi_tactical_score(v, aliases[k], k) if v else 0} for k, v in mapping.items()]
        st.dataframe(pd.DataFrame(q), use_container_width=True)
        if st.checkbox("Előnézet", key=f"{state_prefix}_preview_{signature}"):
            st.dataframe(df2.head(15), use_container_width=True)
        if st.checkbox("Munkalap diagnosztika", key=f"{state_prefix}_debug_{signature}"):
            st.json(debug)
    return df2, mapping

def _fpi_tactical_numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", ".", regex=False).str.replace("%", "", regex=False), errors="coerce")

def _fpi_tactical_parse_team_excel(df2: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> Dict[str, float]:
    metrics = {}
    if df2 is None or df2.empty:
        return metrics
    total_row = None
    try:
        total_mask = df2.iloc[:, 0].astype(str).str.strip().str.lower().eq("total")
        if total_mask.any():
            total_row = df2[total_mask].iloc[0]
    except Exception:
        pass
    avg_fields = {"possession_pct", "pressing_success_pct", "passes_accurate_pct", "ppda", "xg"}
    for field, col in mapping.items():
        if not col or col not in df2.columns:
            continue
        if total_row is not None:
            val = coerce_cell_value(total_row.get(col)) if "coerce_cell_value" in globals() else total_row.get(col)
            metrics[field] = float(val) if isinstance(val, (int, float, np.number)) else float(pd.to_numeric(str(val).replace(",", ".").replace("%", ""), errors="coerce") or 0)
        else:
            nums = _fpi_tactical_numeric(df2[col]).dropna()
            if nums.empty:
                continue
            metrics[field] = float(nums.mean() if field in avg_fields else nums.sum())
    return metrics

def _fpi_tactical_parse_player_excel(df2: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> Dict[str, pd.DataFrame]:
    empty = {"creators": pd.DataFrame(), "progressors": pd.DataFrame(), "build_up": pd.DataFrame(), "defenders": pd.DataFrame(), "duel_players": pd.DataFrame()}
    if df2 is None or df2.empty:
        return empty
    out = pd.DataFrame()
    for field, col in mapping.items():
        if col and col in df2.columns:
            out[field] = df2[col]
    if "player" not in out.columns:
        return empty
    if "minutes_played" not in out.columns:
        out["minutes_played"] = 999
    out["player"] = out["player"].astype(str).str.strip()
    out["minutes_played"] = _fpi_tactical_numeric(out["minutes_played"]).fillna(0)
    out = out[out["minutes_played"] >= 1].copy()
    for c in ["passes", "progressive_passes", "key_passes", "interceptions", "defensive_challenges", "shots", "xg", "assists", "recoveries", "crosses"]:
        out[c] = _fpi_tactical_numeric(out[c]).fillna(0) if c in out.columns else 0
    if "position" not in out.columns:
        out["position"] = ""
    return {
        "creators": out.sort_values("key_passes", ascending=False)[["player", "position", "key_passes"]].head(5).reset_index(drop=True),
        "progressors": out.sort_values("progressive_passes", ascending=False)[["player", "position", "progressive_passes"]].head(5).reset_index(drop=True),
        "build_up": out.sort_values("passes", ascending=False)[["player", "position", "passes"]].head(5).reset_index(drop=True),
        "defenders": out.sort_values("interceptions", ascending=False)[["player", "position", "interceptions"]].head(5).reset_index(drop=True),
        "duel_players": out.sort_values("defensive_challenges", ascending=False)[["player", "position", "defensive_challenges"]].head(5).reset_index(drop=True),
    }

def _fpi_tactical_extract_pdf_text(files: List[object], max_pages: int = 80) -> Tuple[str, List[dict]]:
    pages, texts = [], []
    if pdfplumber is None:
        return "", pages
    for f in files or []:
        if f is None:
            continue
        try:
            with pdfplumber.open(io.BytesIO(f.getvalue())) as pdf:
                for i, p in enumerate(pdf.pages[:max_pages]):
                    txt = p.extract_text(x_tolerance=1, y_tolerance=3) or ""
                    if txt.strip():
                        pages.append({"file": getattr(f, "name", "pdf"), "page": i + 1, "text": txt})
                        texts.append(txt)
        except Exception:
            continue
    return "\n\n".join(texts), pages

def _fpi_tactical_context_lines(text: str, topic: str, limit: int = 7) -> List[str]:
    cfg = TACTICAL_TOPIC_TAGS_FPI.get(topic, {})
    kws = [_fpi_tactical_norm(k) for k in cfg.get("keywords", [])]
    lines = [x.strip() for x in str(text or "").splitlines() if len(x.strip()) >= 4]
    out = []
    for i, line in enumerate(lines):
        ln = _fpi_tactical_norm(line)
        if any(k and k in ln for k in kws):
            for j in range(max(0, i - 1), min(len(lines), i + 2)):
                out.append(lines[j])
        if len(dict.fromkeys(out)) >= limit:
            break
    return list(dict.fromkeys(out))[:limit]

def _fpi_tactical_pdf_insights(text: str) -> Dict[str, object]:
    rows = []
    blocks = {}
    for key, cfg in TACTICAL_TOPIC_TAGS_FPI.items():
        lines = _fpi_tactical_context_lines(text, key, limit=8)
        hit = sum(1 for line in lines for kw in cfg["keywords"] if _fpi_tactical_norm(kw) in _fpi_tactical_norm(line))
        conf = min(100, hit * 15 + len(lines) * 5)
        rows.append({"Téma": cfg["label"], "Kulcs": key, "Találat": hit, "Bizonyosság": conf, "Minta": " | ".join(lines[:2])})
        blocks[key] = lines
    detected = [r for r in rows if r["Találat"] > 0 or r["Minta"]]
    detected = sorted(detected, key=lambda x: x["Bizonyosság"], reverse=True)
    formation_match = re.search(r"\b([3-5]-[1-5]-[1-5](?:-[1-3])?)\b", text or "")
    return {"formation": formation_match.group(1) if formation_match else "n.a.", "blocks": blocks, "topics": detected[:12], "raw_text_len": len(text or "")}

def _fpi_analysis_level(has_gps: bool, has_pdf: bool, has_team_excel: bool, has_player_excel: bool) -> Tuple[int, str]:
    if has_gps and has_pdf and has_team_excel and has_player_excel:
        return 4, "Full Intelligence – GPS + taktikai PDF + csapat Excel + játékos Excel"
    if has_gps and has_pdf and has_team_excel:
        return 3, "GPS + Tactical Team Intelligence"
    if has_gps and has_pdf:
        return 2, "GPS + Tactical PDF Intelligence"
    if has_gps:
        return 1, "GPS Only – Performance Intelligence"
    return 0, "Nincs elegendő adat"

def _fpi_build_adaptive_match_training_plan(gps_context: Dict[str, object], tactical: Dict[str, object]) -> Dict[str, object]:
    readiness = int(gps_context.get("readiness_score", 70) or 70)
    playstyle = gps_context.get("playstyle", "Kiegyensúlyozott")
    priorities = gps_context.get("priorities", []) or []
    pdfi = tactical.get("pdf_insights") or {}
    team_metrics = tactical.get("team_metrics") or {}
    player_tables = tactical.get("player_tables") or {}
    blocks = pdfi.get("blocks", {}) if isinstance(pdfi, dict) else {}

    risks = []
    if blocks.get("transition_attack"):
        risks.append("Ellenfél-kontrák / gyors átmenetek kezelése")
    if blocks.get("set_pieces"):
        risks.append("Pontrúgás-védekezés és második labdák")
    if blocks.get("wide_play"):
        risks.append("Szélső játék, beadások, oldali túlterhelések")
    if blocks.get("pressing"):
        risks.append("Presszing kijátszása és első passzsor döntései")
    if team_metrics.get("counterattacks", 0) > 0:
        risks.append("Adat alapján kimutatható kontraveszély")
    if not risks:
        risks.append("GPS-alapú terhelési és readiness kockázatok")

    plan_a = "KIE – Kiegyensúlyozott" if readiness >= 65 else "BAT – középső blokk + átmenet"
    if blocks.get("transition_attack") or team_metrics.get("counterattacks", 0) > 0:
        plan_a = "BAT – középső blokk + átmenet"
    if blocks.get("defensive_block") and blocks.get("direct_play"):
        plan_a = "POZ/KIE – türelmes labdabirtoklás + biztosítás"
    if blocks.get("pressing") and readiness >= 70:
        plan_a = "PRS – presszing + átmenet, de kontrolláltan"

    md_plan = []
    if readiness < 55:
        md_plan = [
            ("MD+1/MD-5", "Regeneráció + egyéni monitoring", "Magasabb kockázat miatt terheléskontroll."),
            ("MD-4", "Technikai/taktikai volumen közepes intenzitással", "Kerüljük a túl nagy sprint/HSR csúcsot."),
            ("MD-3", "Rövid specifikus exponálás", "Csak célzott HSR/sprint inger, alacsony volumen."),
            ("MD-2", "Meccsterv + taktikai ismétlés", "Ellenfél-specifikus fókusz alacsonyabb fizikai kockázattal."),
            ("MD-1", "Aktiváció", "Frissítés, döntési gyorsaság, pontrúgás."),
        ]
    else:
        md_plan = [
            ("MD+1/MD-5", "Regeneráció / alacsony intenzitás", "Előző terhelés visszarendezése."),
            ("MD-4", "Volumen + játékmodell", "Stabil csapatvolumen és pozíciós/taktikai alapok."),
            ("MD-3", "HSR / sprint exponálás", "Meccsintenzitás előkészítése."),
            ("MD-2", "Ellenfél-specifikus taktikai nap", ", ".join(risks[:2]) if risks else "Meccsterv."),
            ("MD-1", "Aktiváció + pontrúgások", "Frissítés, gyors döntések, fix helyzetek."),
        ]
    if blocks.get("transition_attack"):
        md_plan[3] = ("MD-2", "Kontrák elleni biztosítás + rest defense", "Az ellenfél átmeneti veszélyei miatt.")
    if blocks.get("set_pieces"):
        md_plan[-1] = ("MD-1", "Aktiváció + pontrúgás fókusz", "PDF alapján pontrúgás téma megjelent.")

    player_focus = []
    if isinstance(player_tables, dict):
        for key, label in [("creators", "kreatív játékos"), ("progressors", "progresszor"), ("duel_players", "párharcerős játékos")]:
            dfp = player_tables.get(key)
            if isinstance(dfp, pd.DataFrame) and not dfp.empty and "player" in dfp.columns:
                player_focus.append(f"{dfp.iloc[0]['player']} – {label}")
    if not player_focus and priorities:
        for p in priorities[:3]:
            if isinstance(p, dict):
                player_focus.append(p.get("Teendő", p.get("Cím", "Játékosszintű monitoring")))

    return {"analysis_level": tactical.get("analysis_level_label", "GPS Only"), "plan_a": plan_a, "risks": list(dict.fromkeys(risks))[:5], "md_plan": md_plan, "player_focus": player_focus[:5]}

def _merge_tactical_pdf_insights(own_insights: Dict[str, object], opp_insights: Dict[str, object]) -> Dict[str, object]:
    """Saját + ellenfél taktikai PDF insightok összefűzése úgy, hogy a régi logika se vesszen el."""
    merged_blocks = {}
    for key in TACTICAL_TOPIC_TAGS_FPI.keys():
        own_lines = ((own_insights or {}).get("blocks") or {}).get(key, []) or []
        opp_lines = ((opp_insights or {}).get("blocks") or {}).get(key, []) or []
        merged_blocks[key] = [f"Saját: {x}" for x in own_lines[:4]] + [f"Ellenfél: {x}" for x in opp_lines[:4]]

    topics = []
    for source_label, src in [("Saját", own_insights or {}), ("Ellenfél", opp_insights or {})]:
        for row in src.get("topics", []) or []:
            r = dict(row)
            r["Forrás"] = source_label
            topics.append(r)
    topics = sorted(topics, key=lambda x: x.get("Bizonyosság", 0), reverse=True)

    formation = (opp_insights or {}).get("formation") or (own_insights or {}).get("formation") or "n.a."
    return {
        "formation": formation,
        "blocks": merged_blocks,
        "topics": topics[:18],
        "raw_text_len": int((own_insights or {}).get("raw_text_len", 0) or 0) + int((opp_insights or {}).get("raw_text_len", 0) or 0),
        "own": own_insights or {},
        "opponent": opp_insights or {},
    }

def _tactical_key_numbers_summary(metrics: Dict[str, float]) -> str:
    if not metrics:
        return "Nincs értelmezhető taktikai csapat KPI."
    label_map = {
        "possession_pct": "Labdabirtoklás",
        "shots": "Lövések",
        "xg": "xG",
        "entries_box": "Box entries",
        "key_passes": "Kulcspasszok",
        "corners": "Szögletek",
        "ppda": "PPDA",
        "pressing_success_pct": "Pressing %",
        "counterattacks": "Kontrák",
        "recoveries": "Labdaszerzések",
        "lost_balls": "Labdavesztések",
    }
    parts = []
    for k, lab in label_map.items():
        v = metrics.get(k)
        if v not in [None, 0, 0.0, ""]:
            try:
                parts.append(f"{lab}: {float(v):.1f}")
            except Exception:
                parts.append(f"{lab}: {v}")
    return " | ".join(parts[:8]) if parts else "Nincs kiemelkedő taktikai KPI."

def _build_tactical_executive_context(gps_context: Dict[str, object], tactical_ctx: Dict[str, object], plan: Dict[str, object]) -> Dict[str, object]:
    own = tactical_ctx.get("own", {}) if tactical_ctx else {}
    opp = tactical_ctx.get("opponent", {}) if tactical_ctx else {}
    analysis_level = tactical_ctx.get("analysis_level_label", "GPS Only")
    return {
        "version": TACTICAL_PRO_VERSION,
        "analysis_level": analysis_level,
        "has_own_pdf": bool((own.get("pdf_insights") or {}).get("raw_text_len", 0)),
        "has_opp_pdf": bool((opp.get("pdf_insights") or {}).get("raw_text_len", 0)),
        "has_own_team_excel": bool(own.get("team_metrics")),
        "has_opp_team_excel": bool(opp.get("team_metrics")),
        "has_own_player_excel": bool(own.get("player_tables")),
        "has_opp_player_excel": bool(opp.get("player_tables")),
        "own_topics": ((own.get("pdf_insights") or {}).get("topics") or [])[:8],
        "opp_topics": ((opp.get("pdf_insights") or {}).get("topics") or [])[:8],
        "own_team_metrics": own.get("team_metrics", {}),
        "opp_team_metrics": opp.get("team_metrics", {}),
        "plan_a": plan.get("plan_a", "KIE – Kiegyensúlyozott"),
        "risks": plan.get("risks", []),
        "md_plan": plan.get("md_plan", []),
        "player_focus": plan.get("player_focus", []),
    }

def render_tactical_pro_module(gps_context: Dict[str, object]) -> None:
    st.markdown("## 🧠 Tactical Pro+ / Adaptive Intelligence")
    st.markdown(
        "GPS-alapon önállóan is működik. Ha saját csapatról és/vagy ellenfélről taktikai PDF-et, "
        "csapat Excelt vagy játékos Excelt töltesz fel, azokat beépíti a meccstervbe és a heti edzésterv-javaslatba."
    )

    with st.expander("📥 Taktikai inputok – saját csapat és ellenfél", expanded=True):
        own_col, opp_col = st.columns(2)
        with own_col:
            st.markdown("### Saját csapat")
            own_pdfs = st.file_uploader("Saját taktikai PDF-ek", type=["pdf"], accept_multiple_files=True, key="tactical_pro_own_pdfs")
            own_team_xlsx = st.file_uploader("Saját csapatstatisztika Excel", type=["xlsx", "xls"], key="tactical_pro_own_team_xlsx")
            own_player_xlsx = st.file_uploader("Saját játékosstatisztika Excel", type=["xlsx", "xls"], key="tactical_pro_own_player_xlsx")
        with opp_col:
            st.markdown("### Ellenfél")
            opp_pdfs = st.file_uploader("Ellenfél taktikai PDF-ek", type=["pdf"], accept_multiple_files=True, key="tactical_pro_opp_pdfs")
            opp_team_xlsx = st.file_uploader("Ellenfél csapatstatisztika Excel", type=["xlsx", "xls"], key="tactical_pro_opp_team_xlsx")
            opp_player_xlsx = st.file_uploader("Ellenfél játékosstatisztika Excel", type=["xlsx", "xls"], key="tactical_pro_opp_player_xlsx")

    has_gps = bool(gps_context.get("has_gps", True))
    has_pdf = bool(opp_pdfs or own_pdfs)
    has_team_excel = opp_team_xlsx is not None or own_team_xlsx is not None
    has_player_excel = opp_player_xlsx is not None or own_player_xlsx is not None
    level, level_label = _fpi_analysis_level(has_gps, has_pdf, has_team_excel, has_player_excel)
    st.info(f"Elemzési szint: Level {level} – {level_label}")

    own_pdf_text, own_pdf_pages = _fpi_tactical_extract_pdf_text(own_pdfs or [])
    opp_pdf_text, opp_pdf_pages = _fpi_tactical_extract_pdf_text(opp_pdfs or [])
    own_pdf_insights = _fpi_tactical_pdf_insights(own_pdf_text) if own_pdf_text else {"blocks": {}, "topics": [], "raw_text_len": 0}
    opp_pdf_insights = _fpi_tactical_pdf_insights(opp_pdf_text) if opp_pdf_text else {"blocks": {}, "topics": [], "raw_text_len": 0}
    merged_pdf_insights = _merge_tactical_pdf_insights(own_pdf_insights, opp_pdf_insights)

    own_team_metrics, opp_team_metrics = {}, {}
    own_player_tables, opp_player_tables = {}, {}

    if own_team_xlsx is not None:
        own_team_df, own_team_mapping = _fpi_tactical_mapper_ui(own_team_xlsx, TACTICAL_TEAM_ALIASES_FPI, "own_team_tactical", "Saját csapat Excel")
        own_team_metrics = _fpi_tactical_parse_team_excel(own_team_df, own_team_mapping)

    if opp_team_xlsx is not None:
        opp_team_df, opp_team_mapping = _fpi_tactical_mapper_ui(opp_team_xlsx, TACTICAL_TEAM_ALIASES_FPI, "opp_team_tactical", "Ellenfél csapat Excel")
        opp_team_metrics = _fpi_tactical_parse_team_excel(opp_team_df, opp_team_mapping)

    if own_player_xlsx is not None:
        own_player_df, own_player_mapping = _fpi_tactical_mapper_ui(own_player_xlsx, TACTICAL_PLAYER_ALIASES_FPI, "own_player_tactical", "Saját játékos Excel")
        own_player_tables = _fpi_tactical_parse_player_excel(own_player_df, own_player_mapping)

    if opp_player_xlsx is not None:
        opp_player_df, opp_player_mapping = _fpi_tactical_mapper_ui(opp_player_xlsx, TACTICAL_PLAYER_ALIASES_FPI, "opp_player_tactical", "Ellenfél játékos Excel")
        opp_player_tables = _fpi_tactical_parse_player_excel(opp_player_df, opp_player_mapping)

    # A régi plan-motor ellenfél fókuszú volt. Megtartjuk, de kibővített, merge-elt PDF insighttal és ellenfél KPI-okkal etetjük.
    tactical_ctx_for_plan = {
        "analysis_level_label": level_label,
        "pdf_insights": merged_pdf_insights,
        "team_metrics": opp_team_metrics,
        "player_tables": opp_player_tables,
        "own": {"pdf_insights": own_pdf_insights, "team_metrics": own_team_metrics, "player_tables": own_player_tables},
        "opponent": {"pdf_insights": opp_pdf_insights, "team_metrics": opp_team_metrics, "player_tables": opp_player_tables},
    }
    plan = _fpi_build_adaptive_match_training_plan(gps_context, tactical_ctx_for_plan)
    executive_ctx = _build_tactical_executive_context(gps_context, tactical_ctx_for_plan, plan)
    st.session_state["tactical_pro_context"] = executive_ctx

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Adaptive szint", f"Level {level}")
    k2.metric("Saját PDF oldalak", len(own_pdf_pages))
    k3.metric("Ellenfél PDF oldalak", len(opp_pdf_pages))
    k4.metric("Taktikai KPI-k", len([v for v in {**own_team_metrics, **opp_team_metrics}.values() if v not in [0, 0.0, None]]))

    st.markdown("### 1. Match Plan AI – javasolt meccsterv")
    st.markdown(f"**Plan A:** {plan['plan_a']}")
    st.markdown("**Fő kockázatok / fókuszok:**")
    for r in plan["risks"]:
        st.markdown(f"- {r}")

    st.markdown("### 2. Saját vs ellenfél gyors összevetés")
    comp_rows = [
        {"Oldal": "Saját csapat", "PDF témák": len(own_pdf_insights.get("topics", []) or []), "Csapat KPI": _tactical_key_numbers_summary(own_team_metrics)},
        {"Oldal": "Ellenfél", "PDF témák": len(opp_pdf_insights.get("topics", []) or []), "Csapat KPI": _tactical_key_numbers_summary(opp_team_metrics)},
    ]
    st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)

    st.markdown("### 3. Training Planner AI – heti MD-terv")
    md_df = pd.DataFrame(plan["md_plan"], columns=["Nap", "Fókusz", "Miért?"])
    st.dataframe(md_df, use_container_width=True)

    st.markdown("### 4. Játékosszintű/taktikai fókusz")
    if plan["player_focus"]:
        for p in plan["player_focus"]:
            st.markdown(f"- {p}")
    else:
        st.caption("Nincs külön játékos Excel vagy kiemelt játékos. GPS-alapú monitoring marad aktív.")

    st.markdown("### 5. PDF-ből felismert taktikai témák")
    tcol1, tcol2 = st.columns(2)
    with tcol1:
        st.markdown("**Saját csapat PDF témák**")
        if own_pdf_insights.get("topics"):
            st.dataframe(pd.DataFrame(own_pdf_insights["topics"]), use_container_width=True)
        else:
            st.caption("Nincs saját taktikai PDF vagy nem volt felismerhető szöveg.")
    with tcol2:
        st.markdown("**Ellenfél PDF témák**")
        if opp_pdf_insights.get("topics"):
            st.dataframe(pd.DataFrame(opp_pdf_insights["topics"]), use_container_width=True)
        else:
            st.caption("Nincs ellenfél taktikai PDF vagy nem volt felismerhető szöveg.")

    with st.expander("PDF szövegkörnyezetek témánként – saját + ellenfél"):
        for key, lines in (merged_pdf_insights.get("blocks") or {}).items():
            if lines:
                st.markdown(f"**{TACTICAL_TOPIC_TAGS_FPI.get(key, {}).get('label', key)}**")
                for line in lines[:8]:
                    st.caption(line)

    export_payload = {
        "version": TACTICAL_PRO_VERSION,
        "analysis_level": level_label,
        "plan_a": plan["plan_a"],
        "risks": plan["risks"],
        "md_plan": [{"Nap": a, "Fókusz": b, "Miért": c} for a, b, c in plan["md_plan"]],
        "player_focus": plan["player_focus"],
        "own_detected_topics": own_pdf_insights.get("topics", []),
        "opp_detected_topics": opp_pdf_insights.get("topics", []),
        "own_team_metrics": own_team_metrics,
        "opp_team_metrics": opp_team_metrics,
    }
    st.download_button("⬇️ Tactical Pro+ JSON export", data=json.dumps(export_payload, ensure_ascii=False, indent=2).encode("utf-8"), file_name="fpi_tactical_pro_plus_export.json", mime="application/json", use_container_width=True)



# Tabok
tab_exec, tab_intro, tab1, tab_premium, tab_export, tab_methodology, tab_tactical_pro, tab_intel, tab_micro, tab_risk, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Dashboard",
    "ℹ️ Rendszer",
    "📌 Áttekintő",
    "🎛️ Cockpit",
    "📄 Export",
    "📚 Metodika",
    "🧠 Tactical Pro+",
    "🧠 Intelligence",
    "📅 Mikrociklus",
    "🚨 Kockázat",
    "🎯 Javaslatok",
    "👤 Játékosok",
    "✅ Adatminőség",
    "🧾 Nyers adatok",
])

with tab_methodology:
    render_methodology_tab()

with tab_tactical_pro:
    tactical_gps_context = {
        "has_gps": True,
        "selected_week": selected_week if 'selected_week' in globals() else None,
        "readiness_score": readiness_score if 'readiness_score' in globals() else 70,
        "playstyle": selected_playstyle if 'selected_playstyle' in globals() else "Kiegyensúlyozott",
        "priorities": coaching_priorities if 'coaching_priorities' in globals() else [],
        "periodization_type": periodization_type if 'periodization_type' in globals() else "n.a.",
    }
    render_tactical_pro_module(tactical_gps_context)




with tab_exec:
    st.markdown(
        """
        <div class="hero-box">
            <div class="hero-title">⭐ Vezetői riport</div>
            <div class="hero-sub">
                Egyetlen oldal vezetőedzőnek / sportigazgatónak: meccskészültség, fő kockázatok,
                top edzői teendők és exportálható vezetői csomag.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    mode_col1, mode_col2, mode_col3 = st.columns([1, 1, 2])
    with mode_col1:
        st.metric("Mód", "PRO" if is_pro_mode() else "DEMO")
    with mode_col2:
        st.metric("Hét", format_week_label(selected_week))
    with mode_col3:
        if not is_pro_mode():
            st.empty()
        else:
            pass

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Meccskészültség", f"{readiness_score}/100", score_to_label(readiness_score))
    with k2:
        st.metric("Magas risk", high_risk_count)
    with k3:
        st.metric("Közepes risk", medium_risk_count)
    with k4:
        st.metric("Insight", len(all_insights))
    with k5:
        mem_weeks = analysis_base_df["week"].nunique() if "week" in analysis_base_df.columns else 0
        st.metric("Elemzett hetek", mem_weeks)

    st.markdown("### Heti vezetői összefoglaló")
    st.info(week_status_info.get("message", ""))
    render_weekly_summary_card(weekly_summary_text)

    with st.expander("🧭 Múlt / aktuális / jövő fókusz", expanded=False):
        st.markdown("**Múlt hét -> erre a hétre**")
        render_weekly_summary_card(past_week_review_text)
        st.markdown("**Aktuális hét -> hátralévő napok**")
        render_weekly_summary_card(current_remaining_text)
        st.markdown("**Jövő hét**")
        render_weekly_summary_card(next_week_plan_text)

    left, right = st.columns([1.05, 1])
    with left:
        st.markdown("### Top 3 edzői teendő")
        render_coaching_priorities(coaching_priorities)

    with right:
        st.markdown("### Játékos risk gyorsnézet")
        if player_risk_df is not None and not player_risk_df.empty:
            show_cols = [c for c in ["Játékos", "Kockázati szint", "Risk score", "Fő ok"] if c in player_risk_df.columns]
            if show_cols:
                st.dataframe(player_risk_df[show_cols].head(8), use_container_width=True, hide_index=True)
            else:
                st.dataframe(player_risk_df.head(8), use_container_width=True, hide_index=True)
        else:
            st.info("Nincs player risk adat.")

    st.markdown("### Vezetői export")
    executive_df_main = build_executive_summary_df(
        selected_week,
        selected_playstyle,
        readiness_score,
        periodization_type,
        weekly_summary_text,
        high_risk_count,
        medium_risk_count,
    )
    insight_export_df_main = build_insight_export_df(all_insights)
    priorities_df_main = pd.DataFrame(coaching_priorities)
    risk_export_df_main = player_risk_df if "player_risk_df" in globals() else pd.DataFrame()
    safe_week_main = _safe_filename_week(selected_week)
    e1, e2, e3, e4 = st.columns(4)

    with e1:
        if is_pro_mode():
            premium_pdf = build_premium_pdf_bytes(
                insight_export_df_main,
                selected_week,
                readiness_score,
                periodization_type,
                weekly_summary_text,
                coaching_priorities,
                risk_export_df_main,
                selected_playstyle,
            )
            if premium_pdf is not None:
                st.download_button("⬇️ Vezetői PDF", data=premium_pdf, file_name=f"executive_performance_riport_{safe_week_main}.pdf", mime="application/pdf", use_container_width=True,
            key="download_button_unique_2",
        )
        else:
            pro_locked_box("Vezetői PDF export")

    with e2:
        if is_pro_mode():
            st.download_button(
                "⬇️ Vezetői Excel",
                data=build_executive_excel_bytes(executive_df_main, insight_export_df_main, priorities_df_main, risk_export_df_main, weekly_fingerprints),
                file_name=f"executive_performance_riport_{safe_week_main}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            
            key="download_button_unique_3",
        )
        else:
            pro_locked_box("Vezetői Excel export")

    with e3:
        if is_pro_mode():
            word_bytes = build_executive_word_bytes(executive_df_main, priorities_df_main, insight_export_df_main, risk_export_df_main, selected_week)
            if word_bytes is not None:
                st.download_button("⬇️ Vezetői Word", data=word_bytes, file_name=f"executive_performance_riport_{safe_week_main}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True,
            key="download_button_unique_4",
        )
        else:
            pro_locked_box("Vezetői Word export")

    with e4:
        st.download_button(
            "⬇️ Demo CSV preview",
            data=insight_export_df_main.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"demo_insight_preview_{safe_week_main}.csv",
            mime="text/csv",
            use_container_width=True,
        
            key="download_button_unique_5",
        )


    st.markdown("### Új FPI riportcsomag – éles PDF-ek")
    st.caption("Ezek ugyanazt a logikát használják, mint a minta PDF: vezetői nézet, erőnléti nézet, mikrociklus nézet és teljes stábcsomag.")
    rp1, rp2, rp3, rp4 = st.columns(4)
    live_report_base = analysis_base_df.copy()
    with rp1:
        exec_pack_pdf = build_fpi_product_pdf_bytes(live_report_base, selected_week, selected_playstyle, report_type="executive", tactical_context=st.session_state.get("tactical_pro_context"))
        if exec_pack_pdf is not None:
            st.download_button(
                "⬇️ Vezetői PDF 1-2 oldal",
                data=exec_pack_pdf,
                file_name=f"fpi_vezetoi_riport_{safe_week_main}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_fpi_exec_pack_v58",
            )
    with rp2:
        fitness_pack_pdf = build_fpi_product_pdf_bytes(live_report_base, selected_week, selected_playstyle, report_type="fitness", tactical_context=st.session_state.get("tactical_pro_context"))
        if fitness_pack_pdf is not None:
            st.download_button(
                "⬇️ Erőnléti PDF",
                data=fitness_pack_pdf,
                file_name=f"fpi_eronleti_riport_{safe_week_main}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_fpi_fitness_pack_v58",
            )
    with rp3:
        micro_pack_pdf = build_fpi_product_pdf_bytes(live_report_base, selected_week, selected_playstyle, report_type="microcycle", tactical_context=st.session_state.get("tactical_pro_context"))
        if micro_pack_pdf is not None:
            st.download_button(
                "⬇️ Mikrociklus PDF",
                data=micro_pack_pdf,
                file_name=f"fpi_mikrociklus_riport_{safe_week_main}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_fpi_micro_pack_v58",
            )
    with rp4:
        full_pack_pdf = build_fpi_product_pdf_bytes(live_report_base, selected_week, selected_playstyle, report_type="full", tactical_context=st.session_state.get("tactical_pro_context"))
        if full_pack_pdf is not None:
            st.download_button(
                "⬇️ Teljes stáb PDF",
                data=full_pack_pdf,
                file_name=f"fpi_teljes_stab_riport_{safe_week_main}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_fpi_full_pack_v58",
            )


with tab_intro:
    render_system_intro_page()

with tab1:
    st.subheader("Csapat áttekintő")
    st.caption("A főoldal célja: 30 másodperc alatt látni, mi fontos a héten.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Játékosok", filtered["player_name"].nunique())
    with col2:
        metric_card("Sessionök száma", len(filtered))
    with col3:
        td = filtered["total_distance"].sum() if "total_distance" in filtered.columns else np.nan
        metric_card("Össztáv", f"{td:,.0f} m" if pd.notna(td) else "—")
    with col4:
        load = filtered["training_load"].sum() if "training_load" in filtered.columns else np.nan
        metric_card("Terhelési pont", f"{load:,.0f}" if pd.notna(load) else "—")

    st.markdown("### Heti vezetői összefoglaló")
    render_weekly_summary_card(weekly_summary_text)
    r1, r2, r3 = st.columns(3)
    with r1:
        st.metric("Meccskészültség", f"{readiness_score}/100", score_to_label(readiness_score))
    with r2:
        st.metric("Periodizáció", periodization_type)
    with r3:
        mem_weeks = analysis_base_df["week"].nunique() if "week" in analysis_base_df.columns else 0
        st.metric("Elemzett hetek", mem_weeks)
    st.markdown("### Top 3 adaptív edzői teendő")
    render_coaching_priorities(coaching_priorities)

    st.markdown("### Múlt hét alapján: javaslat erre a hétre")
    render_weekly_summary_card(past_week_review_text)

    st.markdown("### Aktuális hét: maradék napok")
    render_weekly_summary_card(current_remaining_text)
    if current_remaining_plan_df is not None and not current_remaining_plan_df.empty:
        st.dataframe(current_remaining_plan_df, use_container_width=True, hide_index=True)

    st.markdown("### Jövő hét / következő mikrociklus")
    render_weekly_summary_card(next_week_plan_text)
    if next_week_plan_df is not None and not next_week_plan_df.empty:
        st.dataframe(next_week_plan_df, use_container_width=True, hide_index=True)

    weekly = aggregate_weekly(df[df["session_type"].isin(selected_types)])
    st.markdown("### Heti trendek")
    trend_options = available_metric_options(
        weekly,
        ["training_load", "total_distance", "sprint_distance", "hsr_distance", "distance_per_min", "max_speed", "dec_count"],
    )
    if trend_options:
        chart_metric = st.selectbox("Trendmutató", trend_options, format_func=metric_name, index=0)
        fig = px.line(
            weekly,
            x="week",
            y=chart_metric,
            color="session_type",
            markers=True,
            title=f"Heti trend: {metric_name(chart_metric)}",
        )
        fig.update_layout(xaxis_title="Hét", yaxis_title=metric_name(chart_metric), legend_title="Típus", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nincs elérhető trendmutató.")

    st.markdown("### Edzés vs meccs profil az aktuális héten")
    profile_cols = available_metric_options(
        filtered,
        ["total_distance", "distance_per_min", "sprint_distance", "hsr_distance", "max_speed", "dec_count"],
    )
    if profile_cols:
        prof = filtered.groupby("session_type", as_index=False)[profile_cols].mean(numeric_only=True)
        prof = prof.rename(columns={c: metric_name(c) for c in profile_cols})
        prof = prof.rename(columns={"session_type": "Típus"})
        st.dataframe(prof, use_container_width=True, hide_index=True)
    else:
        st.info("Nincs elérhető edzés-meccs összehasonlító mutató.")




with tab_premium:
    st.subheader("🎛️ Cockpit")
    st.caption("Cool vezetői nézet: readiness, risk, load, sprint, periodizáció és top teendők egy képernyőn.")
    render_hero(selected_week, selected_playstyle, readiness_score, periodization_type)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_premium_kpi("Meccskészültség", f"{readiness_score}/100", score_to_label(readiness_score), score_to_color(readiness_score))
    with k2:
        render_premium_kpi("Magas kockázatos játékos", str(high_risk_count), "Játékos kockázati motor alapján", "#ef4444" if high_risk_count else "#22c55e")
    with k3:
        mem_weeks = analysis_base_df["week"].nunique() if "week" in analysis_base_df.columns else 0
        render_premium_kpi("Elemzett hetek", str(mem_weeks), "Memory + aktuális feltöltés", "#38bdf8")
    with k4:
        render_premium_kpi("Periodizáció", periodization_type, "Automatikus heti besorolás", "#a78bfa")
    st.markdown("### Meccskészültség komponensek")
    if readiness_components:
        comp_df = pd.DataFrame([{"Komponens": k, "Pont": round(v, 1)} for k, v in readiness_components.items()])
        fig = px.bar(comp_df, x="Komponens", y="Pont", range_y=[0, 100], title="Meccskészültség komponensek")
        fig.update_layout(xaxis_title="", yaxis_title="Pont", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("### Top 3 edzői teendő")
    render_coaching_priorities(coaching_priorities)
    st.markdown("### Top játékos kockázat")
    render_risk_cards(player_risk_df, limit=5)
    if weekly_fingerprints is not None and not weekly_fingerprints.empty:
        st.markdown("### Multi-week performance fingerprint")
        trend_metric_options = [c for c in ["training_load", "sprint_distance", "distance_per_min", "max_speed", "dec_count"] if c in weekly_fingerprints.columns]
        if trend_metric_options:
            tm = st.selectbox("Vezetői trendmutató", trend_metric_options, format_func=metric_name)
            fig = px.line(weekly_fingerprints, x="week", y=tm, markers=True, title=f"Performance memória trend: {metric_name(tm)}")
            fig.update_layout(xaxis_title="Hét", yaxis_title=metric_name(tm), template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)


with tab_export:
    st.subheader("📄 Export")
    st.caption("Egy helyen minden vezetői információ és export: összefoglaló, readiness, teendők, player risk, insightok.")

    st.markdown(
        """
        <div class="export-panel">
            <h3 style="margin-top:0;">Vezetői csomag</h3>
            <p style="color:#e0f2fe;">
                Ezt érdemes megmutatni vagy elküldeni a vezetőedzőnek: rövid összefoglaló,
                top teendők, readiness, kockázati lista és insightok.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    executive_df = build_executive_summary_df(
        selected_week,
        selected_playstyle,
        readiness_score,
        periodization_type,
        weekly_summary_text,
        high_risk_count if "high_risk_count" in globals() else 0,
        medium_risk_count if "medium_risk_count" in globals() else 0,
    )
    insight_export_df_export = build_insight_export_df(all_insights)
    priorities_df = pd.DataFrame(coaching_priorities)
    risk_export_df = player_risk_df if "player_risk_df" in globals() else pd.DataFrame()

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Meccskészültség", f"{readiness_score}/100", score_to_label(readiness_score))
    with k2:
        st.metric("Periodizáció", periodization_type)
    with k3:
        st.metric("Magas kockázat", high_risk_count if "high_risk_count" in globals() else 0)
    with k4:
        st.metric("Insightok", len(all_insights))

    st.markdown("### Heti vezetői összefoglaló")
    render_wrapped_table(executive_df)

    st.markdown("### Mit jelentenek a fő fogalmak?")
    render_wrapped_table(build_plain_language_explanation())

    st.markdown("### Top 3 edzői teendő")
    if not priorities_df.empty:
        render_wrapped_table(priorities_df)
    else:
        st.info("Nincs kiemelt teendő.")

    st.markdown("### Játékos risk")
    if risk_export_df is not None and not risk_export_df.empty:
        render_wrapped_table(risk_export_df.head(10))
    else:
        st.info("Nincs player kockázati adat.")

    st.markdown("### Insightok")
    render_wrapped_table(insight_export_df_export)

    st.markdown("### Export gombok")
    if not is_pro_mode():
        st.warning("Demo módban a teljes vezetői PDF/Word/Excel export Pro funkció. A főoldalon demo CSV preview elérhető.")
    safe_week = _safe_filename_week(selected_week)
    e1, e2, e3, e4 = st.columns(4)

    with e1:
        premium_pdf = None
        if "build_premium_pdf_bytes" in globals():
            premium_pdf = build_premium_pdf_bytes(
                insight_export_df_export,
                selected_week,
                readiness_score,
                periodization_type,
                weekly_summary_text,
                coaching_priorities,
                risk_export_df,
                selected_playstyle,
            )
        else:
            premium_pdf = insights_to_pdf_bytes(insight_export_df_export, selected_week)

        if premium_pdf is not None:
            st.download_button(
                "⬇️ Vezetői PDF",
                data=premium_pdf,
                file_name=f"executive_performance_riport_{safe_week}.pdf",
                mime="application/pdf",
                use_container_width=True,
            
            key="download_button_unique_6",
        )

    with e2:
        st.download_button(
            "⬇️ Vezetői Excel",
            data=build_executive_excel_bytes(
                executive_df,
                insight_export_df_export,
                priorities_df,
                risk_export_df,
                weekly_fingerprints if "weekly_fingerprints" in globals() else pd.DataFrame(),
            ),
            file_name=f"executive_performance_riport_{safe_week}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        
            key="download_button_unique_7",
        )

    with e3:
        word_bytes = build_executive_word_bytes(
            executive_df,
            priorities_df,
            insight_export_df_export,
            risk_export_df,
            selected_week,
        )
        if word_bytes is not None:
            st.download_button(
                "⬇️ Vezetői Word",
                data=word_bytes,
                file_name=f"executive_performance_riport_{safe_week}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            
            key="download_button_unique_8",
        )
        else:
            st.info("Word exporthoz szükséges: python-docx")

    with e4:
        csv_bundle = insight_export_df_export.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Insight CSV",
            data=csv_bundle,
            file_name=f"executive_insightok_{safe_week}.csv",
            mime="text/csv",
            use_container_width=True,
        
            key="download_button_unique_9",
        )


    # -------------------------------------------------------------------------
    # V6.1 - Product Report Pack visszaemelve az Export fülre is
    # -------------------------------------------------------------------------
    st.markdown("### FPI riportcsomag – minta PDF-ek")
    st.caption("Klubdemóhoz: vezetői, erőnléti, mikrociklus és teljes stáb PDF ugyanazzal a logikával, mint az éles export.")
    if 'build_fpi_sample_pdf_bytes' in globals():
        try:
            sample_exec_pdf_bytes_export = build_fpi_sample_pdf_bytes("executive")
            sample_fitness_pdf_bytes_export = build_fpi_sample_pdf_bytes("fitness")
            sample_micro_pdf_bytes_export = build_fpi_sample_pdf_bytes("microcycle")
            sample_full_pdf_bytes_export = build_fpi_sample_pdf_bytes("full")
        except Exception:
            sample_exec_pdf_bytes_export = sample_fitness_pdf_bytes_export = sample_micro_pdf_bytes_export = sample_full_pdf_bytes_export = None
        sm1, sm2, sm3, sm4 = st.columns(4)
        with sm1:
            if sample_exec_pdf_bytes_export is not None:
                st.download_button("⬇️ Minta vezetői PDF", data=sample_exec_pdf_bytes_export, file_name="fpi_minta_vezetoi_riport.pdf", mime="application/pdf", use_container_width=True, key="download_sample_executive_v61_export")
        with sm2:
            if sample_fitness_pdf_bytes_export is not None:
                st.download_button("⬇️ Minta erőnléti PDF", data=sample_fitness_pdf_bytes_export, file_name="fpi_minta_eronleti_riport.pdf", mime="application/pdf", use_container_width=True, key="download_sample_fitness_v61_export")
        with sm3:
            if sample_micro_pdf_bytes_export is not None:
                st.download_button("⬇️ Minta mikrociklus PDF", data=sample_micro_pdf_bytes_export, file_name="fpi_minta_mikrociklus_riport.pdf", mime="application/pdf", use_container_width=True, key="download_sample_micro_v61_export")
        with sm4:
            if sample_full_pdf_bytes_export is not None:
                st.download_button("⬇️ Minta teljes stáb PDF", data=sample_full_pdf_bytes_export, file_name="fpi_minta_teljes_stab_riportcsomag.pdf", mime="application/pdf", use_container_width=True, key="download_sample_full_v61_export")
        if all(x is None for x in [sample_exec_pdf_bytes_export, sample_fitness_pdf_bytes_export, sample_micro_pdf_bytes_export, sample_full_pdf_bytes_export]):
            st.info("A minta PDF exporthoz a reportlab csomag szükséges.")

    st.markdown("### FPI riportcsomag – éles PDF-ek")
    st.caption("Az aktuális feltöltött / minta adatokból: vezetői 1-2 oldal, erőnléti riport, mikrociklus riport, teljes stábcsomag.")
    if 'build_fpi_product_pdf_bytes' in globals():
        live_report_base_export = analysis_base_df.copy() if 'analysis_base_df' in globals() else df.copy()
        rp1e, rp2e, rp3e, rp4e = st.columns(4)
        with rp1e:
            exec_pack_pdf_export = build_fpi_product_pdf_bytes(live_report_base_export, selected_week, selected_playstyle, report_type="executive")
            if exec_pack_pdf_export is not None:
                st.download_button("⬇️ Éles vezetői PDF", data=exec_pack_pdf_export, file_name=f"fpi_vezetoi_riport_{safe_week}.pdf", mime="application/pdf", use_container_width=True, key="download_fpi_exec_pack_v61_export")
        with rp2e:
            fitness_pack_pdf_export = build_fpi_product_pdf_bytes(live_report_base_export, selected_week, selected_playstyle, report_type="fitness")
            if fitness_pack_pdf_export is not None:
                st.download_button("⬇️ Éles erőnléti PDF", data=fitness_pack_pdf_export, file_name=f"fpi_eronleti_riport_{safe_week}.pdf", mime="application/pdf", use_container_width=True, key="download_fpi_fitness_pack_v61_export")
        with rp3e:
            micro_pack_pdf_export = build_fpi_product_pdf_bytes(live_report_base_export, selected_week, selected_playstyle, report_type="microcycle")
            if micro_pack_pdf_export is not None:
                st.download_button("⬇️ Éles mikrociklus PDF", data=micro_pack_pdf_export, file_name=f"fpi_mikrociklus_riport_{safe_week}.pdf", mime="application/pdf", use_container_width=True, key="download_fpi_micro_pack_v61_export")
        with rp4e:
            full_pack_pdf_export = build_fpi_product_pdf_bytes(live_report_base_export, selected_week, selected_playstyle, report_type="full")
            if full_pack_pdf_export is not None:
                st.download_button("⬇️ Éles teljes stáb PDF", data=full_pack_pdf_export, file_name=f"fpi_teljes_stab_riport_{safe_week}.pdf", mime="application/pdf", use_container_width=True, key="download_fpi_full_pack_v61_export")
    else:
        st.warning("A V5.8 Product Report Pack függvényei nem érhetők el ebben a fájlban.")


with tab_intel:
    st.subheader("🧠 Intelligence")
    st.caption("V2.5: readiness score, periodizáció, performance memória, multi-week mintázatok és adaptív ajánlások.")

    c1, c2 = st.columns([1, 1])
    with c1:
        render_score_card(
            "Meccskészültség",
            readiness_score,
            score_to_label(readiness_score),
            readiness_reasons,
        )
    with c2:
        st.markdown("### Meccskészültség komponensek")
        if readiness_components:
            comp_df = pd.DataFrame([
                {"Komponens": k, "Pont": round(v, 1)}
                for k, v in readiness_components.items()
            ])
            fig = px.bar(comp_df, x="Komponens", y="Pont", range_y=[0, 100], title="Meccskészültség komponensek")
            fig.update_layout(xaxis_title="", yaxis_title="Pont")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nincs elég adat a komponensekhez.")

    st.markdown("### Periodizációs besorolás")
    st.info(f"Az aktuális hét besorolása: **{periodization_type}**")

    st.markdown("### Heti lenyomat / performance memória")
    if weekly_fingerprints.empty:
        st.info("Nincs elég heti adat a fingerprint táblához.")
    else:
        show_cols = [
            "week", "periodizacios_tipus", "players", "training_load", "total_distance",
            "sprint_distance", "distance_per_min", "max_speed", "dec_count"
        ]
        show_cols = [c for c in show_cols if c in weekly_fingerprints.columns]
        fp_show = weekly_fingerprints[show_cols].copy()
        fp_show = fp_show.rename(columns={
            "week": "Hét",
            "periodizacios_tipus": "Periodizáció",
            "players": "Játékosok",
            "training_load": "Terhelési pont",
            "total_distance": "Össztáv",
            "sprint_distance": "Sprinttáv",
            "distance_per_min": "Táv/perc",
            "max_speed": "Max sebesség",
            "dec_count": "Lassítások",
        })
        st.dataframe(fp_show, use_container_width=True, hide_index=True)

        trend_metric_options = [c for c in ["training_load", "sprint_distance", "distance_per_min", "max_speed", "dec_count"] if c in weekly_fingerprints.columns]
        if trend_metric_options:
            tm = st.selectbox("Memória trendmutató", trend_metric_options, format_func=metric_name)
            fig = px.line(weekly_fingerprints, x="week", y=tm, markers=True, title=f"Többhetes trend: {metric_name(tm)}")
            fig.update_layout(xaxis_title="Hét", yaxis_title=metric_name(tm))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Többhetes mintázatok")
    if pattern_insights:
        render_insight_cards(pattern_insights)
    else:
        st.success("Nem látható kiemelt többhetes negatív mintázat az aktuális adatok alapján.")

    st.markdown("### Adaptív ajánlórendszer")
    render_coaching_priorities(coaching_priorities)


with tab_micro:
    st.subheader("📅 Mikrociklus")
    st.caption("A rendszer a meccsnaphoz viszonyítva értelmezi a heti struktúrát: MD-4, MD-3, MD-2, MD-1, MD, MD+1.")

    micro_df = build_microcycle_table(analysis_base_df, selected_week)
    if micro_df.empty:
        st.info("Nincs elérhető mikrociklus adat az aktuális szűrésre.")
    else:
        match_day = detect_match_day(analysis_base_df[analysis_base_df["week"] == selected_week])
        if match_day is not None:
            st.markdown(
                f"<span class='micro-pill'>Meccsnap: {match_day.strftime('%Y-%m-%d')}</span>"
                f"<span class='micro-pill'>Játékmodell: {html.escape(selected_playstyle)}</span>",
                unsafe_allow_html=True,
            )
        else:
            st.warning("Az aktuális héten nincs automatikusan azonosítható meccsnap.")

        show_cols = [
            "session_date_dt", "md_label", "session_type", "load_index", "total_distance",
            "distance_per_min", "sprint_distance", "hsr_distance", "max_speed", "dec_count", "játékosok"
        ]
        show_cols = [c for c in show_cols if c in micro_df.columns]
        show_micro = micro_df[show_cols].copy()
        if "session_date_dt" in show_micro.columns:
            show_micro["session_date_dt"] = show_micro["session_date_dt"].dt.strftime("%Y-%m-%d")
        show_micro = show_micro.rename(columns={
            "session_date_dt": "Dátum",
            "md_label": "MD-nap",
            "session_type": "Típus",
            "load_index": "Load index",
            "total_distance": "Össztáv",
            "distance_per_min": "Táv/perc",
            "sprint_distance": "Sprinttáv",
            "hsr_distance": "Nagy sebességű táv",
            "max_speed": "Max sebesség",
            "dec_count": "Lassítások",
            "játékosok": "Játékosok",
        })
        st.dataframe(show_micro, use_container_width=True, hide_index=True)

        chart_cols = available_metric_options(micro_df, ["load_index", "sprint_distance", "distance_per_min", "max_speed", "dec_count"])
        if chart_cols:
            metric = st.selectbox("Mikrociklus grafikon mutató", chart_cols, format_func=lambda x: "Load index" if x == "load_index" else metric_name(x))
            fig = px.bar(
                micro_df,
                x="md_label",
                y=metric,
                color="session_type",
                hover_data=["session_date_dt"],
                title=f"Mikrociklus profil: {'Load index' if metric == 'load_index' else metric_name(metric)}",
            )
            fig.update_layout(xaxis_title="Meccsnaphoz viszonyított nap", yaxis_title="Load index" if metric == "load_index" else metric_name(metric), legend_title="Típus")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Mikrociklus megállapítások")
        if micro_insights:
            render_insight_cards(micro_insights)
        else:
            st.success("A mikrociklus struktúrában nem látszik kiemelt figyelmeztetés az aktuális szabályok alapján.")



    st.markdown("## 🧭 Múlt hét -> aktuális hét -> jövő hét")
    st.caption("A rendszer külön kezeli: múlt hét teljes elemzése, aktuális hét hátralévő napjai, jövő heti mikrociklus.")

    st.markdown("### 1) Múlt hét teljes elemzése és javaslat erre a hétre")
    render_weekly_summary_card(past_week_review_text)
    if past_week_review_df is not None and not past_week_review_df.empty:
        st.dataframe(past_week_review_df, use_container_width=True, hide_index=True)

    st.markdown("### 2) Aktuális hét eddig feltöltött napjai és hátralévő napok")
    render_weekly_summary_card(current_remaining_text)
    if current_remaining_plan_df is not None and not current_remaining_plan_df.empty:
        st.dataframe(current_remaining_plan_df, use_container_width=True, hide_index=True)

    st.markdown("### 3) Jövő hét / következő mikrociklus az eddigiek alapján")
    render_weekly_summary_card(next_week_plan_text)
    if next_week_plan_df is not None and not next_week_plan_df.empty:
        st.dataframe(next_week_plan_df, use_container_width=True, hide_index=True)

    st.markdown("### 4) Játékosszintű következő teendők")
    if player_next_actions_df is not None and not player_next_actions_df.empty:
        st.dataframe(player_next_actions_df, use_container_width=True, hide_index=True)


with tab_risk:
    st.subheader("🚨 Kockázat")
    st.caption("Játékosszintű, többhetes eltérésalapú risk scoring: load spike, sprintprofil, lassítások, max sebesség.")
    if player_risk_df.empty:
        st.info("Nincs elég adat a játékosszintű risk engine-hez. Legalább több hét játékosszintű adat kell hozzá.")
    else:
        render_risk_cards(player_risk_df, limit=8)
        st.markdown("### Kockázati tábla")
        st.dataframe(player_risk_df, use_container_width=True, hide_index=True)
        fig = px.bar(player_risk_df.head(20), x="Játékos", y="Kockázati pontszám", color="Kockázati szint", title="Játékos risk score")
        fig.update_layout(xaxis_title="Játékos", yaxis_title="Kockázati pontszám", xaxis_tickangle=-45, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        st.download_button("⬇️ Játékos risk export CSV", data=player_risk_df.to_csv(index=False).encode("utf-8-sig"), file_name=f"player_risk_{_safe_filename_week(selected_week)}.csv", mime="text/csv", use_container_width=True,
            key="download_button_unique_10",
        )

with tab2:
    st.subheader("🎯 Javaslatok")
    st.caption("Szabályalapú performance motor: AI nélkül is ad szakmai következtetést és javaslatot.")

    insights = all_insights

    st.markdown("### Heti összefoglaló")
    render_weekly_summary_card(weekly_summary_text)

    st.markdown("### Top 3 adaptív edzői teendő")
    render_coaching_priorities(coaching_priorities)

    st.markdown("### Coach-friendly insight kártyák")
    render_insight_cards(insights)

    st.markdown("### Exportálható insight tábla")
    insight_export_df = build_insight_export_df(insights)
    render_wrapped_table(insight_export_df)

    with st.expander("Táblázat szerkesztés nélküli nézetben"):
        st.data_editor(
            insight_export_df,
            use_container_width=True,
            hide_index=True,
            disabled=True,
            column_config={
                "Mit látunk?": st.column_config.TextColumn("Mit látunk?", width="large"),
                "Miért fontos?": st.column_config.TextColumn("Miért fontos?", width="large"),
                "Javaslat": st.column_config.TextColumn("Javaslat", width="large"),
                "Megállapítás": st.column_config.TextColumn("Megállapítás", width="medium"),
            },
        )

    st.markdown("#### Riport exportálása")
    safe_week = _safe_filename_week(selected_week)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.download_button(
            "⬇️ Excel riport",
            data=insights_to_excel_bytes(insight_export_df, selected_week),
            file_name=f"performance_riport_{safe_week}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        
            key="download_button_unique_11",
        )
    with c2:
        csv_bytes = insight_export_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ CSV",
            data=csv_bytes,
            file_name=f"performance_riport_{safe_week}.csv",
            mime="text/csv",
            use_container_width=True,
        
            key="download_button_unique_12",
        )
    with c3:
        word_bytes = insights_to_word_bytes(insight_export_df, selected_week)
        if word_bytes is not None:
            st.download_button(
                "⬇️ Word riport",
                data=word_bytes,
                file_name=f"performance_riport_{safe_week}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            
            key="download_button_unique_13",
        )
        else:
            st.info("Word exporthoz add hozzá a requirements.txt fájlhoz: python-docx")
    with c4:
        pdf_bytes = insights_to_pdf_bytes(insight_export_df, selected_week)
        if pdf_bytes is not None:
            st.download_button(
                "⬇️ PDF riport",
                data=pdf_bytes,
                file_name=f"performance_riport_{safe_week}.pdf",
                mime="application/pdf",
                use_container_width=True,
            
            key="download_button_unique_14",
        )
        else:
            st.info("PDF exporthoz add hozzá a requirements.txt fájlhoz: reportlab")
    st.markdown("#### Vezetői V3 PDF export")
    premium_pdf = build_premium_pdf_bytes(insight_export_df, selected_week, readiness_score, periodization_type, weekly_summary_text, coaching_priorities, player_risk_df, selected_playstyle)
    if premium_pdf is not None:
        st.download_button("⬇️ Vezetői V3 PDF riport", data=premium_pdf, file_name=f"premium_performance_riport_{safe_week}.pdf", mime="application/pdf", use_container_width=True,
            key="download_button_unique_15",
        )

with tab3:
    st.subheader("👤 Játékosok")
    pw = player_weekly(df)
    pw_current = pw[(pw["week"] == selected_week) & (pw["player_name"].isin(selected_players))]
    if not pw_current.empty:
        rank_options = available_metric_options(
            pw_current,
            ["training_load", "total_distance", "sprint_distance", "hsr_distance", "max_speed", "dec_count", "high_efforts"],
        )
        if rank_options:
            metric = st.selectbox("Játékos rangsor mutató", rank_options, format_func=metric_name, index=0)
            rank = pw_current.groupby("player_name", as_index=False)[metric].sum().sort_values(metric, ascending=False)
            fig = px.bar(rank.head(25), x="player_name", y=metric, title=f"Játékosrangsor: {metric_name(metric)}")
            fig.update_layout(xaxis_title="Játékos", yaxis_title=metric_name(metric), xaxis_tickangle=-45, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Játékos heti összesítő tábla")
        show = pw_current.rename(columns={"player_name": "Játékos", "week": "Hét", "session_type": "Típus"})
        show = show.rename(columns={c: metric_name(c) for c in pw_current.columns})
        st.dataframe(show, use_container_width=True, hide_index=True)
    else:
        st.info("Nincs adat az aktuális szűrésre.")

with tab4:
    st.subheader("✅ Adatminőség")
    st.caption("Ez azért fontos, mert a sportadat a valóságban mindig kicsit koszos.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Nyers sor", len(raw_df))
    with c2:
        metric_card("Standardizált sor", len(df))
    with c3:
        metric_card("Hetek", df["week"].nunique())
    with c4:
        metric_card("Típusok", ", ".join(session_types))

    st.markdown("### Performance memória állapot")
    mem_df = load_memory_df()
    if mem_df.empty:
        st.info("Nincs még mentett lokális memory adat.")
    else:
        st.success(f"Mentett memory: {len(mem_df)} sor, {mem_df['week'].nunique() if 'week' in mem_df.columns else 'ismeretlen'} hét.")
    st.markdown("### Automatikus oszlopmapping")
    map_df = pd.DataFrame([
        {"standard mező": k, "forrás oszlop": v if v is not None else "NINCS"}
        for k, v in mapping.items()
    ])
    st.dataframe(map_df, use_container_width=True, hide_index=True)

    st.markdown("### Hiányzó értékek a standard mezőkben")
    na = df.isna().mean().sort_values(ascending=False).reset_index()
    na.columns = ["oszlop", "hiányzó arány"]
    st.dataframe(na.head(30), use_container_width=True, hide_index=True)

with tab5:
    st.subheader("Nyers / standardizált adatok")
    st.markdown("### Standardizált adat")
    st.dataframe(df.head(500), use_container_width=True)
    st.markdown("### Nyers adat")
    st.dataframe(raw_df.head(200), use_container_width=True)


st.divider()
st.caption("V5.7 GENERAL EXCEL IMPORT – Data lap + általános fejlécfelismerés + védett dátumkezelés + ISO hetek.")

# -----------------------------------------------------------------------------
# V4.4 Smart Excel Mapper + License UI
# -----------------------------------------------------------------------------
with st.expander("🧩 Smart Excel Mapper + License / oszlopmapping ellenőrzése", expanded=False):
    st.write("Ha más klub más szerkezetű Excel-exportot tölt fel, itt ellenőrizhető és javítható, hogy melyik forrásoszlop melyik standard mezőre menjen.")
    raw_df_for_mapper = locals().get("raw_df", st.session_state.get("last_raw_df", pd.DataFrame()))
    if isinstance(raw_df_for_mapper, pd.DataFrame) and not raw_df_for_mapper.empty:
        raw_df = raw_df_for_mapper
        current_mapping = st.session_state.get("manual_mapping", None)
        if current_mapping is None:
            current_mapping = suggest_mapping(raw_df)
        render_mapping_score(current_mapping)
        st.session_state["manual_mapping"] = current_mapping

        profile_upload = st.file_uploader("Korábban mentett mapping profil betöltése (.json)", type=["json"], key="mapping_profile_upload")
        if profile_upload is not None:
            loaded_mapping = load_mapping_profile(profile_upload)
            if loaded_mapping:
                st.session_state["manual_mapping"] = loaded_mapping
                current_mapping = loaded_mapping
                st.success("Mapping profil betöltve.")

        st.dataframe(enhanced_mapping_quality_df(raw_df, current_mapping), use_container_width=True)

        if st.button("♻️ Mapping override törlése", use_container_width=True, key="clear_mapping_override"):
            st.session_state.pop("mapped_df_override", None)
            st.session_state.pop("manual_mapping", None)
            st.rerun()

        st.markdown("#### Kézi javítás")
        source_options = [""] + list(raw_df.columns)
        cols = st.columns(2)
        editable_mapping = dict(current_mapping)
        important_fields = CORE_REQUIRED + [
            "position", "duration", "total_distance", "distance_per_min", "max_speed",
            "sprints", "speed_zone_4", "speed_zone_5", "training_load", "acc_high", "dec_high"
        ]
        for idx, std_col in enumerate(important_fields):
            with cols[idx % 2]:
                current_val = editable_mapping.get(std_col) or ""
                default_idx = source_options.index(current_val) if current_val in source_options else 0
                editable_mapping[std_col] = st.selectbox(
                    f"{std_col} → forrásoszlop",
                    source_options,
                    index=default_idx,
                    key=f"mapper_select_{std_col}",
                ) or None

        c_apply, c_export = st.columns(2)
        with c_apply:
            if st.button("✅ Mapping alkalmazása erre a fájlra", use_container_width=True, key="apply_manual_mapping"):
                mapped_df, applied_mapping, missing = apply_mapping_to_raw(raw_df, editable_mapping)
                if missing:
                    st.error(f"Hiányzó kötelező mezők: {', '.join(missing)}")
                else:
                    st.session_state["manual_mapping"] = applied_mapping
                    st.session_state["mapped_df_override"] = mapped_df
                    st.success(f"Mapping alkalmazva. Feldolgozott sorok: {len(mapped_df)}")
                    st.rerun()
        with c_export:
            st.download_button(
                "⬇️ Mapping profil mentése",
                data=export_mapping_profile(editable_mapping),
                file_name="gps_mapping_profile.json",
                mime="application/json",
                use_container_width=True,
                key="download_mapping_profile",
            )
    else:
        st.info("Mapping ellenőrzéshez előbb tölts fel egy Excel/CSV fájlt.")
