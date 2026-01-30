import streamlit as st
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

# --- CONFIGURAZIONE PERCORSI E JINJA ---
CURRENT_DIR = Path(__file__).parent.resolve()
# Risaliamo per trovare la cartella templates corretta
PROJECT_ROOT = CURRENT_DIR.parent.parent 
TEMPLATES_DIR = PROJECT_ROOT / "frontend" / "assets" / "templates"

# Setup Ambiente Jinja Sicuro (Protezione XSS)
# Se la cartella non esiste, evitiamo crash immediati, gestiremo l'errore al render
try:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(['html', 'xml']) # <-- FONDAMENTALE PER SICUREZZA
    )
except Exception:
    env = None

def _get_badge_class(rec):
    """Logica pura Python: decide la classe CSS in base al valore."""
    if not rec:
        return "badge-style"
        
    rec_upper = str(rec).strip().upper()
    cls_map = {
        "LONG": "badge-long",
        "SHORT": "badge-short",
        "WATCH": "badge-watch"
    }
    return cls_map.get(rec_upper, "badge-style")

def _safe_render_template(template_name, **kwargs):
    """Wrapper sicuro per renderizzare template o fallire con grazia."""
    if env is None:
        return ""
    
    try:
        template = env.get_template(template_name)
        return template.render(**kwargs)
    except Exception as e:
        # In sviluppo mostra l'errore, in prod potresti volerlo nascondere
        return f""
    
def _render_single_card(row):
    """Renderizza la card con data e bottone per espansione dettagli."""
    
    # 1. Preparazione Dati (Logica esistente + Colore Canale)
    style = row.get('channel_style') or 'Fondamentale'
    raw_rec = row.get('recommendation')
    rec = str(raw_rec).upper() if raw_rec else 'WATCH'
    rec_class = _get_badge_class(raw_rec)
    
    ticker = row.get('asset_ticker', 'ASSET')
    name = row.get('asset_name', '')
    summary = row.get('summary_card') or 'Nessun dettaglio disponibile.'
    drivers = row.get('key_drivers') or []
    
    # Gestione Colore in base al canale (Tabella sources)
    channel_name = row.get('source_name', 'Analisi')
    accent_color = "#34495e" # Default
    if "investirebiz" in channel_name.lower():
        accent_color = "#2ecc71" # Verde
    elif "marketmind" in channel_name.lower():
        accent_color = "#95a5a6" # Grigio

    # 2. Formattazione Data sicura (Quella che abbiamo approvato)
    raw_date = row.get('published_at')
    display_date = "Data N.D."
    if raw_date:
        try:
            if hasattr(raw_date, 'strftime'):
                display_date = raw_date.strftime("%d/%m/%Y")
            else:
                import pandas as pd
                display_date = pd.to_datetime(raw_date).strftime("%d/%m/%Y")
        except:
            display_date = str(raw_date)[:10]

    # 3. Rendering Visuale
    with st.container(border=True):
        
        # A. Header Custom con Bordo Colorato, Data e Badge
        # Manteniamo i tuoi badge HTML originali
        html_badges = _safe_render_template("badges.html", style=style, rec=rec, rec_class=rec_class)
        st.markdown(html_badges, unsafe_allow_html=True)

        # B. Ticker, Nome e Data (Layout pulito)
        st.markdown(f"""
            <div style="border-left: 5px solid {accent_color}; padding-left: 10px; margin: 10px 0;">
                <small style="color: #888;">📅 {display_date}</small>
                <h3 style="margin: 0;">{ticker}</h3>
                <small style="color: {accent_color}; font-weight: bold;">{channel_name}</small>
            </div>
        """, unsafe_allow_html=True)
        
        if name:
            st.caption(name)
        
        st.markdown("---")
        
        # C. Summary e Drivers (Compatti)
        st.markdown(f"**Analisi:** {summary}")
        if isinstance(drivers, list) and drivers:
            st.markdown("**Key Drivers:**")
            # HTML custom per rimuovere lo spazio eccessivo tra i punti
            drivers_html = "".join([f"<li style='margin-bottom: 0px;'>{d}</li>" for d in drivers])
            st.markdown(f"<ul style='margin-top: -10px; padding-left: 20px; font-size: 0.9rem;'>{drivers_html}</ul>", unsafe_allow_html=True)

        # D. Bottone "Leggi Tutto" (Sostituisce il vecchio link_button)
        # Usiamo l'ID del database per rendere il bottone univoco
        if st.button("🔍 DETTAGLI COMPLETI", key=f"expand_{row['id']}", use_container_width=True):
            _show_full_analysis_modal(row)

@st.dialog("Dettaglio Analisi")
def _show_full_analysis_modal(row):
    st.subheader(f"{row['asset_ticker']} - {row.get('asset_name', '')}")
    st.info(f"Fonte: {row.get('source_name')} | Pubblicato il: {row.get('published_at')}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Sentiment", row.get('sentiment'))
    with col2:
        st.metric("Recommendation", row.get('recommendation'))

    st.markdown("### 📝 Analisi Completa")
    # Qui usiamo 'video_summary' che è il testo lungo della tabella intelligence_feed
    st.write(row.get('video_summary') or row.get('summary_card'))
    
    if row.get('video_url'):
        st.link_button("📺 Guarda Video Originale", row['video_url'])

def render_grid(df, assets_to_show):
    """Funzione principale chiamata dalla dashboard"""
    if df.empty:
        return

    # Ordinamento sicuro
    if 'published_at' in df.columns:
        df = df.sort_values(by='published_at', ascending=False)
    
    for asset in assets_to_show:
        asset_df = df[df['asset_ticker'] == asset]
        if asset_df.empty: continue
        
        st.markdown(f"### 💎 {asset}")
        st.markdown("---")
        
        cols = st.columns(3)
        for idx, (_, row) in enumerate(asset_df.iterrows()):
            with cols[idx % 3]:
                _render_single_card(row)
        
        st.markdown("<br>", unsafe_allow_html=True)