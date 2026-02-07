import streamlit as st
import pandas as pd
import pytz  # per gestire timezone

def _generate_html_card(row, card_type="VIDEO", local_tz="Europe/Rome"):
    """
    Genera l'HTML per una card.
    Versione MINIFIED: Rimuove spazi e a capo per evitare che Streamlit mostri il codice.
    """
    # 1. GESTIONE DATA E TICKER (Logica invariata)
    tickers = row.get('asset_ticker')
    if not isinstance(tickers, list): tickers = [tickers] if tickers else []
    valid_tickers = sorted(list(set([str(t).strip() for t in tickers if t and str(t).lower() not in ['nan', 'none', '']])))
    tickers_html = "".join(f'<span class="ticker-badge">{t}</span>' for t in valid_tickers)

    date_str = ""
    try:
        raw_date = row.get('temp_date') or row.get('published_at') or row.get('created_at')
        if isinstance(raw_date, (pd.Series, list)):
            raw_date = raw_date[0] if isinstance(raw_date, list) else raw_date.iloc[0]
        
        if raw_date and str(raw_date).lower() != 'nat':
            dt = pd.to_datetime(str(raw_date), utc=True)
            dt_local = dt.tz_convert(local_tz)
            date_str = dt_local.strftime("%d %b %H:%M")
    except: date_str = ""

    # 2. LOGICA VISIVA
    summary = row.get('summary_card') or row.get('video_summary') or row.get('title') or "..."
    summary = str(summary).replace('"', '&quot;')

    if card_type == "TRUMP":
        badge_text = "TRUMP POST"
        badge_class = "badge-trump"
        bg_style = "background: linear-gradient(135deg, #002D72 0%, #C8102E 100%);"
        display_title = summary if len(summary) < 140 else summary[:137] + "..."
        score_color = "#E74C3C" # Rosso
        footer_text = "TRUMP INTEL"
    else: 
        cat = row.get('category') or row.get('channel_style', 'MARKET')
        if isinstance(cat, (pd.Series, list)): cat = str(cat[0])
        badge_text = str(cat).upper() if cat else "MARKET"
        badge_class = "badge-video"
        bg_style = "background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);"
        display_title = summary
        score_color = "#2ECC71" # Verde
        footer_text = "VIDEO INTEL"

    # 3. HTML MINIFICATO (La correzione chiave è qui sotto)
    # Usiamo una stringa unica senza indentazioni o newlines che confondano Streamlit
    html = f"""
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
                <span style="color: #94A3B8; font-size: 12px;">{footer_text}</span>
                <span class="w-score" style="color: {score_color};">WATCH</span>
            </div>
        </div>
    </div>
    """
    
    # Rimuoviamo tutti i ritorni a capo e gli spazi extra
    return " ".join(html.split())

def render_trump_section(df):
    """
    Renderizza la sezione Trump (Archivio).
    """
    trump_df = df[df['feed_type'] == 'SOCIAL_POST'].copy()
    
    if trump_df.empty:
        return

    st.markdown("""
        <div class="section-header header-trump">
            <h2 style="margin:0">🦅 Trump Watch</h2>
            <p style="margin:0; color:#888">Monitoraggio aggregato di Truth Social e impatto geopolitico.</p>
        </div>
    """, unsafe_allow_html=True)

    grouped_df = trump_df.groupby('video_url', as_index=False).agg({
        'summary_card': 'first',
        'created_at': 'first',
        'asset_ticker': list,
        'impact_score': 'max',
        'feed_type': 'first',
        'source_name': 'first'
    }).sort_values(by='created_at', ascending=False)

    cards_html = ""
    for _, row in grouped_df.iterrows():
        cards_html += _generate_html_card(row, card_type="TRUMP")
    
    st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)

def render_market_section(df, assets_filter):
    """Renderizza la sezione Insights di Mercato (Archivio)"""
    video_df = df[df['feed_type'] == 'VIDEO'].copy()
    
    if assets_filter != "TUTTI":
        video_df = video_df[video_df['asset_ticker'] == assets_filter]

    if video_df.empty:
        if assets_filter != "TUTTI":
            st.info(f"Nessun video trovato per {assets_filter}")
        return

    st.markdown("""
        <div class="section-header header-market">
            <h2 style="margin:0">🧠 Market Insights</h2>
            <p style="margin:0; color:#888">Analisi tecnica e fondamentale dai migliori analisti.</p>
        </div>
    """, unsafe_allow_html=True)

    cards_html = ""
    for _, row in video_df.iterrows():
        cards_html += _generate_html_card(row, card_type="VIDEO")
    
    st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)

def render_carousel(df):
    if df.empty:
        st.warning("⚠️ Nessun dato disponibile per il carosello.")
        return

    # 1. Preparazione Data Unificata
    df_c = df.copy()
    # Usa published_at come fonte primaria (visto che nel DB è popolata anche per Trump)
    df_c['temp_date'] = df_c['published_at'].fillna(df_c['created_at'])
    
    # Pulizia NaT
    df_c = df_c.dropna(subset=['temp_date'])
    if df_c.empty: return

    # Conversione UTC
    df_c['temp_date'] = pd.to_datetime(df_c['temp_date'], utc=True)
    
    # 2. Filtro Temporale (Ultimo Giorno)
    latest_ts = df_c['temp_date'].max()
    target_date = latest_ts.normalize()
    
    mask = (df_c['temp_date'] >= target_date) & (df_c['temp_date'] < target_date + pd.Timedelta(days=1))
    today_df = df_c.loc[mask].copy()

    if today_df.empty: return

    carousel_items = []

    # A. TRUMP (Raggruppati)
    trump_raw = today_df[today_df['feed_type'] == 'SOCIAL_POST']
    if not trump_raw.empty:
        grouped = trump_raw.groupby('video_url', as_index=False).agg({
            'summary_card': 'first',      
            'published_at': 'first',      # Importante: manteniamo la data originale
            'temp_date': 'first',         # Importante: manteniamo la data unificata
            'asset_ticker': list,         
            'impact_score': 'max',        
            'feed_type': 'first',
            'video_url': 'first'
        })
        carousel_items.extend(grouped.to_dict('records'))

    # B. VIDEO (Singoli)
    market_raw = today_df[today_df['feed_type'] == 'VIDEO']
    if not market_raw.empty:
        # Assicuriamoci che temp_date sia nel dizionario
        carousel_items.extend(market_raw.to_dict('records'))

    # 4. Ordinamento e Render
    carousel_items.sort(key=lambda x: x['temp_date'], reverse=True)

    # 5. RENDER TITOLO E CAROSELLO
    # Formatta data titolo (es. 06 February)
    formatted_date = target_date.strftime('%d %B')
    
    st.markdown(f"""
        <div style="margin: 20px 0 15px 0; border-left: 4px solid #F1C40F; padding-left: 15px;">
            <h2 style="display:inline-block; margin:0; font-size: 26px;">🔥 Daily Briefing</h2>
            <span style="color:#94A3B8; font-family:'Space Grotesk'; margin-left:10px; font-size:18px;">
                {formatted_date}
            </span>
        </div>
    """, unsafe_allow_html=True)

    # Genera HTML Card
    cards_html = ""
    for item in carousel_items:
        # Determina tipo
        ftype = item.get('feed_type')
        c_type = "TRUMP" if ftype == 'SOCIAL_POST' else "VIDEO"
        
        cards_html += _generate_html_card(item, card_type=c_type)

    # --- MODIFICA QUI ---
    # Usiamo la classe specifica 'worldy-carousel' invece di 'worldy-grid'
    st.markdown(f'<div class="worldy-carousel">{cards_html}</div>', unsafe_allow_html=True)