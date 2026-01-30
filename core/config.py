import os
from typing import List

# from dotenv import load_dotenv; load_dotenv() # Decommentare se locale

class Config:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    APIFY_TOKEN: str = os.getenv("APIFY_TOKEN", "")
    
    YOUTUBE_HANDLES: List[str] = ["@Market.Mind.trading"] #"@InvestireBiz", @investirebiz-analisi
    MAX_CHARS_AI: int = 150000
    APIFY_ACTOR_ID: str = "scrape-creators/best-youtube-transcripts-scraper"

    @classmethod
    def validate(cls):
        required = [cls.SUPABASE_URL, cls.SUPABASE_KEY, cls.GOOGLE_API_KEY, cls.APIFY_TOKEN]
        if not all(required):
            raise ValueError("❌ ERRORE CORE: Variabili d'ambiente mancanti.")

# Validazione all'import
try:
    Config.validate()
except ValueError as e:
    print(e)
    # Non usiamo exit(1) qui per permettere import parziali in test, ma lo logghiamo