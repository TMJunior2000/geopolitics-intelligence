import streamlit as st
import pandas as pd
import pytz  # per gestire timezone

def _generate_html_card(row, card_type="VIDEO", local_tz="Europe/Rome"):
    """
    Genera l'HTML per una card "Tactical" ricca di dati.
    """
    # ---------------------------------------------------
    # 1. PARSING DATA SICURO (Come prima)
    # ---------------------------------------------------
    date_str = ""
    try:
        raw_date = row.get('temp_date') or row.get('published_at') or row.get('created_at')
        if isinstance(raw_date, (pd.Series, list)):
            raw_date = raw_date[0] if isinstance(raw_date, list) else raw_date.iloc[0]
        
        if raw_date and str(raw_date).lower() != 'nat':
            dt = pd.to_datetime(str(raw_date), utc=True).tz_convert(local_tz)
            date_str = dt.strftime("%d %b %H:%M")
    except: date_str = ""

    # ---------------------------------------------------
    # 2. TICKER (Badge in basso)
    # ---------------------------------------------------
    tickers = row.get('asset_ticker')
    if not isinstance(tickers, list): tickers = [tickers] if tickers else []
    valid_tickers = sorted(list(set([str(t).strip() for t in tickers if t and str(t).lower() not in ['nan', 'none', '']])))
    tickers_html = "".join(f'<span class="ticker-badge">{t}</span>' for t in valid_tickers)

    # ---------------------------------------------------
    # 3. DATI OPERATIVI (Sentiment, Target, Entry)
    # ---------------------------------------------------
    # Estraiamo i dati "sporchi" e li puliamo
    def get_val(key):
        val = row.get(key)
        if isinstance(val, (pd.Series, list)): val = val[0]
        return str(val) if val and str(val).lower() not in ['nan', 'none', ''] else None

    sentiment = get_val('sentiment') or "Neutral"
    recommendation = (get_val('recommendation') or "WATCH").upper()
    time_horizon = get_val('time_horizon') or "Intraday"
    
    entry = get_val('entry_zone') or "-"
    target = get_val('target_price') or "-"
    stop = get_val('stop_invalidation') or "-"

    # Colore Bordo/Badge basato sulla Raccomandazione
    if "LONG" in recommendation or "BUY" in recommendation:
        rec_class = "sig-long"
        rec_icon = "🟢"
    elif "SHORT" in recommendation or "SELL" in recommendation:
        rec_class = "sig-short"
        rec_icon = "🔴"
    else:
        rec_class = "sig-watch"
        rec_icon = "👁️"

    # ---------------------------------------------------
    # 4. LOGICA VISIVA DIFFERENZIATA
    # ---------------------------------------------------
    summary = row.get('summary_card') or row.get('video_summary') or row.get('title') or "..."
    summary = str(summary).replace('"', '&quot;')

    if card_type == "TRUMP":
        # --- STILE TRUMP ---
        badge_text = "TRUMP WATCH"
        badge_class = "badge-trump"
        bg_style = "background: linear-gradient(135deg, #002D72 0%, #C8102E 100%);"
        
        # Titolo + Impatto
        display_title = summary
        if len(display_title) > 130: display_title = display_title[:127] + "..."
        
        impact = row.get('impact_score', 0)
        try: 
            if isinstance(impact, (pd.Series, list)): impact = max(impact)
            impact = int(impact)
        except: impact = 1
        
        # Visualizza Impatto come stelle o numero
        extra_html = f'<div style="color: #F1C40F; font-size: 11px; margin-top:5px;">IMPACT: {"⚡" * impact}</div>'
        
        # Per Trump non mostriamo la griglia livelli, ma l'impatto
        middle_block = f"""
        <div style="margin: 10px 0;">
            {extra_html}
        </div>
        """
        footer_text = "GEOPOLITICS"
        footer_right = f"<span style='color:#E74C3C'><b>{sentiment.upper()}</b></span>"

    else:
        # --- STILE VIDEO/MARKET ---
        cat = row.get('channel_style', 'MARKET')
        if isinstance(cat, (pd.Series, list)): cat = str(cat[0])
        badge_text = str(cat).upper()
        badge_class = "badge-video"
        bg_style = "background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);"
        
        display_title = summary
        
        # Griglia Livelli Operativi
        middle_block = f"""
        <div class="levels-grid">
            <div class="level-box">
                <span class="level-label">Entry</span>
                <span class="level-val">{entry}</span>
            </div>
            <div class="level-box">
                <span class="level-label">Target</span>
                <span class="level-val" style="color:#2ECC71">{target}</span>
            </div>
            <div class="level-box">
                <span class="level-label">Stop</span>
                <span class="level-val" style="color:#E74C3C">{stop}</span>
            </div>
        </div>
        """
        
        # Footer: Nascondiamo la fonte video (privacy richiesta)
        footer_text = "MARKET INTEL"
        footer_right = f"<span class='signal-badge {rec_class}'>{rec_icon} {recommendation}</span>"

    # ---------------------------------------------------
    # 5. ASSEMBLAGGIO HTML
    # ---------------------------------------------------
    html = f"""
    <div class="w-card">
        <div class="w-cover" style="{bg_style}">
            <div class="w-badge {badge_class}">{badge_text}</div>
            <div class="w-overlay"></div>
        </div>
        
        <div class="w-content">
            
            <div class="top-meta-row">
                <span>📅 {date_str}</span>
                <span>⏳ {time_horizon}</span>
            </div>

            <div class="w-title">{display_title}</div>
            
            {middle_block}

            <div class="w-tickers" style="margin-top:auto; margin-bottom: 10px;">{tickers_html}</div>

            <div class="w-footer">
                <span style="color: #64748B; font-size: 11px; font-weight:600;">{footer_text}</span>
                {footer_right}
            </div>
        </div>
    </div>
    """
    
    # Minificazione per evitare che Streamlit mostri codice
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