import streamlit as st
import pandas as pd
import pytz  # per gestire timezone

import json

def _generate_html_card(row, card_type="VIDEO", local_tz="Europe/Rome"):
    """
    Genera una card ricca di informazioni, nascondendo i campi vuoti.
    """
    # ---------------------------------------------------------
    # 1. PARSING DATI GREZZI
    # ---------------------------------------------------------
    # Tickers
    tickers = row.get('asset_ticker')
    if not isinstance(tickers, list): tickers = [tickers] if tickers else []
    valid_tickers = sorted(list(set([str(t).strip() for t in tickers if t and str(t).lower() not in ['nan', 'none', '']])))
    tickers_html = "".join(f'<span class="ticker-badge">{t}</span>' for t in valid_tickers)

    # Data
    date_str = ""
    try:
        raw_date = row.get('temp_date') or row.get('published_at') or row.get('created_at')
        if isinstance(raw_date, (pd.Series, list)): raw_date = raw_date[0] if len(raw_date)>0 else None
        
        if raw_date and str(raw_date).lower() != 'nat':
            dt = pd.to_datetime(str(raw_date), utc=True).tz_convert(local_tz)
            date_str = dt.strftime("%d %b %H:%M")
    except: pass

    # Summary/Titolo
    summary = row.get('summary_card') or row.get('video_summary') or row.get('title') or "..."
    summary = str(summary).replace('"', '&quot;')
    
    # ---------------------------------------------------------
    # 2. SEZIONE SPECIFICA: DATI OPERATIVI (Solo se presenti)
    # ---------------------------------------------------------
    # Recommendation (LONG, SHORT, WATCH)
    rec = str(row.get('recommendation', 'WATCH')).upper()
    if rec not in ['LONG', 'SHORT', 'WATCH', 'HOLD']: rec = 'WATCH'
    
    # Time Horizon
    horizon = row.get('time_horizon')
    horizon_html = f'<span style="font-size:10px; color:#94A3B8; margin-left:5px;">| {horizon}</span>' if horizon else ""

    # Livelli Operativi (Griglia)
    entry = row.get('entry_zone')
    target = row.get('target_price')
    stop = row.get('stop_invalidation')
    
    # Mostra la griglia SOLO se almeno uno dei valori esiste
    levels_html = ""
    if entry or target or stop:
        # Helper per formattare valori nulli come trattini
        def fmt(val): return str(val) if val and str(val).lower() != 'nan' else "-"
        
        levels_html = f"""
        <div class="levels-grid">
            <div class="level-box">
                <div class="level-label">ENTRY</div>
                <div class="level-value" style="color:#60A5FA">{fmt(entry)}</div>
            </div>
            <div class="level-box">
                <div class="level-label">TARGET</div>
                <div class="level-value" style="color:#2ECC71">{fmt(target)}</div>
            </div>
            <div class="level-box">
                <div class="level-label">STOP</div>
                <div class="level-value" style="color:#F87171">{fmt(stop)}</div>
            </div>
        </div>
        """

    # Key Drivers (Lista Punti)
    drivers_html = ""
    raw_drivers = row.get('key_drivers')
    if raw_drivers:
        try:
            # Se è una stringa che sembra una lista, prova a parsificarla
            if isinstance(raw_drivers, str) and raw_drivers.startswith('['):
                drivers_list = json.loads(raw_drivers.replace("'", '"')) # Fix quote semplici
            elif isinstance(raw_drivers, list):
                drivers_list = raw_drivers
            else:
                drivers_list = []
            
            if drivers_list:
                list_items = "".join(f'<div class="driver-item"><span class="driver-dot">•</span>{d}</div>' for d in drivers_list[:3]) # Max 3 drivers
                drivers_html = f'<div class="drivers-box">{list_items}</div>'
        except:
            pass # Se fallisce il parsing, non mostra nulla

    # ---------------------------------------------------------
    # 3. STILE VISIVO (TRUMP vs VIDEO)
    # ---------------------------------------------------------
    if card_type == "TRUMP":
        badge_text = "TRUMP WATCH"
        badge_class = "badge-trump"
        bg_style = "background: linear-gradient(135deg, #002D72 0%, #C8102E 100%);"
        footer_text = "TRUMP INTEL"
        
        # Titolo più lungo per Trump dato che non ha livelli tecnici di solito
        display_title = summary if len(summary) < 160 else summary[:157] + "..."
        
        # Impact Score Bar
        score = row.get('impact_score', 0)
        try: score = int(float(score))
        except: score = 1
        
        score_color = "#E74C3C" if score >= 4 else "#F1C40F"
        # Visualizzazione grafica score (Barra)
        width_pct = min(score * 20, 100) # 5 = 100%
        levels_html = f"""
        <div style="margin-top:10px;">
            <div style="display:flex; justify-content:space-between; font-size:10px; color:#CBD5E1; margin-bottom:2px;">
                <span>IMPACT SCORE</span>
                <span style="color:{score_color}; font-weight:bold;">{score}/5</span>
            </div>
            <div class="impact-bar"><div class="impact-fill" style="width:{width_pct}%; background:{score_color};"></div></div>
        </div>
        """
        # Trump di solito non ha drivers tecnici, quindi usiamo lo spazio per questo

    else: # VIDEO
        cat = row.get('channel_style', 'MARKET')
        badge_text = str(cat).upper() if cat else "MARKET"
        badge_class = "badge-video"
        
        # Colore Header in base al sentiment/channel style
        if "TECNICA" in badge_text:
            bg_style = "background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);" # Blu Tecnico
        elif "QUANT" in badge_text:
            bg_style = "background: linear-gradient(135deg, #581c87 0%, #8b5cf6 100%);" # Viola Quant
        else:
            bg_style = "background: linear-gradient(135deg, #064e3b 0%, #10b981 100%);" # Verde Fondamentale

        display_title = summary if len(summary) < 110 else summary[:107] + "..."
        footer_text = "MARKET INTEL" # Generico, nasconde il canale
        score_color = "#2ECC71"

    # ---------------------------------------------------------
    # 4. ASSEMBLAGGIO HTML
    # ---------------------------------------------------------
    # Header Content (Rec Badge + Title)
    header_content = f"""
    <div style="margin-bottom:8px;">
        <span class="rec-badge rec-{rec}">{rec}</span>
        {horizon_html}
    </div>
    <div class="w-title" style="font-size:15px; margin-bottom:0;">{display_title}</div>
    """

    html = f"""
    <div class="w-card">
        <div class="w-cover" style="{bg_style}; height: 140px;">
            <div class="w-badge {badge_class}">{badge_text}</div>
            <div class="w-overlay"></div>
        </div>
        <div class="w-content" style="padding:12px;">
            <div style="margin-bottom:8px;">
                <div class="w-meta" style="margin-bottom:4px;">{date_str}</div>
                {header_content}
            </div>
            
            <div style="flex:1;">
                {levels_html}
                {drivers_html}
            </div>

            <div class="w-footer" style="margin-top:10px;">
                <span style="color: #94A3B8; font-size: 11px; text-transform:uppercase; letter-spacing:0.5px;">{footer_text}</span>
                <div class="w-tickers" style="margin:0; position:relative; bottom:0;">{tickers_html}</div>
            </div>
        </div>
    </div>
    """
    
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