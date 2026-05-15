# performance_app_v2_0_hu.py
# AI-assisted Performance Recommendation System - magyar Streamlit MVP
# Upload -> standardizálás -> KPI-k -> szabályalapú insightok -> coach-friendly javaslatok -> Excel/Word/PDF export

from __future__ import annotations

import html
import io
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


# -----------------------------------------------------------------------------
# Oldalbeállítás
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Football Performance Intelligence V3",
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
        color: rgba(226,232,240,.86);
        font-weight: 800;
        margin-top: 6px;
    }
    .mini-muted {
        color: rgba(226,232,240,.72);
        font-size: .92rem;
        line-height: 1.35;
    }

    .hero-box {border-radius:24px;padding:24px 28px;margin-bottom:20px;background:radial-gradient(circle at top left,rgba(34,197,94,.22),transparent 34%),radial-gradient(circle at bottom right,rgba(59,130,246,.24),transparent 30%),linear-gradient(135deg,rgba(2,6,23,.96),rgba(15,23,42,.88));border:1px solid rgba(148,163,184,.22);box-shadow:0 18px 45px rgba(0,0,0,.28)}
    .hero-title {font-size:2.1rem;font-weight:950;letter-spacing:-.04em;margin-bottom:4px}.hero-sub{color:rgba(226,232,240,.78);font-size:1.02rem;line-height:1.45}
    .premium-kpi{border-radius:20px;padding:18px;background:linear-gradient(145deg,rgba(15,23,42,.94),rgba(30,41,59,.78));border:1px solid rgba(148,163,184,.20);box-shadow:0 10px 28px rgba(0,0,0,.18);min-height:120px}
    .premium-kpi-label{color:rgba(226,232,240,.72);font-size:.86rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em}.premium-kpi-value{font-size:2rem;font-weight:950;margin-top:8px;line-height:1}.premium-kpi-note{color:rgba(226,232,240,.70);font-size:.86rem;margin-top:9px}
    .risk-high{border-left:8px solid #ef4444!important}.risk-medium{border-left:8px solid #f59e0b!important}.risk-low{border-left:8px solid #22c55e!important}
    .section-chip{display:inline-block;padding:5px 11px;border-radius:999px;background:rgba(34,197,94,.15);border:1px solid rgba(34,197,94,.25);color:#bbf7d0;font-weight:850;margin:2px 4px 8px 0}
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Oszlopmapping
# -----------------------------------------------------------------------------
STANDARD_COLUMNS = {
    "player_name": ["Játékos neve", "Player", "Player Name", "Name", "Név"],
    "session_type": ["Típus", "Type", "Session Type", "Edzés/Meccs"],
    "session_name": ["Szakasz neve", "Session", "Session Name"],
    "position": ["Poszt", "Position", "Player Position", "Role"],
    "start_time": ["Kezdési idő", "Start Time", "Start", "Dátum", "Date"],
    "end_time": ["Befejezési idő", "End Time", "End"],
    "duration": ["Időtartam", "Duration", "Time"],
    "total_distance": ["Teljes táv [m]", "Tel\xadjes táv [m]", "Total Distance", "Distance", "Össztáv"],
    "distance_per_min": ["Táv/perc [m/min]", "Distance/min", "Distance Per Min", "m/min"],
    "max_speed": ["Maximális sebesség [km/h]", "Max Speed", "Maximum Speed"],
    "avg_speed": ["Átlagsebesség [km/h]", "Average Speed", "Avg Speed"],
    "sprints": ["Sprintek", "Sprints", "Sprint Count"],
    "speed_zone_3": ["Táv a sebesség célzónában 3 [m] (14.40 - 19.79 km/h)"],
    "speed_zone_4": ["Táv a sebesség célzónában 4 [m] (19.80 - 24.99 km/h)"],
    "speed_zone_5": ["Táv a sebesség célzónában 5 [m] (25.00- km/h)"],
    "training_load": ["Edzési terhelési pontérték", "Terhelési pont", "Player Load", "Load"],
    "cardio_load": ["Kardióterhelés", "Cardio Load"],
    "recovery_hours": ["Regenerálódási idő [h]", "Recovery Time", "Recovery"],
    "muscle_load": ["Izomterhelés", "Muscle Load"],
    "hr_avg": ["Átlagos pulzus [bpm]", "Average HR", "Avg HR"],
    "hr_max": ["Maximális pulzus [bpm]", "Max HR", "Maximum HR"],
    "hrv": ["HRV (RMSSD)", "HRV", "RMSSD"],
    "acc_low": ["Gyorsulások száma (2.00 - 2.49 m/s²)"],
    "acc_mid": ["Gyorsulások száma (2.50 - 2.99 m/s²)"],
    "acc_high": ["Gyorsulások száma (3.00 - 50.00 m/s²)"],
    "dec_low": ["Gyorsulások száma (-2.49 - -2.00 m/s²)"],
    "dec_mid": ["Gyorsulások száma (-2.99 - -2.50 m/s²)"],
    "dec_high": ["Gyorsulások száma (-50.00 - -3.00 m/s²)"],
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
    "Transition": "Gyors átmenetek, magas sprint- és speed exposure igény.",
    "Possession": "Stabil volumen, kontrollált intenzitás, fenntartható terhelés.",
    "Low Block": "Rövidebb, robbanékony intenzív blokkok, kontrollált összterhelés.",
}


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


@st.cache_data(show_spinner=False)
def read_excel_all(file) -> Dict[str, pd.DataFrame]:
    return pd.read_excel(file, sheet_name=None)


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

    missing_core = [c for c in CORE_REQUIRED if c not in out.columns]
    if missing_core:
        return out, mapping, missing_core

    out["player_name"] = out["player_name"].astype(str).str.strip()
    out["session_type"] = out["session_type"].apply(normalize_session_type)
    out["start_time"] = pd.to_datetime(out["start_time"], errors="coerce")
    out["session_date"] = out["start_time"].dt.date
    out["week"] = out["start_time"].dt.to_period("W").astype(str)

    if "duration" in out.columns:
        out["duration_min"] = out["duration"].apply(duration_to_minutes)
    else:
        out["duration_min"] = np.nan

    numeric_cols = [
        "total_distance", "distance_per_min", "max_speed", "avg_speed", "sprints",
        "speed_zone_3", "speed_zone_4", "speed_zone_5", "training_load", "cardio_load",
        "recovery_hours", "muscle_load", "hr_avg", "hr_max", "hrv", "acc_low", "acc_mid",
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
    out["high_efforts"] = out[["acc_mid", "acc_high", "dec_mid", "dec_high"]].sum(axis=1, min_count=1)

    if "distance_per_min" not in out.columns or out["distance_per_min"].isna().all():
        if "total_distance" in out.columns:
            out["distance_per_min"] = out["total_distance"] / out["duration_min"]

    out = out.dropna(subset=["start_time"])
    out = out[out["player_name"].str.len() > 0]
    out = out[~out["player_name"].str.lower().str.contains("benchmark|átlag|atlag|összesen|osszesen", na=False)]

    return out, mapping, []


def aggregate_weekly(df: pd.DataFrame) -> pd.DataFrame:
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
        "distance_per_min": "mean",
        "max_speed": "max",
        "hr_avg": "mean",
        "hrv": "mean",
    }
    usable = {k: v for k, v in agg_map.items() if k in df.columns}
    return df.groupby(["week", "session_type"], as_index=False).agg(usable)


def player_weekly(df: pd.DataFrame) -> pd.DataFrame:
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
        "distance_per_min": "mean",
        "max_speed": "max",
        "hr_avg": "mean",
        "hrv": "mean",
    }
    usable = {k: v for k, v in agg_map.items() if k in df.columns}
    return df.groupby(["player_name", "week", "session_type"], as_index=False).agg(usable)


def pct_change(current: float, previous: float) -> Optional[float]:
    if previous is None or pd.isna(previous) or previous == 0 or pd.isna(current):
        return None
    return (current - previous) / previous


def available_metric_options(df: pd.DataFrame, desired: List[str]) -> List[str]:
    return [m for m in desired if m in df.columns and not df[m].isna().all()]


def metric_name(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric)


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

    # Speed exposure: történt-e értelmezhető sprintinger a meccs előtti napokban?
    if not train.empty and "sprint_distance" in daily.columns and not match.empty:
        match_sprint = match["sprint_distance"].mean()
        max_training_sprint = train["sprint_distance"].max()
        if pd.notna(match_sprint) and match_sprint > 0:
            ratio = max_training_sprint / match_sprint if pd.notna(max_training_sprint) else 0
            if ratio < 0.15:
                insights.append(Insight(
                    "Hiányzó speed exposure", "KRITIKUS",
                    f"A héten nem látszik érdemi sprintinger: a legmagasabb edzésnapi sprintterhelés a meccs kb. {ratio:.0%}-a.",
                    "Meccsigényhez képest alacsony lehetett a maximális sebességű inger, ami a felkészítés minőségét ronthatja.",
                    "Érdemes lehet egy rövid, kontrollált speed exposure blokkot betervezni a megfelelő napon, ha a heti cél és a játékosállapot engedi.",
                    scope="Mikrociklus",
                ))
            elif ratio < 0.30:
                insights.append(Insight(
                    "Alacsony speed exposure", "FIGYELMEZTETÉS",
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


def build_weekly_summary(insights: List[Insight], selected_week: str, playstyle: str) -> str:
    if not insights:
        return f"A(z) {selected_week} hét fő mutatói alapján nem látható kiemelt kockázat. A játékmodell: {playstyle}."
    critical = [i for i in insights if i.severity == "KRITIKUS"]
    warning = [i for i in insights if i.severity == "FIGYELMEZTETÉS"]
    info = [i for i in insights if i.severity == "INFORMÁCIÓ"]
    main = critical[0] if critical else (warning[0] if warning else info[0])
    second = None
    for i in insights:
        if i.title != main.title:
            second = i
            break
    text = (
        f"A(z) {selected_week} hét legfontosabb üzenete: {main.title.lower()}. "
        f"{main.observation} {main.recommendation}"
    )
    if second is not None:
        text += f" Második fontos téma: {second.title.lower()}."
    text += f" A kiválasztott játékmodell: {playstyle}."
    return text


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
# V2.5 - Performance Memory + Readiness + Adaptive Intelligence
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

    # 2. Speed exposure
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
                reasons.append("A héten alig látszik speed exposure a meccsigényhez képest.")
            elif ratio < 0.30:
                score -= 7
                reasons.append("A speed exposure visszafogott volt.")
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

    # 5. Readiness végső skála
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
            "Érdemes több heti adatot egy fájlban feltölteni vagy használni a performance memory funkciót.",
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
                "A tartós speed exposure hiány hosszabb távon ronthatja a maximális sebesség és intenzitás fenntartását.",
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
        combined["week"] = combined["start_time"].dt.to_period("W").astype(str)
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
            "Cím": "Readiness elsődleges figyelem",
            "Súlyosság": "KRITIKUS",
            "Teendő": "A következő edzésterhelést érdemes óvatosan kezelni, és a frissességi jeleket külön figyelni.",
            "Miért": "A match readiness score alacsony, több komponens egyszerre jelezhet terhelési vagy frissességi problémát.",
        })
    elif readiness_score < 70:
        recs.append({
            "Cím": "Readiness kontroll",
            "Súlyosság": "FIGYELMEZTETÉS",
            "Teendő": "Tarts kontrollált intenzitást, és csak célzottan terheld a hiányzó elemeket.",
            "Miért": "A readiness közepes tartományban van, ezért a túlzott korrekció is kockázatos lehet.",
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
            "Cím": "Recovery vagy alulterhelés értelmezése",
            "Súlyosság": "INFORMÁCIÓ",
            "Teendő": "Döntsd el, hogy tudatos regenerációs hét volt-e, vagy nem kívánt terhelésvesztés.",
            "Miért": "Az alacsony load lehet hasznos frissítés, de tartósan teljesítményvesztést is okozhat.",
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
        for metric, hi, lo, lab in [("training_load",.30,-.35,"Terhelési pont"),("dec_count",.35,-.40,"Lassítás"),("sprint_distance",.45,-.45,"Sprinttáv")]:
            if metric in row.index and metric in hp.columns:
                v=row.get(metric,np.nan); base=hp[metric].mean()
                if pd.notna(v) and pd.notna(base) and base!=0:
                    d=(v-base)/base
                    if d>hi: score+=18; reasons.append(f"{lab}: +{d:.0%} a saját átlaghoz képest")
                    elif d<lo: score+=8; reasons.append(f"{lab}: {d:.0%} a saját átlaghoz képest")
        if "max_speed" in row.index and "max_speed" in hp.columns:
            v=row.get("max_speed",np.nan); base=hp["max_speed"].max()
            if pd.notna(v) and pd.notna(base) and base>0 and (v-base)/base < -.06:
                score+=14; reasons.append(f"Max sebesség: {(v-base)/base:.0%} a saját csúcshoz képest")
        score=int(max(0,min(100,score))); level="Magas" if score>=70 else ("Közepes" if score>=45 else "Alacsony")
        rows.append({"Játékos":player,"Típus":row.get("session_type",""),"Risk score":score,"Kockázati szint":level,"Fő okok":"; ".join(reasons[:3]) if reasons else "Nincs jelentős eltérés a saját előzményhez képest."})
    res=pd.DataFrame(rows); return res.sort_values("Risk score",ascending=False) if not res.empty else res

def render_premium_kpi(label: str, value: str, note: str="", color: str="#22c55e") -> None:
    st.markdown(f"""<div class='premium-kpi'><div class='premium-kpi-label'>{html.escape(label)}</div><div class='premium-kpi-value' style='color:{color};'>{html.escape(str(value))}</div><div class='premium-kpi-note'>{html.escape(note)}</div></div>""", unsafe_allow_html=True)

def render_hero(selected_week: str, selected_playstyle: str, readiness_score: int, periodization_type: str) -> None:
    color=score_to_color(readiness_score) if "score_to_color" in globals() else "#22c55e"; label=score_to_label(readiness_score) if "score_to_label" in globals() else ""
    st.markdown(f"""<div class='hero-box'><div class='hero-title'>Football Performance Intelligence</div><div class='hero-sub'><span class='section-chip'>Hét: {html.escape(str(selected_week))}</span><span class='section-chip'>Játékmodell: {html.escape(str(selected_playstyle))}</span><span class='section-chip'>Readiness: <b style='color:{color};'>{readiness_score}/100</b> - {html.escape(label)}</span><span class='section-chip'>Periodizáció: {html.escape(str(periodization_type))}</span></div></div>""", unsafe_allow_html=True)

def render_risk_cards(risk_df: pd.DataFrame, limit: int=5) -> None:
    if risk_df.empty: st.info("Nincs elég adat játékosszintű risk engine számításhoz."); return
    for _, row in risk_df.head(limit).iterrows():
        level=row.get("Kockázati szint","Alacsony"); css="risk-high" if level=="Magas" else ("risk-medium" if level=="Közepes" else "risk-low")
        st.markdown(f"""<div class='insight-card {css}'><div class='insight-title'>{html.escape(str(row.get('Játékos','')))} · {html.escape(str(level))} kockázat · {row.get('Risk score',0)}/100</div><div class='insight-label'>Fő okok</div><div class='insight-text'>{html.escape(str(row.get('Fő okok','')))}</div></div>""", unsafe_allow_html=True)

def build_premium_pdf_bytes(insights_df: pd.DataFrame, selected_week: str, readiness_score: int, periodization_type: str, weekly_summary_text: str, coaching_priorities: List[Dict[str,str]], risk_df: pd.DataFrame, playstyle: str) -> Optional[bytes]:
    if SimpleDocTemplate is None: return None
    font_name,font_bold=_register_pdf_font(); output=io.BytesIO(); doc=SimpleDocTemplate(output,pagesize=landscape(A4),rightMargin=.8*cm,leftMargin=.8*cm,topMargin=.8*cm,bottomMargin=.8*cm)
    styles=getSampleStyleSheet(); title=ParagraphStyle("V3Title",parent=styles["Title"],fontName=font_bold,fontSize=21,leading=25,textColor=colors.HexColor("#0F172A")); h2=ParagraphStyle("V3H2",parent=styles["Heading2"],fontName=font_bold,fontSize=13,leading=16,textColor=colors.HexColor("#1F4E78")); body=ParagraphStyle("V3Body",parent=styles["Normal"],fontName=font_name,fontSize=8.5,leading=11); small=ParagraphStyle("V3Small",parent=styles["Normal"],fontName=font_name,fontSize=7,leading=9); header=ParagraphStyle("V3Header",parent=styles["Normal"],fontName=font_bold,fontSize=7,leading=9,textColor=colors.white)
    def P(v,style=body): return Paragraph(html.escape(pdf_safe_text(v)).replace("\n","<br/>",),style)
    story=[P("Football Performance Intelligence - V3 riport",title),P(f"Hét: {selected_week} · Játékmodell: {playstyle} · Generálva: {datetime.now().strftime('%Y-%m-%d %H:%M')}",body),Spacer(1,.25*cm)]
    exec_data=[[P("Match readiness",header),P("Periodizáció",header),P("Vezetői összefoglaló",header)],[P(f"{readiness_score}/100 - {score_to_label(readiness_score)}",body),P(periodization_type,body),P(weekly_summary_text,body)]]
    et=Table(exec_data,colWidths=[5*cm,5*cm,16.5*cm]); et.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0F172A")),("BACKGROUND",(0,1),(-1,1),colors.HexColor("#F1F5F9")),("GRID",(0,0),(-1,-1),.35,colors.HexColor("#CBD5E1")),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)])); story += [et,Spacer(1,.35*cm),P("Top adaptív edzői teendők",h2)]
    if coaching_priorities:
        data=[[P("#",header),P("Téma",header),P("Teendő",header),P("Miért fontos?",header)]]
        for i,it in enumerate(coaching_priorities[:3],1): data.append([P(str(i),small),P(it.get("Cím",""),small),P(it.get("Teendő",""),small),P(it.get("Miért",""),small)])
        t=Table(data,colWidths=[.8*cm,5*cm,10.5*cm,10.2*cm],repeatRows=1); t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1F4E78")),("GRID",(0,0),(-1,-1),.25,colors.HexColor("#CBD5E1")),("VALIGN",(0,0),(-1,-1),"TOP"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F8FAFC")]),("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)])); story.append(t)
    if risk_df is not None and not risk_df.empty:
        story += [Spacer(1,.35*cm),P("Top játékos risk lista",h2)]; cols=["Játékos","Risk score","Kockázati szint","Fő okok"]; data=[[P(c,header) for c in cols]]
        for _,r in risk_df.head(8).iterrows(): data.append([P(r.get(c,""),small) for c in cols])
        rt=Table(data,colWidths=[5.2*cm,2.3*cm,3.2*cm,15.8*cm],repeatRows=1); rt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#7F1D1D")),("GRID",(0,0),(-1,-1),.25,colors.HexColor("#CBD5E1")),("VALIGN",(0,0),(-1,-1),"TOP"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#FFF7ED")]),("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)])); story.append(rt)
    story += [Spacer(1,.35*cm),P("Insight tábla",h2)]; cols=["Súlyosság","Terület","Megállapítás","Mit látunk?","Miért fontos?","Javaslat"]; cols=[c for c in cols if c in insights_df.columns]; data=[[P(c,header) for c in cols]]
    for _,r in insights_df.iterrows(): data.append([P(r.get(c,""),small) for c in cols])
    widths={"Súlyosság":2.5*cm,"Terület":2*cm,"Megállapítás":3.7*cm,"Mit látunk?":5.7*cm,"Miért fontos?":5.7*cm,"Javaslat":6.9*cm}; tab=Table(data,colWidths=[widths.get(c,3*cm) for c in cols],repeatRows=1); tab.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1F4E78")),("GRID",(0,0),(-1,-1),.25,colors.HexColor("#BFBFBF")),("VALIGN",(0,0),(-1,-1),"TOP"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F7F9FC")]),("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)])); story.append(tab)
    doc.build(story); return output.getvalue()

# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------
st.title("⚽ Football Performance Intelligence – V3")
st.caption("Premium performance cockpit → readiness → risk engine → posztlogika → cool export")

with st.sidebar:
    st.header("1) Adatfeltöltés")
    uploaded = st.file_uploader("Tölts fel Excel fájlt", type=["xlsx", "xls"])
    st.divider()
    st.markdown("**MVP fókusz:** edzői döntéstámogatás, nem sérülésdiagnosztika.")

if uploaded is None:
    st.info("Tölts fel egy GPS/terhelési Excel fájlt a kezdéshez.")
    st.stop()

sheets = read_excel_all(uploaded)
sheet_names = list(sheets.keys())

with st.sidebar:
    selected_sheet = st.selectbox("Melyik munkalapot használjuk?", sheet_names, index=0)

raw_df = sheets[selected_sheet]
df, mapping, missing_core = standardize_dataframe(raw_df)
df = add_position_group(df)

if missing_core:
    st.error(f"Hiányzó alapmezők: {', '.join(missing_core)}")
    st.write("Oszlopmapping:", mapping)
    st.stop()

weeks = sorted(df["week"].dropna().unique().tolist())
players = sorted(df["player_name"].dropna().unique().tolist())
session_types = sorted(df["session_type"].dropna().unique().tolist())

with st.sidebar:
    st.header("2) Szűrők")
    selected_week = st.selectbox("Hét", weeks, index=len(weeks) - 1 if weeks else 0)
    selected_playstyle = st.selectbox("Játékmodell", list(PLAYSTYLE_OPTIONS.keys()), index=0)
    st.caption(PLAYSTYLE_OPTIONS[selected_playstyle])
    selected_types = st.multiselect("Típus", session_types, default=session_types)
    selected_players = st.multiselect("Játékosok", players, default=players)

    st.header("3) Performance memory")
    use_memory = st.checkbox("Korábbi mentett adatok bevonása", value=False)
    save_current_to_memory = st.button("Aktuális feltöltés mentése memoryba", use_container_width=True)

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
weekly_summary_text += f" Readiness: {readiness_score}/100 ({score_to_label(readiness_score)}). Periodizációs besorolás: {periodization_type}."
player_risk_df = calculate_player_risk(analysis_base_df, selected_week)
high_risk_count = int((player_risk_df["Kockázati szint"] == "Magas").sum()) if not player_risk_df.empty else 0
medium_risk_count = int((player_risk_df["Kockázati szint"] == "Közepes").sum()) if not player_risk_df.empty else 0

# Tabok
tab1, tab_premium, tab_intel, tab_micro, tab_risk, tab2, tab3, tab4, tab5 = st.tabs([
    "Vezetői áttekintő",
    "Premium cockpit",
    "Intelligence cockpit",
    "Mikrociklus intelligencia",
    "Player risk engine",
    "Megállapítások és javaslatok",
    "Játékosmonitoring",
    "Adatminőség",
    "Nyers adatok",
])

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
    st.info(weekly_summary_text)
    r1, r2, r3 = st.columns(3)
    with r1:
        st.metric("Match readiness", f"{readiness_score}/100", score_to_label(readiness_score))
    with r2:
        st.metric("Periodizáció", periodization_type)
    with r3:
        mem_weeks = analysis_base_df["week"].nunique() if "week" in analysis_base_df.columns else 0
        st.metric("Elemzett hetek", mem_weeks)
    st.markdown("### Top 3 adaptív edzői teendő")
    render_coaching_priorities(coaching_priorities)

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
    st.subheader("Premium cockpit")
    st.caption("Cool vezetői nézet: readiness, risk, load, sprint, periodizáció és top teendők egy képernyőn.")
    render_hero(selected_week, selected_playstyle, readiness_score, periodization_type)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_premium_kpi("Match readiness", f"{readiness_score}/100", score_to_label(readiness_score), score_to_color(readiness_score))
    with k2:
        render_premium_kpi("Magas risk játékos", str(high_risk_count), "Player risk engine alapján", "#ef4444" if high_risk_count else "#22c55e")
    with k3:
        mem_weeks = analysis_base_df["week"].nunique() if "week" in analysis_base_df.columns else 0
        render_premium_kpi("Elemzett hetek", str(mem_weeks), "Memory + aktuális feltöltés", "#38bdf8")
    with k4:
        render_premium_kpi("Periodizáció", periodization_type, "Automatikus heti besorolás", "#a78bfa")
    st.markdown("### Readiness komponensek")
    if readiness_components:
        comp_df = pd.DataFrame([{"Komponens": k, "Pont": round(v, 1)} for k, v in readiness_components.items()])
        fig = px.bar(comp_df, x="Komponens", y="Pont", range_y=[0, 100], title="Readiness komponensek")
        fig.update_layout(xaxis_title="", yaxis_title="Pont", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("### Top adaptív edzői teendők")
    render_coaching_priorities(coaching_priorities)
    st.markdown("### Top player risk")
    render_risk_cards(player_risk_df, limit=5)
    if weekly_fingerprints is not None and not weekly_fingerprints.empty:
        st.markdown("### Multi-week performance fingerprint")
        trend_metric_options = [c for c in ["training_load", "sprint_distance", "distance_per_min", "max_speed", "dec_count"] if c in weekly_fingerprints.columns]
        if trend_metric_options:
            tm = st.selectbox("Premium trend mutató", trend_metric_options, format_func=metric_name)
            fig = px.line(weekly_fingerprints, x="week", y=tm, markers=True, title=f"Performance memory trend: {metric_name(tm)}")
            fig.update_layout(xaxis_title="Hét", yaxis_title=metric_name(tm), template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

with tab_intel:
    st.subheader("Intelligence cockpit")
    st.caption("V2.5: readiness score, periodizáció, performance memory, multi-week mintázatok és adaptív ajánlások.")

    c1, c2 = st.columns([1, 1])
    with c1:
        render_score_card(
            "Match readiness",
            readiness_score,
            score_to_label(readiness_score),
            readiness_reasons,
        )
    with c2:
        st.markdown("### Readiness komponensek")
        if readiness_components:
            comp_df = pd.DataFrame([
                {"Komponens": k, "Pont": round(v, 1)}
                for k, v in readiness_components.items()
            ])
            fig = px.bar(comp_df, x="Komponens", y="Pont", range_y=[0, 100], title="Readiness komponensek")
            fig.update_layout(xaxis_title="", yaxis_title="Pont")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nincs elég adat a komponensekhez.")

    st.markdown("### Periodizációs besorolás")
    st.info(f"Az aktuális hét besorolása: **{periodization_type}**")

    st.markdown("### Weekly fingerprint / performance memory")
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
            tm = st.selectbox("Memory trend mutató", trend_metric_options, format_func=metric_name)
            fig = px.line(weekly_fingerprints, x="week", y=tm, markers=True, title=f"Multi-week trend: {metric_name(tm)}")
            fig.update_layout(xaxis_title="Hét", yaxis_title=metric_name(tm))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Multi-week mintázatok")
    if pattern_insights:
        render_insight_cards(pattern_insights)
    else:
        st.success("Nem látható kiemelt többhetes negatív mintázat az aktuális adatok alapján.")

    st.markdown("### Adaptív ajánlórendszer")
    render_coaching_priorities(coaching_priorities)


with tab_micro:
    st.subheader("Mikrociklus intelligencia")
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


with tab_risk:
    st.subheader("Player risk engine")
    st.caption("Játékosszintű, többhetes eltérésalapú risk scoring: load spike, sprintprofil, lassítások, max sebesség.")
    if player_risk_df.empty:
        st.info("Nincs elég adat a játékosszintű risk engine-hez. Legalább több hét játékosszintű adat kell hozzá.")
    else:
        render_risk_cards(player_risk_df, limit=8)
        st.markdown("### Risk tábla")
        st.dataframe(player_risk_df, use_container_width=True, hide_index=True)
        fig = px.bar(player_risk_df.head(20), x="Játékos", y="Risk score", color="Kockázati szint", title="Játékos risk score")
        fig.update_layout(xaxis_title="Játékos", yaxis_title="Risk score", xaxis_tickangle=-45, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        st.download_button("⬇️ Player risk export CSV", data=player_risk_df.to_csv(index=False).encode("utf-8-sig"), file_name=f"player_risk_{_safe_filename_week(selected_week)}.csv", mime="text/csv", use_container_width=True)

with tab2:
    st.subheader("Megállapítások és javaslatok")
    st.caption("Szabályalapú performance motor: AI nélkül is ad szakmai következtetést és javaslatot.")

    insights = all_insights

    st.markdown("### Heti összefoglaló")
    st.info(weekly_summary_text)

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
        )
    with c2:
        csv_bytes = insight_export_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ CSV",
            data=csv_bytes,
            file_name=f"performance_riport_{safe_week}.csv",
            mime="text/csv",
            use_container_width=True,
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
            )
        else:
            st.info("PDF exporthoz add hozzá a requirements.txt fájlhoz: reportlab")
    st.markdown("#### Premium V3 PDF export")
    premium_pdf = build_premium_pdf_bytes(insight_export_df, selected_week, readiness_score, periodization_type, weekly_summary_text, coaching_priorities, player_risk_df, selected_playstyle)
    if premium_pdf is not None:
        st.download_button("⬇️ Premium V3 PDF riport", data=premium_pdf, file_name=f"premium_performance_riport_{safe_week}.pdf", mime="application/pdf", use_container_width=True)

with tab3:
    st.subheader("Játékosmonitoring")
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
    st.subheader("Adatminőség")
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

    st.markdown("### Performance memory állapot")
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
st.caption("V2.5 HU – Performance memory, readiness scoring, periodizáció, multi-week mintázatok, adaptív ajánlórendszer.")
