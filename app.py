import os
import json
import datetime as dt
from typing import Dict, Any, cast
from typing import List
import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Geopolitical Intelligence",
    layout="wide",
    page_icon="🌍"
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Variabili d'ambiente SUPABASE mancanti")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# SIDEBAR
# =========================
st.sidebar.title("🌐 Intelligence Filters")

mode = st.sidebar.radio(
    "Modalità",
    ["LIVE (ultime 24h)", "STORICO"]
)

keyword = st.sidebar.text_input("🔍 Cerca keyword", "")

date_from = None
date_to = None

if mode == "STORICO":
    date_from = st.sidebar.date_input(
        "Da",
        value=dt.date(2026, 1, 1)
    )
    date_to = st.sidebar.date_input(
        "A",
        value=dt.date(2026, 1, 25)
    )

# =========================
# DATA LOADING
# =========================
@st.cache_data(ttl=300)
def load_sources() -> dict[str, str]:
    res = supabase.table("sources").select("id,name").execute()

    raw = res.data or []

    data = cast(List[Dict[str, Any]], raw)

    return {str(s["id"]): str(s["name"]) for s in data}

@st.cache_data(ttl=300)
def load_feed():
    res = (
        supabase
        .table("intelligence_feed")
        .select("*")
        .order("published_at", desc=True)
        .execute()
    )
    return res.data


sources = load_sources()
feed = load_feed()

# =========================
# FILTERING
# =========================
df = pd.DataFrame(feed)

if df.empty:
    st.warning("Nessun dato disponibile.")
    st.stop()

df["published_at"] = pd.to_datetime(
    df["published_at"],
    errors="coerce",
    utc=True
)

df["content"] = df["content"].fillna("")

now_utc = dt.datetime.now(dt.timezone.utc)

if mode == "LIVE (ultime 24h)":
    cutoff = now_utc - dt.timedelta(hours=24)
    df = df[df["published_at"] >= cutoff]

if date_from is not None and date_to is not None:
    start = pd.Timestamp(date_from, tz="UTC")
    end = pd.Timestamp(date_to, tz="UTC") + pd.Timedelta(days=1)

    df = df[
        (df["published_at"] >= start) &
        (df["published_at"] < end)
    ]

if keyword:
    df = df[
        df["title"].str.contains(keyword, case=False, na=False) |
        df["content"].str.contains(keyword, case=False, na=False)
    ]

df = df.sort_values("published_at", ascending=False)

# =========================
# UI
# =========================
st.title("🌍 Geopolitical Intelligence Feed")

st.caption(
    f"Fonti monitorate: {', '.join(sorted(set(sources.values())))}"
)

st.markdown("---")

for _, row in df.iterrows():
    source_name = sources.get(row["source_id"], "Unknown")

    with st.container():
        col1, col2 = st.columns([4, 1])

        with col1:
            st.subheader(row["title"])
            st.caption(
                f"🗞️ {source_name} | 🕒 {row['published_at'].strftime('%Y-%m-%d %H:%M UTC')}"
            )

        with col2:
            if row["url"].startswith("http"):
                st.link_button("Apri Fonte", row["url"])

        with st.expander("📄 Contenuto / Trascrizione"):
            st.write(row["content"][:5000])

        if row["analysis"]:
            with st.expander("🧠 Analisi Geopolitica (AI)"):
                try:
                    analysis = row["analysis"]

                    if isinstance(analysis, str):
                        analysis = json.loads(analysis)

                    st.markdown("**📝 Summary**")
                    st.write(analysis.get("summary", "N/A"))

                    st.markdown("**🌍 Paesi Coinvolti**")
                    st.write(", ".join(analysis.get("countries_involved", [])) or "N/A")

                    st.markdown("**⚠️ Livello di Rischio**")
                    st.write(analysis.get("risk_level", "N/A"))

                    st.markdown("**🏷️ Keywords**")
                    st.write(", ".join(analysis.get("keywords", [])) or "N/A")

                except Exception as e:
                    st.error("Errore parsing analisi AI")
                    st.json(row["analysis"])

        st.markdown("---")
