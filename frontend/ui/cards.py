import streamlit as st
import pandas as pd
import pytz  # per gestire timezone

def _generate_html_card(row, card_type="VIDEO", local_tz: str | None = "Europe/Rome"):
    """
    Genera l'HTML per una card.
    Mostra data + ora, opzionalmente convertita in timezone locale.
    """
    # --- GESTIONE TICKER ---
    tickers = row.get('asset_ticker')
    if not isinstance(tickers, list):
        tickers = [tickers] if tickers else []
    tickers = sorted(list(set([t for t in tickers if t])))
    tickers_html = "".join(f'<span class="ticker-badge">{t}</span>' for t in tickers)

    # --- SUMMARY ---
    summary = row.get('summary_card') or row.get('video_summary') or "Nessuna descrizione."
    summary = str(summary).replace('"', '&quot;')

    # --- DATA + ORA ---
    try:
        raw_date = row.get('published_at') or row.get('created_at')
        if isinstance(raw_date, pd.Series):
            raw_date = raw_date.iloc[0]

        dt = pd.to_datetime(raw_date)
        if dt.tzinfo is None:
            # Assume UTC se non c'è timezone
            dt = dt.tz_localize('UTC')

        # Converti in locale se richiesto
        if local_tz:
            dt = dt.tz_convert(local_tz)

        # Formatta data + ora
        date_str = dt.strftime("%d %b %Y %H:%M %Z")

    except Exception as e:
        print(f"⚠️ Data parsing error: {e}")
        date_str = "OGGI"

    # --- LOGICA VISIVA ---
    if card_type == "TRUMP":
        badge_text = "TRUMP WATCH"
        badge_class = "badge-trump"
        bg_style = "background: linear-gradient(135deg, #002D72 0%, #C8102E 100%);"

        display_title = summary[:120] + "..." if len(summary) > 120 else summary

        score = row.get('impact_score', 0)
        if isinstance(score, pd.Series) or isinstance(score, list):
            score = max(score)
        
        extra_info = ""
        if row.get('sentiment'):
            extra_info += f"{row.get('sentiment')} | "
        if row.get('time_horizon'):
            extra_info += f"{row.get('time_horizon')} | "
        if row.get('entry_zone'):
            extra_info += f"Entry: {row.get('entry_zone')} | "
        if row.get('target_price'):
            extra_info += f"Target: {row.get('target_price')} | "
        if row.get('stop_invalidation'):
            extra_info += f"Stop: {row.get('stop_invalidation')}"

        footer_info = "WATCH" if not extra_info else extra_info.strip(" | ")
        score_color = "#E74C3C" if score >= 4 else "#F1C40F"

    else:  # VIDEO
        badge_text = row.get('channel_style', 'ANALYSIS')
        if isinstance(badge_text, pd.Series):
            badge_text = badge_text.iloc[0]
        badge_class = "badge-video"

        video_url = row.get('video_url')
        if isinstance(video_url, pd.Series):
            video_url = video_url.iloc[0]

        bg_style = "background: linear-gradient(135deg, #0F766E 0%, #22C55E 100%);"
        raw_title = row.get('summary_card') or row.get('video_summary') or "Nessuna descrizione."
        if isinstance(raw_title, pd.Series):
            raw_title = raw_title.iloc[0]
        display_title = str(raw_title).replace('"', '&quot;')

        footer_info = "WATCH"
        score_color = "#2ECC71"

    # --- TEMPLATE HTML ---
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
                <span style="color: #94A3B8; font-size: 12px;">{card_type} INTEL</span>
                <span class="w-score" style="color: {score_color};">{footer_info}</span>
            </div>
        </div>
    </div>
    """
    return html.strip()

def render_trump_section(df):
    """
    Renderizza la sezione Trump raggruppando post identici che colpiscono asset diversi.
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

    # --- LOGICA DI RAGGRUPPAMENTO ---
    # Raggruppiamo per URL (o content se url manca) per unire gli asset
    # Aggreghiamo 'asset_ticker' in una lista e prendiamo il max di 'impact_score'
    grouped_df = trump_df.groupby('video_url', as_index=False).agg({
        'summary_card': 'first',      # Il riassunto è lo stesso
        'created_at': 'first',        # La data è la stessa
        'asset_ticker': list,         # <--- QUI UNIAMO I TICKER IN UNA LISTA
        'impact_score': 'max',        # Prendiamo il punteggio più alto
        'feed_type': 'first',
        'source_name': 'first'
    }).sort_values(by='created_at', ascending=False)

    # Griglia Responsive
    cards_html = ""
    for _, row in grouped_df.iterrows():
        cards_html += _generate_html_card(row, card_type="TRUMP")
    
    st.markdown(f'<div class="worldy-grid">{cards_html}</div>', unsafe_allow_html=True)

def render_market_section(df, assets_filter):
    """Renderizza la sezione Insights di Mercato (Youtube)"""
    # Filtra solo VIDEO
    video_df = df[df['feed_type'] == 'VIDEO'].copy()
    
    # Filtro Asset
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