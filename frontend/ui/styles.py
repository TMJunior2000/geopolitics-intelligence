# CSS Globale
GLOBAL_STYLES = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');
    .stApp { background: #0E1117; }
    h1, h2, h3, p, div { font-family: 'Inter', sans-serif; color: #FAFAFA; }
    
    /* Bottoni Filtro */
    div[data-testid="column"] button {
        width: 100% !important; height: 50px !important;
        border-radius: 12px !important; font-family: 'Space Grotesk' !important;
        font-weight: 700; border: none !important;
    }
    div[data-testid="column"] button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important; box-shadow: 0 4px 15px rgba(102,126,234,0.4);
    }
    div[data-testid="column"] button[kind="secondary"] {
        background: #1E232F !important; color: #A0AEC0 !important;
        border: 1px solid #2D3748 !important;
    }
</style>
"""

# CSS Card (interno iframe)
CARD_CSS = """
<style>
    body { font-family: 'Inter', sans-serif; background: #0E1117; color: #fff; padding: 0; margin: 0; }
    .modern-card {
        background: #fff; border-radius: 20px; padding: 24px;
        height: 360px; display: flex; flex-direction: column;
        position: relative; overflow: hidden; color: #1A1A2E; margin-bottom: 20px;
    }
    .modern-card:hover { transform: translateY(-5px); }
    .modern-card::before { content:''; position: absolute; top:0; left:0; right:0; height:6px; background: linear-gradient(90deg, #FF6B6B, #FFE66D); }
    .tag-bullish { background: #06FFA5; color: #004d40; padding: 4px 12px; border-radius: 50px; font-weight: 800; font-size: 11px; }
    .tag-bearish { background: #FF6B6B; color: white; padding: 4px 12px; border-radius: 50px; font-weight: 800; font-size: 11px; }
    .card-title { font-weight: 700; font-family: 'Space Grotesk'; font-size: 18px; margin: 10px 0; height: 48px; overflow: hidden; }
    .card-text { font-size: 14px; color: #4A5568; height: 85px; overflow: hidden; margin-bottom: 15px; }
    .cta-button {
        display: flex; align-items: center; justify-content: center; width: 100%; height: 40px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;
        text-decoration: none; font-weight: 700; border-radius: 10px; margin-top: auto;
    }
    .cards-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
    .asset-header { font-family: 'Space Grotesk'; font-size: 28px; font-weight: 700; color: #FAFAFA; margin: 30px 0 20px 0; border-bottom: 1px solid rgba(255,255,255,0.1); }
</style>
"""