GLOBAL_STYLES = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Inter:wght@400;500;600&display=swap');
    .stApp { background: #0E1117; }
    h1, h2, h3, p, div { font-family: 'Inter', sans-serif; color: #FAFAFA; }
    
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
        background: #1E232F !important; color: #A0AEC0 !important; border: 1px solid #2D3748 !important;
    }
</style>
"""

CARD_CSS = """
<style>
    .modern-card {
        background: #FFFFFF; border-radius: 20px; padding: 22px;
        display: flex; flex-direction: column; position: relative;
        color: #1A1A2E; margin-bottom: 25px; transition: transform 0.2s;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid #E2E8F0;
    }
    .modern-card:hover { transform: translateY(-5px); border-color: #667eea; }
    
    /* Header & Badges */
    .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .tag { padding: 4px 10px; border-radius: 6px; font-size: 10px; font-weight: 800; text-transform: uppercase; }
    .tag-style { background: #F1F5F9; color: #64748B; border: 1px solid #E2E8F0; }
    
    .rec-long { background: #DCFCE7; color: #166534; }
    .rec-short { background: #FEE2E2; color: #991B1B; }
    .rec-watch { background: #FEF9C3; color: #854d0e; }
    
    .card-ticker { font-family: 'Space Grotesk'; font-size: 26px; font-weight: 700; color: #0F172A; margin: 0; }
    .card-name { font-size: 14px; color: #64748B; margin-bottom: 10px; }

    /* Summary & Drivers */
    .summary-text { font-size: 15px; font-weight: 600; color: #1E293B; line-height: 1.4; margin-bottom: 15px; border-left: 3px solid #667eea; padding-left: 10px; }
    .drivers-list { margin: 0 0 15px 0; padding-left: 20px; font-size: 13px; color: #475569; }

    /* Technical Box */
    .levels-box { 
        background: #F8FAFC; border-radius: 12px; padding: 12px; border: 1px solid #F1F5F9; 
        display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 15px;
    }
    .level-item { font-size: 11px; color: #64748B; }
    .level-val { font-size: 13px; font-weight: 700; color: #0F172A; display: block; }

    .cta-button {
        display: flex; align-items: center; justify-content: center; width: 100%; height: 42px;
        background: #0F172A; color: white; text-decoration: none; font-weight: 700;
        border-radius: 10px; font-size: 12px; margin-top: auto;
    }
    .cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }
    .asset-header { font-family: 'Space Grotesk'; font-size: 32px; font-weight: 700; color: #FAFAFA; margin: 40px 0 20px 0; border-bottom: 2px solid #2D3748; padding-bottom: 10px; }
</style>
"""