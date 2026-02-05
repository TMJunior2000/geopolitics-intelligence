from datetime import datetime
import os
import json
from apify_client import ApifyClient
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from datetime import datetime, timezone, timedelta
from dateutil import parser

class TrumpWatchService:
    def __init__(self):
        # 1. Inizializzazione Apify
        self.apify_client = ApifyClient(os.getenv("APIFY_API_TOKEN"))
        
        # 2. Inizializzazione Google GenAI (Nuova SDK)
        self.ai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


    def get_latest_truths(self, mode: str = "LIVE") -> list:
        """
        Scarica i post di Trump gestendo Backfill (storico) e Live (nuovi).
        """
        print(f"🦅 Trump Watch: Controllo nuovi Truth... | Mode: {mode}")

        # --- 1. CONFIGURAZIONE DATE ---
        # Usiamo UTC perché le date dei social sono sempre in UTC
        now = datetime.now(timezone.utc)
        
        if mode == "BACKFILL":
            # Range: Dal 1 Gennaio 2026 a Oggi
            start_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
            # Stimiamo che Trump faccia max 10 post al giorno. 
            # 35 giorni x 10 post = 350. Mettiamo 500 per sicurezza.
            run_max_items = 500 
            run_monitoring = False # Disattiva memoria per prendere lo storico
        else:
            # Mode LIVE: Ci interessano solo le ultime 24h o i nuovi
            start_date = now - timedelta(days=1) 
            run_max_items = 10      # Pochi post, solo i freschissimi
            run_monitoring = True   # Attiva memoria (scarica solo i delta)

        # --- 2. CONFIGURAZIONE APIFY ---
        run_input = {
            "startUrls": ["https://truthsocial.com/@realDonaldTrump"],
            "maxItems": run_max_items,
            "monitoringMode": run_monitoring,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }

        # --- 3. ESECUZIONE ---
        try:
            run = self.apify_client.actor("memo23/truth-social-profile-scraper-with-posts").call(run_input=run_input)
            
            if not run:
                print("⚠️ Trump Watch: Errore avvio Actor Apify.")
                return []

            # Recupera i risultati grezzi
            dataset_items = self.apify_client.dataset(run["defaultDatasetId"]).list_items().items
            
            if not dataset_items:
                print("🦅 Trump Watch: Nessun post restituito dallo scraper.")
                return []

            # --- 4. FILTRO DATE (Python Side) ---
            valid_posts = []
            print(f"   📉 Filtro {len(dataset_items)} post grezzi per data (Start: {start_date.strftime('%Y-%m-%d')})...")

            for item in dataset_items:
                # Truth Social restituisce la data in 'created_at' (ISO format string)
                raw_date = item.get('created_at')
                if not raw_date: continue

                try:
                    # Parsiamo la data stringa in oggetto datetime
                    post_date = parser.parse(raw_date)
                    
                    # Se la data del post è DOPO la data di inizio, lo teniamo
                    if post_date >= start_date:
                        valid_posts.append(item)
                except Exception as e:
                    print(f"   ⚠️ Errore parsing data post: {e}")
                    continue

            print(f"🦅 Trump Watch: Selezionati {len(valid_posts)} post validi nel range temporale.")
            return valid_posts

        except Exception as e:
            print(f"⚠️ Errore critico Apify Trump Watch: {e}")
            return []

    def clean_html(self, raw_html):
        """Rimuove i tag HTML dal post di Truth Social"""
        if not raw_html: return ""
        # BeautifulSoup estrae solo il testo pulito
        return BeautifulSoup(raw_html, "html.parser").get_text(separator=" ").strip()

    def analyze_market_impact(self, post_item):
        """
        Chiede a Gemini se il post può muovere i mercati (Nuova SDK)
        """
        # Estrazione del testo (Truth Social usa spesso 'content' con HTML)
        raw_text = post_item.get('content') or post_item.get('text') or ""
        clean_text = self.clean_html(raw_text)
        created_at = post_item.get('created_at')

        # Filtro rumore: se il post è troppo breve, ignoralo
        if len(clean_text) < 15:
            return None

        print(f"   🔎 Analizzo Truth: {clean_text[:50]}...")

        prompt = f"""
        Sei un Senior Risk Manager AI. Analizza questo post di Donald Trump su Truth Social.
        
        DATA POST: {created_at}
        TESTO: "{clean_text}"
        
        Compito: Identifica se contiene annunci concreti che muovono il mercato (DAZI, GUERRA, FED, DOLLARO, CRYPTO).
        Ignora propaganda politica generica.
        
        Rispondi ESCLUSIVAMENTE con questo schema JSON:
        {{
            "impact_score": (intero 1-5, dove 5 = Alta Volatilità Immediata),
            "summary_it": "Sintesi brevissima in italiano (max 10 parole)",
            "assets_affected": ["Lista Ticker", "es: USD, BTC, NQ100"],
            "trade_direction": "BULLISH" o "BEARISH" o "NEUTRAL"
        }}
        """

        try:
            # Chiamata con la NUOVA sintassi google.genai
            response = self.ai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json" # Forza output JSON pulito
                )
            )

            if not response.text:
                return None
            
            # Parsing diretto (grazie a response_mime_type non servono replace strani)
            return json.loads(response.text)

        except Exception as e:
            print(f"⚠️ Errore analisi AI Trump: {e}")
            return None