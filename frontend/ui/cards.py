import streamlit as st
import pandas as pd
import json

def _generate_html_card(row, card_type="VIDEO", local_tz="Europe/Rome"):
    """
    Genera una SMART CARD HTML che si adatta ai dati disponibili.
    Include logica Source ID per colori differenziati (Source 2 = Grigio).
    """
    # ---------------------------------------------------------
    # 1. PARSING DATI & PULIZIA
    # ---------------------------------------------------------
    # Tickers (Badge in basso)
    tickers = row.get('asset_ticker')
    if not isinstance(tickers, list): tickers = [tickers] if tickers else []
    valid_tickers = sorted(list(set([str(t).strip() for t in tickers if t and str(t).lower() not in ['nan', 'none', '']])))
    tickers_html = "".join(f'<span class="ticker-badge">{t}</span>' for t in valid_tickers)

    # Data
    date_str = ""
    try:
        raw_date = row.get('temp_date') or row.get('published_at') or row.get('created_at')
        if isinstance(raw_date, (pd.Series, list)): 
            raw_date = raw_date[0] if len(raw_date)>0 else None
        
        if raw_date and str(raw_date).lower() != 'nat':
            dt = pd.to_datetime(str(raw_date), utc=True).tz_convert(local_tz)
            date_str = dt.strftime("%d %b %H:%M")
    except: pass

    # Summary
    summary = row.get('summary_card') or row.get('video_summary') or row.get('title') or "..."
    summary = str(summary).replace('"', '&quot;')
    tooltip_attr = f'title="{summary}"'

    # Sentiment
    raw_sent = str(row.get('sentiment', '')).upper()
    sentiment_html = ""
    if raw_sent and raw_sent not in ['NAN', 'NONE', '']:
        sent_color = "#2ECC71" if "BULL" in raw_sent else "#EF4444" if "BEAR" in raw_sent else "#94A3B8"
        sentiment_html = f'<span style="color:{sent_color}; font-size:9px; font-weight:700; margin-right:8px;">{raw_sent}</span>'

    # ---------------------------------------------------------
    # 2. LOGICA VISIVA
    # ---------------------------------------------------------
    extra_html = ""
    header_html = ""
    
    # --- A. CASO TRUMP ---
    if card_type == "TRUMP":
        badge_text = "TRUMP WATCH"
        bg_style = "background: linear-gradient(135deg, #002D72 0%, #C8102E 100%);"
        footer_label = "TRUTH SOCIAL"
        
        score = row.get('impact_score', 0)
        try: score = int(float(score))
        except: score = 1
        s_color = "#EF4444" if score >= 4 else "#F59E0B"
        pct = min(score * 20, 100)
        
        extra_html = f"""
        <div class="impact-bar-container">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                {sentiment_html}
                <div style="font-size:9px; color:#94A3B8;">
                    IMPACT <span style="color:{s_color}; font-weight:bold;">{score}/5</span>
                </div>
            </div>
            <div class="impact-track"><div class="impact-fill" style="width:{pct}%; background:{s_color};"></div></div>
        </div>
        """
    
    # --- B. CASO VIDEO ---
    else:
        style = str(row.get('channel_style', 'MARKET')).upper()
        
        # Recupera source_id per colori custom
        try:
            sid = int(float(row.get('source_id', 0)))
        except:
            sid = 0

        # Rec & Horizon
        rec = str(row.get('recommendation', 'WATCH')).upper()
        if rec not in ['LONG', 'SHORT', 'WATCH', 'HOLD']: rec = 'WATCH'
        
        horizon = row.get('time_horizon')
        hor_html = f'<span style="color:#64748B; font-size:9px; font-weight:600;"> • {horizon}</span>' if horizon else ""
        
        header_html = f"""
        <div style="margin-bottom:6px; display:flex; align-items:center;">
            <span class="rec-badge rec-{rec}">{rec}</span>
            {sentiment_html}
            {hor_html}
        </div>
        """

        # --- LOGICA STILI & FONTI ---
        if "TECNICA" in style:
            # === MODIFICA QUI: CONTROLLO SOURCE ID ===
            if sid == 2:
                # Source 2 -> GRIGIO TITANIUM (Slate)
                bg_style = "background: linear-gradient(135deg, #334155 0%, #64748B 100%);"
            else:
                # Altre Source (es. 3) -> BLU CLASSICO
                bg_style = "background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);"
            
            badge_text = "TECNICA"
            footer_label = f"TECH SETUP (SID: {sid})"
            
            # Griglia Prezzi
            entry = row.get('entry_zone')
            target = row.get('target_price')
            stop = row.get('stop_invalidation')
            
            if (entry or target or stop) and str(entry).lower() != 'nan':
                def f(x): return str(x) if x and str(x).lower() not in ['nan','none', 'null'] else "-"
                extra_html += f"""
                <div class="levels-container">
                    <div class="level-box"><div class="level-label">ENTRY</div><div class="level-val" style="color:#60A5FA">{f(entry)}</div></div>
                    <div class="level-box"><div class="level-label">TARGET</div><div class="level-val" style="color:#4ADE80">{f(target)}</div></div>
                    <div class="level-box"><div class="level-label">STOP</div><div class="level-val" style="color:#F87171">{f(stop)}</div></div>
                </div>
                """

        elif "QUANT" in style or "CERTIFICA" in str(summary).upper():
            bg_style = "background: linear-gradient(135deg, #581c87 0%, #a855f7 100%);" # Viola
            badge_text = "STRATEGIA"
            footer_label = "STRATEGY & YIELD"
            
        else:
            bg_style = "background: linear-gradient(135deg, #064e3b 0%, #10b981 100%);" # Verde
            badge_text = "FONDAMENTALE"
            footer_label = "MACRO SCENARIO"

        # Key Drivers
        raw_drv = row.get('key_drivers')
        if raw_drv:
            try:
                if isinstance(raw_drv, str): d_list = json.loads(raw_drv.replace("'", '"'))
                elif isinstance(raw_drv, list): d_list = raw_drv
                else: d_list = []
                if d_list:
                    lis = "".join(f'<div class="driver-row"><span class="driver-dot">•</span><span class="driver-text">{d}</span></div>' for d in d_list[:3])
                    extra_html += f'<div class="drivers-container">{lis}</div>'
            except: pass

    # ---------------------------------------------------------
    # 3. ASSEMBLAGGIO
    # ---------------------------------------------------------
    html = f"""
    <div class="w-card" {tooltip_attr}>
        <div class="w-cover" style="{bg_style}">
            <div class="w-badge">{badge_text}</div>
        </div>
        <div class="w-content">
            <div class="w-meta">{date_str}</div>
            {header_html}
            <div class="w-body">
                <div class="w-title">{summary}</div>
                {extra_html}
            </div>
            <div class="w-footer">
                <span class="footer-label">{footer_label}</span>
                <div class="w-tickers">{tickers_html}</div>
            </div>
        </div>
    </div>
    """
    return " ".join(html.split())


# ==============================================================================
# FUNZIONI DI RENDERIZZAZIONE (LAYOUT)
# ==============================================================================

def render_carousel(df):
    """Renderizza il carosello orizzontale 'Daily Briefing'."""
    if df.empty: return

    # 1. Preparazione Data Unificata
    df_c = df.copy()
    df_c['temp_date'] = df_c['published_at'].fillna(df_c['created_at'])
    df_c = df_c.dropna(subset=['temp_date'])
    if df_c.empty: return

    # Conversione UTC
    df_c['temp_date'] = pd.to_datetime(df_c['temp_date'], utc=True)
    
    # 2. Filtro: Solo le ultime 24-48h o ultimi X item
    latest_ts = df_c['temp_date'].max()
    target_date = latest_ts.normalize()
    
    mask = (df_c['temp_date'] >= target_date)
    today_df = df_c.loc[mask].copy()

    if today_df.empty: return

    carousel_items = []

    # A. TRUMP (Raggruppati per Video URL)
    trump_raw = today_df[today_df['feed_type'] == 'SOCIAL_POST']
    if not trump_raw.empty:
        grouped = trump_raw.groupby('video_url', as_index=False).agg({
            'summary_card': 'first',      
            'published_at': 'first',      
            'temp_date': 'first',         
            'asset_ticker': list,         
            'impact_score': 'max',
            'sentiment': 'first',        
            'feed_type': 'first',
            'video_url': 'first'
        })
        carousel_items.extend(grouped.to_dict('records'))

    # B. VIDEO (Singoli)
    market_raw = today_df[today_df['feed_type'] == 'VIDEO']
    if not market_raw.empty:
        carousel_items.extend(market_raw.to_dict('records'))

    # Ordinamento temporale decrescente
    carousel_items.sort(key=lambda x: x['temp_date'], reverse=True)

    formatted_date = target_date.strftime('%d %B')
    
    st.markdown(f"""
        <div style="margin: 20px 0 15px 0; border-left: 4px solid #F1C40F; padding-left: 15px;">
            <h2 style="display:inline-block; margin:0; font-size: 26px;">🔥 Daily Briefing</h2>
            <span style="color:#94A3B8; font-family:'Space Grotesk'; margin-left:10px; font-size:18px;">
                {formatted_date}
            </span>
        </div>
    """, unsafe_allow_html=True)

    cards_html = ""
    for item in carousel_items:
        ftype = item.get('feed_type')
        c_type = "TRUMP" if ftype == 'SOCIAL_POST' else "VIDEO"
        cards_html += _generate_html_card(item, card_type=c_type)

    st.markdown(f'<div class="worldy-carousel">{cards_html}</div>', unsafe_allow_html=True)


def render_trump_section(df):
    """Renderizza la griglia verticale completa per Trump."""
    trump_df = df[df['feed_type'] == 'SOCIAL_POST'].copy()
    if trump_df.empty: return

    st.markdown("""
        <div class="section-header header-trump">
            <h2 style="margin:0">🦅 Trump Watch</h2>
        </div>
    """, unsafe_allow_html=True)

    # Raggruppamento per evitare duplicati visivi
    grouped_df = trump_df.groupby('video_url', as_index=False).agg({
        'summary_card': 'first',
        'created_at': 'first',
        'asset_ticker': list,
        'impact_score': 'max',
        'sentiment': 'first',
        'feed_type': 'first'
    }).sort_values(by='created_at', ascending=False)

    cards_html = ""
    for _, row in grouped_df.iterrows():
        cards_html += _generate_html_card(row, card_type="TRUMP")
    
    st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)


def render_market_section(df, assets_filter="TUTTI"):
    """
    (Legacy) Renderizza una griglia semplice filtrata.
    Utile se si vuole vedere tutto insieme senza divisione per asset.
    """
    video_df = df[df['feed_type'] == 'VIDEO'].copy()
    
    if assets_filter != "TUTTI":
        video_df = video_df[video_df['asset_ticker'] == assets_filter]

    if video_df.empty: return

    st.markdown("""
        <div class="section-header header-market">
            <h2 style="margin:0">🧠 Market Insights</h2>
        </div>
    """, unsafe_allow_html=True)

    cards_html = ""
    for _, row in video_df.iterrows():
        cards_html += _generate_html_card(row, card_type="VIDEO")
    
    st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)


def render_all_assets_sections(df):
    """
    Renderizza una sezione separata per OGNI Asset presente nei dati VIDEO.
    Ogni sezione è un CAROSELLO orizzontale per compattezza.
    """
    video_df = df[df['feed_type'] == 'VIDEO'].copy()
    
    if video_df.empty:
        st.info("Nessun dato di mercato disponibile.")
        return

    # Trova tutti i ticker unici
    unique_tickers = video_df['asset_ticker'].dropna().unique().tolist()
    unique_tickers = sorted([t for t in unique_tickers if str(t).strip() != ''])

    for ticker in unique_tickers:
        # Filtra dati
        asset_data = video_df[video_df['asset_ticker'] == ticker]
        if asset_data.empty: continue
        
        # Recupera nome esteso (se disponibile)
        try:
            asset_name_series = asset_data['asset_name'].dropna()
            asset_name = asset_name_series.iloc[0] if not asset_name_series.empty else ticker
        except:
            asset_name = ticker

        # Header Asset
        count = len(asset_data)
        st.markdown(f"""
            <div style="margin-top: 35px; margin-bottom: 15px; padding-left: 5px; display: flex; align-items: baseline; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom:5px;">
                <h3 style="margin: 0; color: #F8FAFC; font-size: 22px; font-family: 'Space Grotesk', sans-serif;">
                    {asset_name} <span style="color: #2ECC71; font-size: 16px; margin-left:5px;">{ticker}</span>
                </h3>
                <span style="margin-left: auto; font-size: 10px; font-weight: 700; color: #64748B; background: rgba(15,23,42,0.8); padding: 2px 8px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                    {count} INSIGHTS
                </span>
            </div>
        """, unsafe_allow_html=True)

        # Genera Card HTML
        cards_html = ""
        # Ordina per data
        if 'published_at' in asset_data.columns:
             asset_data = asset_data.sort_values(by='published_at', ascending=False)

        for _, row in asset_data.iterrows():
            cards_html += _generate_html_card(row, card_type="VIDEO")
        
        # Renderizza come Carosello Orizzontale
        st.markdown(f'<div class="worldy-carousel">{cards_html}</div>', unsafe_allow_html=True)