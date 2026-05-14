# performance_app_v1.py
# AI-Assisted Performance Recommendation System - MVP V1
# Streamlit app: upload -> standardization -> KPI engine -> insight/recommendation engine

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="Performance Recommendation System MVP",
    page_icon="⚽",
    layout="wide",
)


# -----------------------------
# Constants / metric mapping
# -----------------------------
STANDARD_COLUMNS = {
    "player_name": ["Játékos neve", "Player", "Player Name", "Name", "Név"],
    "session_type": ["Típus", "Type", "Session Type", "Edzés/Meccs"],
    "session_name": ["Szakasz neve", "Session", "Session Name"],
    "start_time": ["Kezdési idő", "Start Time", "Start", "Dátum", "Date"],
    "end_time": ["Befejezési idő", "End Time", "End"],
    "duration": ["Időtartam", "Duration", "Time"],
    "total_distance": ["Tel\xadjes táv [m]", "Teljes táv [m]", "Total Distance", "Distance", "Össztáv"],
    "distance_per_min": ["Táv/perc [m/min]", "Distance/min", "Distance Per Min", "m/min"],
    "max_speed": ["Maximális sebesség [km/h]", "Max Speed", "Maximum Speed"],
    "avg_speed": ["Átlagsebesség [km/h]", "Average Speed", "Avg Speed"],
    "sprints": ["Sprintek", "Sprints", "Sprint Count"],
    "speed_zone_3": ["Táv a sebesség célzónában 3 [m] (14.40 - 19.79 km/h)"],
    "speed_zone_4": ["Táv a sebesség célzónában 4 [m] (19.80 - 24.99 km/h)"],
    "speed_zone_5": ["Táv a sebesség célzónában 5 [m] (25.00- km/h)"],
    "training_load": ["Edzési terhelési pontérték", "Training Load", "Player Load", "Load"],
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


@dataclass
class Insight:
    title: str
    severity: str
    observation: str
    impact: str
    recommendation: str
    scope: str = "Team"

    def as_dict(self) -> Dict[str, str]:
        return {
            "Severity": self.severity,
            "Scope": self.scope,
            "Title": self.title,
            "Observation": self.observation,
            "Impact": self.impact,
            "Recommendation": self.recommendation,
        }


# -----------------------------
# Utility functions
# -----------------------------
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
    # fuzzy contains fallback
    for alias in aliases:
        a = clean_col_name(alias).lower()
        for c in df.columns:
            cc = clean_col_name(c).lower()
            if a and (a in cc or cc in a):
                return c
    return None


def to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def duration_to_minutes(x) -> float:
    if pd.isna(x):
        return np.nan
    if isinstance(x, pd.Timedelta):
        return x.total_seconds() / 60
    if hasattr(x, "hour") and hasattr(x, "minute") and hasattr(x, "second"):
        return x.hour * 60 + x.minute + x.second / 60
    if isinstance(x, str):
        # Try formats like HH:MM:SS
        try:
            td = pd.to_timedelta(x)
            return td.total_seconds() / 60
        except Exception:
            return np.nan
    if isinstance(x, (int, float)):
        # Excel time fraction fallback: values under 2 are probably day fractions
        if x < 2:
            return x * 24 * 60
        return float(x)
    return np.nan


def normalize_session_type(x: object) -> str:
    text = str(x).strip().lower()
    if "meccs" in text or "match" in text or "game" in text:
        return "Meccs"
    if "edzés" in text or "training" in text:
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

    # Derived fields
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

    # Remove empty/bad rows
    out = out.dropna(subset=["start_time"])
    out = out[out["player_name"].str.len() > 0]
    out = out[~out["player_name"].str.lower().str.contains("benchmark|átlag|összesen", na=False)]

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

    # 1. Sprint underload: training sprint per session/player vs match sprint per session/player
    if not cur_train.empty and not cur_match.empty:
        train_sprint = cur_train["sprint_distance"].mean()
        match_sprint = cur_match["sprint_distance"].mean()
        if match_sprint and match_sprint > 0:
            ratio = train_sprint / match_sprint
            if ratio < 0.65:
                insights.append(Insight(
                    "Sprint underload", "CRITICAL",
                    f"Az edzés sprintterhelése a meccsterhelés kb. {ratio:.0%}-a.",
                    "A nagy intenzitású terhelés jelentősen elmaradhat a mérkőzésigénytől.",
                    "Érdemes lehet célzott sprint- vagy nagysebességű blokkokat beépíteni, ha ez illeszkedik a heti periodizációhoz.",
                ))
            elif ratio < 0.80:
                insights.append(Insight(
                    "Sprint underload", "WARNING",
                    f"Az edzés sprintterhelése a meccsterhelés kb. {ratio:.0%}-a.",
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
                    "Weekly load spike", "WARNING",
                    f"Az edzés terhelési pontértéke {chg:.0%}-kal nőtt az előző héthez képest.",
                    "A hirtelen terhelésemelkedés ronthatja a heti frissességet.",
                    "Érdemes figyelni a következő edzések intenzitását és a játékosok egyéni válaszait.",
                ))
            elif chg < -0.25:
                insights.append(Insight(
                    "Weekly load drop", "INFO",
                    f"Az edzés terhelési pontértéke {abs(chg):.0%}-kal csökkent az előző héthez képest.",
                    "Ez lehet tudatos tapering, de lehet nem kívánt terhelésvesztés is.",
                    "Érdemes kontextusba helyezni: meccs előtti frissítés, hiányzók vagy edzéstartalom-váltás okozta-e.",
                ))

    # 3. Match intensity gap
    if not cur_train.empty and not cur_match.empty:
        train_int = cur_train["distance_per_min"].mean()
        match_int = cur_match["distance_per_min"].mean()
        if match_int and match_int > 0:
            ratio = train_int / match_int
            if ratio < 0.85:
                insights.append(Insight(
                    "Match intensity gap", "WARNING",
                    f"Az edzés átlagos táv/perc értéke a meccs kb. {ratio:.0%}-a.",
                    "A csapat edzésintenzitása elmaradhat a mérkőzés tempójától.",
                    "Érdemes lehet rövidebb, intenzívebb játékszituációkat vagy tempóváltásokat használni.",
                ))

    # 4. High deceleration load
    if not cur_train.empty and not prev_train.empty:
        cur_dec = cur_train["dec_count"].mean()
        prev_dec = prev_train["dec_count"].mean()
        chg = pct_change(cur_dec, prev_dec)
        if chg is not None and chg > 0.35:
            insights.append(Insight(
                "High deceleration load", "WARNING",
                f"Az átlagos lassításszám {chg:.0%}-kal nőtt az előző héthez képest.",
                "A lassítások nagy neuromuszkuláris terhelést jelenthetnek.",
                "Érdemes figyelni a regenerációra és a következő edzés excentrikus terhelésére.",
            ))

    # 5. Max speed suppression
    if not cur_train.empty and not prev_train.empty:
        cur_speed = cur_train["max_speed"].max()
        prev_speed = prev_train["max_speed"].max()
        chg = pct_change(cur_speed, prev_speed)
        if chg is not None and chg < -0.05:
            insights.append(Insight(
                "Max speed suppression", "INFO",
                f"A heti maximális sebesség {abs(chg):.0%}-kal alacsonyabb az előző hétnél.",
                "Ez jelezhet alacsonyabb neuromuszkuláris frissességet, de lehet edzéstartalom-függő is.",
                "Érdemes megnézni, volt-e valódi max sebességű inger a héten.",
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
                    "Player load outliers", "WARNING",
                    f"Néhány játékos jelentősen a csapatátlag felett terhelődött: {names}.",
                    "Egyéni terheléskülönbség alakult ki a héten.",
                    "Érdemes egyéni szinten ránézni a következő edzés terhelésére és a játékpercekre.",
                    scope="Player",
                ))
            if len(low) > 0:
                names = ", ".join(low.head(3).index.tolist())
                insights.append(Insight(
                    "Low load outliers", "INFO",
                    f"Néhány játékos jelentősen a csapatátlag alatt terhelődött: {names}.",
                    "Terheléslemaradás alakulhat ki, főleg ha ez több héten át fennáll.",
                    "Érdemes ellenőrizni a hiányzásokat, játékperceket és egyéni kiegészítő munkát.",
                    scope="Player",
                ))

    # If no insights, return positive summary
    if not insights:
        insights.append(Insight(
            "Stable week", "INFO",
            "Nem látható kiemelt negatív eltérés az aktuális hét fő mutatóiban.",
            "A csapat terhelési profilja stabilnak tűnik az elérhető adatok alapján.",
            "Érdemes tovább figyelni a sprint- és intenzitási trendeket, különösen meccs előtti héten.",
        ))

    severity_rank = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    return sorted(insights, key=lambda x: severity_rank.get(x.severity, 9))[:8]


def style_severity(sev: str) -> str:
    if sev == "CRITICAL":
        return "🔴 CRITICAL"
    if sev == "WARNING":
        return "🟠 WARNING"
    return "🔵 INFO"


def metric_card(label: str, value: object, help_text: str = ""):
    st.metric(label, value if value is not None else "—", help=help_text)


# -----------------------------
# UI
# -----------------------------
st.title("⚽ Performance Recommendation System MVP")
st.caption("Streamlit MVP: adatfeltöltés → KPI-k → insightok → ajánlások")

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

if missing_core:
    st.error(f"Hiányzó alapmezők: {', '.join(missing_core)}")
    st.write("Oszlopmapping:", mapping)
    st.stop()

# Sidebar filters
weeks = sorted(df["week"].dropna().unique().tolist())
players = sorted(df["player_name"].dropna().unique().tolist())
session_types = sorted(df["session_type"].dropna().unique().tolist())

with st.sidebar:
    st.header("2) Szűrők")
    selected_week = st.selectbox("Hét", weeks, index=len(weeks) - 1 if weeks else 0)
    selected_types = st.multiselect("Típus", session_types, default=session_types)
    selected_players = st.multiselect("Játékosok", players, default=players)

filtered = df[(df["week"] == selected_week) & (df["session_type"].isin(selected_types)) & (df["player_name"].isin(selected_players))]

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Team Command Center", "Insights & Recommendations", "Player Monitoring", "Data Quality", "Raw Data"
])

with tab1:
    st.subheader("Team Command Center")
    st.caption("A főoldal célja: 30 másodperc alatt látni, mi fontos a héten.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Játékosok", filtered["player_name"].nunique())
    with col2:
        metric_card("Session sorok", len(filtered))
    with col3:
        td = filtered["total_distance"].sum() if "total_distance" in filtered.columns else np.nan
        metric_card("Össztáv", f"{td:,.0f} m" if pd.notna(td) else "—")
    with col4:
        load = filtered["training_load"].sum() if "training_load" in filtered.columns else np.nan
        metric_card("Training Load", f"{load:,.0f}" if pd.notna(load) else "—")

    weekly = aggregate_weekly(df[df["session_type"].isin(selected_types)])
    st.markdown("### Heti trendek")
    chart_metric = st.selectbox(
        "Trend mutató",
        [m for m in ["training_load", "total_distance", "sprint_distance", "hsr_distance", "distance_per_min", "max_speed", "dec_count"] if m in weekly.columns],
        index=0,
    )
    fig = px.line(
        weekly,
        x="week",
        y=chart_metric,
        color="session_type",
        markers=True,
        title=f"Heti trend: {chart_metric}",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Edzés vs meccs profil az aktuális héten")
    profile_cols = ["total_distance", "distance_per_min", "sprint_distance", "hsr_distance", "max_speed", "dec_count"]
    usable_profile = [c for c in profile_cols if c in filtered.columns]
    if usable_profile:
        prof = filtered.groupby("session_type", as_index=False)[usable_profile].mean(numeric_only=True)
        st.dataframe(prof, use_container_width=True)

with tab2:
    st.subheader("Insights & Recommendations")
    st.caption("Szabályalapú performance engine: AI nélkül is ad konklúziót és ajánlást.")
    insights = team_insights(df[df["player_name"].isin(selected_players)], selected_week)
    for ins in insights:
        with st.container(border=True):
            st.markdown(f"### {style_severity(ins.severity)} · {ins.title}")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**Observation**")
                st.write(ins.observation)
            with c2:
                st.markdown("**Impact**")
                st.write(ins.impact)
            with c3:
                st.markdown("**Recommendation**")
                st.write(ins.recommendation)

    st.markdown("### Exportálható insight tábla")
    st.dataframe(pd.DataFrame([i.as_dict() for i in insights]), use_container_width=True)

with tab3:
    st.subheader("Player Monitoring")
    pw = player_weekly(df)
    pw_current = pw[(pw["week"] == selected_week) & (pw["player_name"].isin(selected_players))]
    if not pw_current.empty:
        metric = st.selectbox(
            "Játékos rangsor mutató",
            [m for m in ["training_load", "total_distance", "sprint_distance", "hsr_distance", "max_speed", "dec_count", "high_efforts"] if m in pw_current.columns],
            index=0,
        )
        rank = pw_current.groupby("player_name", as_index=False)[metric].sum().sort_values(metric, ascending=False)
        fig = px.bar(rank.head(25), x="player_name", y=metric, title=f"Játékos ranking: {metric}")
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Játékos heti aggregált tábla")
        st.dataframe(pw_current, use_container_width=True)
    else:
        st.info("Nincs adat az aktuális szűrésre.")

with tab4:
    st.subheader("Data Quality")
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

    st.markdown("### Automatikus oszlopmapping")
    map_df = pd.DataFrame([
        {"standard_column": k, "source_column": v if v is not None else "NINCS"}
        for k, v in mapping.items()
    ])
    st.dataframe(map_df, use_container_width=True)

    st.markdown("### Hiányzó értékek a standard mezőkben")
    na = df.isna().mean().sort_values(ascending=False).reset_index()
    na.columns = ["column", "missing_ratio"]
    st.dataframe(na.head(30), use_container_width=True)

with tab5:
    st.subheader("Raw / Standardized Data")
    st.markdown("### Standardizált adat")
    st.dataframe(df.head(500), use_container_width=True)
    st.markdown("### Nyers adat")
    st.dataframe(raw_df.head(200), use_container_width=True)


st.divider()
st.caption("MVP V1 – szabályalapú engine. Következő lépés: finomított szabályok, benchmarkok, PDF riport, majd AI summary layer.")
