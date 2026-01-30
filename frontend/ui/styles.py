GLOBAL_STYLES = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap');
    
    /* BACKGROUND GRADIENT */
    .stApp { 
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        background-attachment: fixed;
    }
    
    /* HERO HEADER */
    .hero-header {
        text-align: center;
        padding: 40px 20px;
        margin-bottom: 30px;
        background: linear-gradient(135deg, #FF6B6B 0%, #FFE66D 50%, #4ECDC4 100%);
        border-radius: 25px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
    }
    
    .hero-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 56px;
        font-weight: 700;
        background: linear-gradient(45deg, #1A1A2E, #16213E);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -2px;
    }
    
    .hero-subtitle {
        font-size: 16px;
        color: #2D3748;
        margin-top: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 3px;
    }
    
    /* NAVIGATION TITLE */
    .nav-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 22px;
        font-weight: 700;
        color: #FAFAFA;
        margin: 30px 0 20px 0;
        padding: 20px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
    }
    
    /* STREAMLIT BUTTONS STYLING */
    div[data-testid="column"] button {
        width: 100% !important;
        min-width: 100px !important;
        height: 55px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        border-radius: 15px !important;
        border: 3px solid transparent !important;
        transition: all 0.3s ease !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        padding: 0 10px !important;
    }
    
    div[data-testid="column"] button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: 3px solid #667eea !important;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4) !important;
        transform: scale(1.05);
    }
    
    div[data-testid="column"] button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.05) !important;
        color: #A0AEC0 !important;
        border: 3px solid rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(10px);
    }
    
    div[data-testid="column"] button[kind="secondary"]:hover {
        background: rgba(255, 255, 255, 0.1) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2) !important;
    }
    
    /* GLOBAL TEXT COLORS */
    h1, h2, h3, p, div, .stMarkdown { 
        font-family: 'Inter', sans-serif; 
        color: #FAFAFA; 
    }
    
    /* CAPTIONS */
    .stCaptionContainer {
        color: #A0AEC0 !important;
    }
</style>
"""

CARD_CSS = """
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    
    body { 
        font-family: 'Inter', sans-serif; 
        background: transparent;
        padding: 20px;
    }
    
    /* ASSET HEADER */
    .asset-header { 
        font-family: 'Space Grotesk', sans-serif; 
        font-size: 36px; 
        font-weight: 700; 
        color: #FAFAFA; 
        margin: 50px 0 25px 0; 
        padding: 20px;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%);
        border-radius: 15px;
        border-left: 5px solid #667eea;
        backdrop-filter: blur(10px);
    }
    
    /* CARDS GRID */
    .cards-grid { 
        display: grid; 
        grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); 
        gap: 25px;
        margin-bottom: 30px;
    }
    
    /* MODERN CARD - FIXED HEIGHT */
    .modern-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(15px);
        border-radius: 25px;
        padding: 28px;
        display: flex;
        flex-direction: column;
        position: relative;
        color: #1A1A2E;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        border: 2px solid rgba(255, 255, 255, 0.2);
        height: 520px;
        min-height: 520px;
        max-height: 520px;
        overflow: hidden;
    }
    
    .modern-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 6px;
        background: linear-gradient(90deg, #FF6B6B, #FFE66D, #4ECDC4);
        border-radius: 25px 25px 0 0;
    }
    
    .modern-card:hover { 
        transform: translateY(-10px) scale(1.02);
        box-shadow: 0 20px 60px rgba(0,0,0,0.4);
        border-color: rgba(102, 126, 234, 0.6);
    }
    
    /* CARD HEADER - FIXED HEIGHT */
    .card-header { 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        margin-bottom: 15px;
        height: 32px;
        min-height: 32px;
        max-height: 32px;
        flex-shrink: 0;
    }
    
    /* TAGS - FIXED HEIGHT */
    .tag { 
        padding: 6px 14px; 
        border-radius: 50px; 
        font-size: 11px; 
        font-weight: 800; 
        text-transform: uppercase;
        letter-spacing: 0.5px;
        height: 28px;
        line-height: 16px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    
    .tag-style { 
        background: linear-gradient(135deg, #E2E8F0, #CBD5E0); 
        color: #2D3748;
        border: 1px solid #A0AEC0;
    }
    
    .rec-long { 
        background: linear-gradient(135deg, #06FFA5, #4ECDC4);
        color: #0F4C3A;
        box-shadow: 0 3px 10px rgba(6, 255, 165, 0.3);
    }
    
    .rec-short { 
        background: linear-gradient(135deg, #FF6B6B, #E63946);
        color: white;
        box-shadow: 0 3px 10px rgba(255, 107, 107, 0.3);
    }
    
    .rec-watch { 
        background: linear-gradient(135deg, #FFE66D, #FFA500);
        color: #854d0e;
        box-shadow: 0 3px 10px rgba(255, 230, 109, 0.3);
    }
    
    /* TICKER - FIXED HEIGHT */
    .card-ticker { 
        font-family: 'Space Grotesk', sans-serif; 
        font-size: 28px; 
        font-weight: 700; 
        color: #0F172A; 
        margin: 10px 0;
        height: 36px;
        min-height: 36px;
        max-height: 36px;
        line-height: 36px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex-shrink: 0;
    }
    
    /* NAME - FIXED HEIGHT */
    .card-name { 
        font-size: 14px; 
        color: #64748B; 
        margin-bottom: 12px;
        height: 20px;
        min-height: 20px;
        max-height: 20px;
        line-height: 20px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex-shrink: 0;
    }
    
    /* SUMMARY TEXT - FIXED HEIGHT */
    .summary-text { 
        font-size: 15px; 
        font-weight: 600; 
        color: #1E293B; 
        line-height: 1.4; 
        margin-bottom: 15px; 
        border-left: 4px solid #667eea; 
        padding-left: 12px;
        height: 84px;
        min-height: 84px;
        max-height: 84px;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 4;
        -webkit-box-orient: vertical;
        text-overflow: ellipsis;
        flex-shrink: 0;
    }
    
    /* DRIVERS LIST - FIXED HEIGHT */
    .drivers-list { 
        margin: 0 0 15px 0; 
        padding-left: 20px; 
        font-size: 13px; 
        color: #475569;
        height: 90px;
        min-height: 90px;
        max-height: 90px;
        overflow: hidden;
        flex-shrink: 0;
    }
    
    .drivers-list li {
        margin-bottom: 6px;
        line-height: 1.4;
    }
    
    /* LEVELS BOX - FIXED HEIGHT */
    .levels-box { 
        background: linear-gradient(135deg, #F8FAFC, #EDF2F7);
        border-radius: 15px; 
        padding: 14px; 
        border: 2px solid #E2E8F0;
        display: grid; 
        grid-template-columns: 1fr 1fr; 
        gap: 10px; 
        margin-bottom: 15px;
        height: 90px;
        min-height: 90px;
        max-height: 90px;
        flex-shrink: 0;
    }
    
    .level-item { 
        font-size: 10px; 
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .level-val { 
        font-size: 14px; 
        font-weight: 700; 
        color: #0F172A; 
        display: block; 
        margin-top: 4px;
    }
    
    /* CTA BUTTON - FIXED HEIGHT */
    .cta-button {
        display: flex; 
        align-items: center; 
        justify-content: center; 
        width: 100%; 
        height: 48px;
        min-height: 48px;
        max-height: 48px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; 
        text-decoration: none; 
        font-weight: 700;
        font-family: 'Space Grotesk', sans-serif;
        border-radius: 15px; 
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: auto;
        transition: all 0.3s ease;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        flex-shrink: 0;
    }
    
    .cta-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.6);
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* CONTENT WRAPPER */
    .card-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }
</style>
"""