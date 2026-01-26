import os
import json
import datetime as dt

import streamlit as st
import pandas as pd
from supabase import create_client, Client

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Geopolitical Intelligence",
    layout="wide",
    page_icon="🌍"
)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# SIDEBAR
# =========================
st.sidebar.title("🌐 Intelligence Filters")

mode = st.sidebar.radio(
    "Modalità",
    ["LIVE (ultime 24h)", "STORICO"]
)

keyword = st.sidebar.text_input("🔍 Cerca keyword")

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
def load_sources():
    res = supabase.table("sources").select("*").execute()
    return {s["id"]: s["name"] for s in res.data}


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

df["published_at"] = pd.to_datetime(df["published_at"])

if mode == "LIVE (ultime 24h)":
    cutoff = dt.datetime.utcnow() - dt.timedelta(hours=24)
    df = df[df["published_at"] >= cutoff]

if date_from and date_to:
    df = df[
        (df["published_at"].dt.date >= date_from) &
        (df["published_at"].dt.date <= date_to)
    ]

if keyword:
    df = df[
        df["title"].str.contains(keyword, case=False, na=False) |
        df["content"].str.contains(keyword, case=False, na=False)
    ]

# =========================
# UI
# =========================
st.title("🌍 Geopolitical Intelligence Feed")

st.caption(
    f"Fonti monitorate: {', '.join(set(sources.values()))}"
)

st.markdown("---")

for _, row in df.iterrows():
    source_name = sources.get(row["source_id"], "Unknown")

    with st.container():
        col1, col2 = st.columns([3, 1])

        with col1:
            st.subheader(row["title"])
            st.caption(
                f"🗞️ {source_name} | 🕒 {row['published_at']}"
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

                    st.markdown("**Summary**")
                    st.write(analysis.get("summary", analysis))

                    st.markdown("**Paesi Coinvolti**")
                    st.write(", ".join(analysis.get("countries_involved", [])))

                    st.markdown("**Livello di Rischio**")
                    st.write(analysis.get("risk_level", "N/A"))

                    st.markdown("**Keywords**")
                    st.write(", ".join(analysis.get("keywords", [])))

                except Exception:
                    st.json(row["analysis"])

        st.markdown("---")
