import os
from typing import List

# Carica variabili d'ambiente (se usi python-dotenv localmente)
# from dotenv import load_dotenv; load_dotenv()

class Config:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    APIFY_TOKEN: str = os.getenv("APIFY_TOKEN", "")
    
    # Canali da monitorare
    YOUTUBE_HANDLES: List[str] = ["@InvestireBiz"]
    
    # Limiti
    MAX_CHARS_AI: int = 150000 # Ampia finestra per Gemini 2.0 Flash
    
    # Apify Actor ID (quello che abbiamo validato)
    APIFY_ACTOR_ID: str = "pintostudio/youtube-transcript-scraper"

    @classmethod
    def validate(cls):
        if not all([cls.SUPABASE_URL, cls.SUPABASE_KEY, cls.GOOGLE_API_KEY, cls.APIFY_TOKEN]):
            raise ValueError("❌ ERRORE: Variabili d'ambiente mancanti.")

# Validazione immediata all'import
try:
    Config.validate()
except ValueError as e:
    print(e)
    exit(1)