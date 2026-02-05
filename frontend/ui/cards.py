import streamlit as st
import pandas as pd

def _generate_html_card(row, card_type="VIDEO"):
    """
    Genera l'HTML puro per una card stile Worldy.
    card_type: 'TRUMP' o 'VIDEO'
    """
    # Dati comuni
    ticker = row.get('asset_ticker', 'N/A')
    summary = row.get('summary_card') or row.get('video_summary') or "Nessuna descrizione disponibile."
    
    # Pulizia testo per evitare rotture dell'HTML (virgolette)
    summary = str(summary).replace('"', '&quot;')
    
    # Gestione Data
    try:
        raw_date = row.get('published_at') or row.get('created_at')
        date_str = pd.to_datetime(raw_date).strftime("%d %b %Y")
    except:
        date_str = "OGGI"

    # Stili specifici per tipo
    if card_type == "TRUMP":
        badge_text = "TRUMP WATCH"
        badge_class = "badge-trump"
        cover_class = "cover-trump"
        display_title = summary[:120] + "..." if len(summary) > 120 else summary
        
        score = row.get('impact_score', 0)
        footer_info = f"IMPACT SCORE: {score}/5"
        score_color = "#E74C3C" if score >= 4 else "#F1C40F"
    else:
        badge_text = row.get('channel_style', 'ANALYSIS')
        badge_class = "badge-video"
        cover_class = "cover-video"
        
        raw_title = row.get('video_title') or row.get('asset_name') or ticker
        display_title = str(raw_title).replace('"', '&quot;')
        
        footer_info = f"{row.get('sentiment', 'NEUTRAL')} | {row.get('recommendation', 'WATCH')}"
        score_color = "#2ECC71"

    # HTML Template COMPATTATO (Senza spazi all'inizio delle righe)
    html = f"""
    <div class="w-card">
        <div class="w-cover {cover_class}">
            <div class="w-badge {badge_class}">{badge_text}</div>
            <div class="w-overlay"></div>
        </div>
        <div class="w-content">
            <div>
                <div class="w-meta">{date_str} • {ticker}</div>
                <div class="w-title">{display_title}</div>
            </div>
            <div class="w-footer">
                <span style="color: #94A3B8; font-size: 12px;">{row.get('source_name', 'System')}</span>
                <span class="w-score" style="color: {score_color};">{footer_info}</span>
            </div>
        </div>
    </div>
    """
    return html.strip() # .strip() rimuove spazi vuoti inizio/fine stringa

def render_trump_section(df):
    """Renderizza la sezione orizzontale/griglia per Trump"""
    trump_df = df[df['feed_type'] == 'SOCIAL_POST'].copy()
    
    if trump_df.empty:
        return

    st.markdown("""
        <div class="section-header header-trump">
            <h2 style="margin:0">🦅 Trump Watch</h2>
            <p style="margin:0; color:#888">Monitoraggio in tempo reale di Truth Social e impatto geopolitico.</p>
        </div>
    """, unsafe_allow_html=True)

    # Griglia Responsive
    # Usiamo un container HTML per la griglia CSS
    cards_html = ""
    for _, row in trump_df.iterrows():
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