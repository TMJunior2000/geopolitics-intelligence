import streamlit as st
import pandas as pd
import re

# --- UTILS ---
def _get_youtube_thumbnail(url):
    """Estrae la thumbnail HQ da un URL YouTube."""
    if not url: return None
    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', str(url))
    if video_id_match:
        return f"https://img.youtube.com/vi/{video_id_match.group(1)}/hqdefault.jpg"
    return None

def _generate_html_card(row, card_type="VIDEO"):
    """
    Genera l'HTML puro della card Worldy-Style.
    Gestisce liste di ticker e sfondi dinamici.
    """
    
    # 1. Gestione Ticker Multipli o Singoli
    tickers = row.get('asset_ticker')
    if not isinstance(tickers, list): 
        tickers = [tickers] if tickers else []
    
    # Pulizia: rimuovi None e duplicati, ordina
    tickers = sorted(list(set([str(t) for t in tickers if t])))
    
    # Creazione Badge HTML per i ticker
    tickers_html = ""
    for t in tickers:
        tickers_html += f'<span class="ticker-badge">{t}</span>'

    # 2. Dati Testuali e Pulizia
    summary = row.get('summary_card') or row.get('video_summary') or "Nessuna descrizione."
    # Escape delle virgolette per non rompere l'HTML
    summary = str(summary).replace('"', '&quot;')
    
    # 3. Gestione Data (Solo Published At)
    try:
        raw_date = row.get('published_at')
        if isinstance(raw_date, pd.Series): raw_date = raw_date.iloc[0]
        
        if pd.isna(raw_date):
            date_str = "N.D."
        else:
            date_str = pd.to_datetime(raw_date).strftime("%d %b")
    except:
        date_str = "N.D."

    # 4. Stili e Sfondi
    bg_style = ""
    if card_type == "TRUMP":
        badge_text = "TRUMP WATCH"
        badge_class = "badge-trump"
        # Gradiente "Presidential"
        bg_style = "background: linear-gradient(135deg, #002D72 0%, #C8102E 100%);"
        
        # Titolo corto per Trump
        display_title = summary[:110] + "..." if len(summary) > 110 else summary
        
        score = row.get('impact_score', 0)
        if isinstance(score, (list, pd.Series)): score = max(score)
        footer_info = f"IMPACT: {score}/5"
        score_color = "#E74C3C" if score >= 4 else "#F1C40F"
        
    else: # VIDEO
        badge_text = row.get('channel_style', 'ANALYSIS')
        if isinstance(badge_text, pd.Series): badge_text = badge_text.iloc[0]
        badge_class = "badge-video"
        
        video_url = row.get('video_url') or row.get('url')
        if isinstance(video_url, pd.Series): video_url = video_url.iloc[0]
        
        # Recupera Thumbnail reale o usa gradiente tech
        thumb_url = _get_youtube_thumbnail(video_url)
        if thumb_url:
            bg_style = f"background-image: url('{thumb_url}');"
        else:
            bg_style = "background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);"

        raw_title = row.get('video_title') or row.get('asset_name')
        if isinstance(raw_title, pd.Series): raw_title = raw_title.iloc[0]
        display_title = str(raw_title).replace('"', '&quot;')
        
        footer_info = "WATCH"
        score_color = "#2ECC71"

    # 5. Output HTML
    return f"""
    <div class="w-card">
        <div class="w-cover" style="{bg_style}">
            <div class="w-badge {badge_class}">{badge_text}</div>
            <div class="w-overlay"></div>
        </div>
        <div class="w-content">
            <div>
                <div class="w-meta">{date_str}</div>
                <div class="w-title">{display_title}</div>
                <div class="w-tickers">{tickers_html}</div>
            </div>
            <div class="w-footer">
                <span style="color: #94A3B8; font-size: 12px;">{card_type} INTEL</span>
                <span class="w-score" style="color: {score_color};">{footer_info}</span>
            </div>
        </div>
    </div>
    """.strip()

# --- RENDERERS DI SEZIONE ---

def render_todays_briefing(df):
    """Mostra una griglia mista (Trump + Video) solo per oggi."""
    
    cards_html = ""
    
    # 1. Trump Cards di Oggi (Raggruppate)
    trump_df = df[df['feed_type'] == 'SOCIAL_POST'].copy()
    if not trump_df.empty:
        # Grouping Dinamico
        if 'url' in trump_df.columns: grp = 'url'
        elif 'video_id' in trump_df.columns: grp = 'video_id'
        else: grp = 'summary_card'
        
        # Regole di aggregazione sicure
        agg_cols = {
            'content':'first', 'summary_card':'first', 'published_at':'first', 
            'asset_ticker':list, 'impact_score':'max', 'feed_type':'first', 
            'source_name':'first', 'url':'first', 'video_url': 'first'
        }
        final_agg = {k:v for k,v in agg_cols.items() if k in trump_df.columns}
        
        try:
            t_grouped = trump_df.groupby(grp, as_index=False).agg(final_agg)
            for _, row in t_grouped.iterrows():
                cards_html += _generate_html_card(row, "TRUMP")
        except: pass

    # 2. Video Cards di Oggi
    video_df = df[df['feed_type'] == 'VIDEO'].copy()
    for _, row in video_df.iterrows():
        cards_html += _generate_html_card(row, "VIDEO")
        
    if cards_html:
        st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)
    else:
        st.info("Nessuna novità rilevante nelle ultime 24 ore.")

def render_trump_section(df):
    """Sezione Trump Watch (Raggruppata per evitare duplicati)."""
    trump_df = df[df['feed_type'] == 'SOCIAL_POST'].copy()
    if trump_df.empty: return

    st.markdown("""
        <div class="section-header header-trump">
            <h2 style="margin:0">🦅 Trump Watch</h2>
        </div>
    """, unsafe_allow_html=True)

    # Scelta chiave di raggruppamento
    if 'url' in trump_df.columns: grp = 'url'
    elif 'video_id' in trump_df.columns: grp = 'video_id'
    else: grp = 'summary_card'

    # Aggregazione: preserva published_at e unisce ticker in lista
    agg_cols = {
        'content':'first', 'summary_card':'first', 'published_at':'first', 
        'asset_ticker':list, 'impact_score':'max', 'feed_type':'first', 
        'source_name':'first', 'url':'first'
    }
    final_agg = {k:v for k,v in agg_cols.items() if k in trump_df.columns}

    try:
        grouped_df = trump_df.groupby(grp, as_index=False).agg(final_agg)
        if 'published_at' in grouped_df.columns:
            grouped_df = grouped_df.sort_values('published_at', ascending=False)
            
        cards_html = "".join([_generate_html_card(row, "TRUMP") for _, row in grouped_df.iterrows()])
        st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Errore visualizzazione Trump: {e}")

def render_market_section(df, assets_filter):
    """
    Sezione Mercati: 
    - Se 'TUTTI': Crea una sezione H3 per ogni Asset.
    - Se Asset Specifico: Mostra solo quello.
    """
    video_df = df[df['feed_type'] == 'VIDEO'].copy()
    if video_df.empty: return

    st.markdown("""
        <div class="section-header header-market">
            <h2 style="margin:0">🧠 Market Insights</h2>
        </div>
    """, unsafe_allow_html=True)

    # Logica Multi-Asset vs Singolo Asset
    if assets_filter == "TUTTI":
        unique_assets = sorted(video_df['asset_ticker'].dropna().unique().tolist())
        for asset in unique_assets:
            asset_rows = video_df[video_df['asset_ticker'] == asset]
            if asset_rows.empty: continue
            
            # Intestazione Asset
            st.markdown(f"<h3 style='margin-top:30px; color:#2ECC71;'>💎 {asset}</h3>", unsafe_allow_html=True)
            
            # Grid per questo asset
            cards_html = "".join([_generate_html_card(row, "VIDEO") for _, row in asset_rows.iterrows()])
            st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)
            
    else:
        # Singolo Asset Selezionato
        filtered_df = video_df[video_df['asset_ticker'] == assets_filter]
        if filtered_df.empty:
            st.info(f"Nessun video recente per {assets_filter}")
            return
            
        cards_html = "".join([_generate_html_card(row, "VIDEO") for _, row in filtered_df.iterrows()])
        st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)