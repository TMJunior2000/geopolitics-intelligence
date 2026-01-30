GLOBAL_STYLES = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Inter:wght@400;500;600&display=swap');
    
    /* Global App Style */
    .stApp { background-color: #0E1117; }
    h1, h2, h3, p, li { font-family: 'Inter', sans-serif; }
    
    /* Buttons Styles */
    div[data-testid="column"] button {
        width: 100% !important;
        border-radius: 8px !important; 
        font-family: 'Space Grotesk' !important;
        font-weight: 700;
        border: none !important;
        transition: all 0.2s;
    }
    
    /* Custom Badges for Markdown use */
    .badge {
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 800;
        text-transform: uppercase;
        display: inline-block;
        margin-right: 8px;
    }
    .badge-long { background: #DCFCE7; color: #166534; border: 1px solid #bbf7d0; }
    .badge-short { background: #FEE2E2; color: #991B1B; border: 1px solid #fecaca; }
    .badge-watch { background: #FEF9C3; color: #854d0e; border: 1px solid #fef08a; }
    .badge-style { background: #F1F5F9; color: #475569; border: 1px solid #e2e8f0; }

    /* Technical Box Styling */
    .tech-box {
        background-color: #1E232F;
        border-radius: 8px;
        padding: 10px;
        margin-top: 10px;
        border: 1px solid #2D3748;
    }
    .tech-label { font-size: 10px; color: #A0AEC0; text-transform: uppercase; }
    .tech-val { font-size: 14px; font-weight: bold; color: #E2E8F0; }
</style>
"""

# Il vecchio CARD_CSS non serve più, lo rimuoviamo per pulizia.
CARD_CSS = ""