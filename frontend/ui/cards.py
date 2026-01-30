import streamlit as st
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

# --- CONFIGURAZIONE PERCORSI ---
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent.parent 
TEMPLATES_DIR = PROJECT_ROOT / "frontend" / "assets" / "templates"

# Setup Jinja
try:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(['html', 'xml'])
    )
except Exception:
    env = None

def _get_badge_class(rec):
    if not rec: return "badge-style"
    rec_upper = str(rec).strip().upper()
    return {
        "LONG": "badge-long",
        "SHORT": "badge-short",
        "WATCH": "badge-watch"
    }.get(rec_upper, "badge-style")

def _safe_render_template(template_name, **kwargs):
    if env is None: return ""
    try:
        return env.get_template(template_name).render(**kwargs)
    except Exception as e:
        return f""

def _render_single_card(row):
    """
    Renderizza la card usando il nuovo template 'card.html' in stile Worldy.
    """
    # 1. Preparazione Dati
    rec = row.get('recommendation', 'WATCH')
    rec_class = _get_badge_class(rec)
    
    # Gestione Immagine (se non c'è, mettiamo un placeholder o una logica custom)
    # Puoi aggiungere una colonna 'image_url' al tuo DB o usare una logica basata sul ticker
    image_url = row.get('image_url', 'https://via.placeholder.com/600x400?text=Analysis') 

    # Per simulare l'effetto "Bold" di Worldy, potremmo dover processare il summary
    # Qui passo il summary raw, ma nel template uso |safe se contiene già HTML
    summary = row.get('summary_card', 'Analisi tecnica non disponibile')
    
    # Formattazione data
    published = row.get('published_at')
    date_str = published.strftime('%d %B %Y') if published else ""

    # 2. Rendering unico HTML
    html_card = _safe_render_template("card.html",
        asset=row.get('asset_ticker', 'ASSET'),
        summary=summary,
        rec=str(rec).upper(),
        rec_class=rec_class,
        image_url=image_url,
        video_url=row.get('video_url', '#'),
        date=date_str,
        entry=row.get('entry_zone')
    )
    
    # 3. Output in Streamlit
    # Rimuoviamo st.container(border=True) perché il bordo è ora nel CSS .box
    st.markdown(html_card, unsafe_allow_html=True)

def render_grid(df, assets_to_show):
    if df.empty: return

    # CSS Grid personalizzato per gestire il layout responsive meglio delle colonne native
    # Inietta un container grid HTML
    st.markdown('<div class="grid">', unsafe_allow_html=True)
    
    # Trucco: Usiamo colonne Streamlit per iniettare l'HTML, 
    # ma in realtà stiamo affidando il layout al CSS .grid
    
    # NOTA: Per un layout a griglia pura HTML/CSS come Worldy, 
    # l'ideale è iterare e creare un'unica stringa HTML gigante o usare colonne.
    # Manteniamo la logica a colonne per compatibilità con i tuoi dati, 
    # ma applichiamo lo stile alle card interne.
    
    cols = st.columns(3)
    for idx, (_, row) in enumerate(df.iterrows()):
        if row['asset_ticker'] in assets_to_show or "TUTTI" in assets_to_show:
            with cols[idx % 3]:
                _render_single_card(row)