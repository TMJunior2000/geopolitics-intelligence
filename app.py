import streamlit as st
import pandas as pd
from services.db_service import DBService

# Setup
st.set_page_config(page_title="Trading Intelligence DSS", layout="wide")
db = DBService()

st.title("📊 Trading Intelligence Dashboard")
st.markdown("### Macro Insights + Technical Signals Confluence")

# 1. Recupero Dati
insights_data, signals_data = db.get_dashboard_data()

# Convertiamo in DataFrame per facilità
if insights_data:
    df_insights = pd.DataFrame(insights_data)
    # Appiattiamo il JSON annidato di intelligence_feed
    df_insights['source'] = df_insights['intelligence_feed'].apply(lambda x: x['title'] if x else 'N/A')
    df_insights['date'] = df_insights['intelligence_feed'].apply(lambda x: x['published_at'] if x else 'N/A')
else:
    df_insights = pd.DataFrame()

if signals_data:
    df_signals = pd.DataFrame(signals_data)
else:
    df_signals = pd.DataFrame()

# 2. Sidebar: Filtri
st.sidebar.header("Filters")
selected_asset = st.sidebar.text_input("Search Ticker (es. XAUUSD)", "").upper()

# 3. Main View: Confluence Board
col1, col2 = st.columns(2)

with col1:
    st.subheader("📡 Macro Sentiment (Ultimi Video)")
    if not df_insights.empty:
        # Filtro
        view_df = df_insights
        if selected_asset:
            view_df = df_insights[df_insights['asset_ticker'].str.contains(selected_asset, na=False)]
        
        for _, row in view_df.iterrows():
            sentiment_color = "🟢" if row['sentiment'] == "BULLISH" else "🔴" if row['sentiment'] == "BEARISH" else "⚪"
            with st.expander(f"{sentiment_color} {row['asset_ticker']} | {row['timeframe']}"):
                st.write(f"**Reasoning:** {row['ai_reasoning']}")
                st.write(f"**Levels:** {row['key_levels']}")
                st.caption(f"Source: {row['source']} ({row['date']})")
    else:
        st.info("Nessun insight recente.")

with col2:
    st.subheader("📈 Technical Signals (FVG / Price Action)")
    if not df_signals.empty:
        view_sig = df_signals
        if selected_asset:
            view_sig = df_signals[df_signals['asset_ticker'].str.contains(selected_asset, na=False)]
            
        for _, row in view_sig.iterrows():
            st.warning(f"🔔 {row['asset_ticker']} - {row['pattern']} ({row['direction']})")
            st.write(f"Status: **{row['status']}**")
            st.write(f"Notes: {row['notes']}")
    else:
        st.info("Nessun segnale tecnico attivo. Inseriscine uno nel DB.")

# 4. Sezione Inserimento Manuale Segnali (Per te)
st.sidebar.markdown("---")
st.sidebar.subheader("📝 Add Manual Signal")
with st.sidebar.form("add_signal"):
    new_ticker = st.text_input("Ticker").upper()
    new_pattern = st.selectbox("Pattern", ["FVG_H4", "BREAKOUT", "RETEST"])
    new_dir = st.selectbox("Direction", ["LONG", "SHORT"])
    submit = st.form_submit_button("Save Signal")
    
    if submit and new_ticker:
        db.client.table("technical_signals").insert({
            "asset_ticker": new_ticker,
            "pattern": new_pattern,
            "direction": new_dir,
            "status": "PENDING"
        }).execute()
        st.sidebar.success("Segnale salvato!")