import os
import json
import time
import re
from apify_client import ApifyClient
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from datetime import datetime, timezone, timedelta
from dateutil import parser

class TrumpWatchService:
    def __init__(self):
        self.apify_client = ApifyClient(os.getenv("APIFY_TOKEN"))
        self.ai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    def get_latest_truths(self, mode: str = "LIVE") -> list:
        """Scarica i post gestendo Backfill e Live."""
        print(f"🦅 Trump Watch: Controllo nuovi Truth... | Mode: {mode}")

        now = datetime.now(timezone.utc)
        
        if mode == "BACKFILL":
            # Start dal 1 Gennaio 2026
            start_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
            run_max_items = 500 
            run_monitoring = False 
        else:
            # Live: ultime 24h
            start_date = now - timedelta(days=1) 
            run_max_items = 10      
            run_monitoring = True   

        run_input = {
            "startUrls": ["https://truthsocial.com/@realDonaldTrump"],
            "maxItems": run_max_items,
            "monitoringMode": run_monitoring,
            "proxy": { "useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"] }
        }

        try:
            run = self.apify_client.actor("memo23/truth-social-profile-scraper-with-posts").call(run_input=run_input)
            if not run: return []

            dataset_items = self.apify_client.dataset(run["defaultDatasetId"]).list_items().items
            if not dataset_items: return []

            valid_posts = []
            print(f"   📉 Filtro {len(dataset_items)} post grezzi per data (Start: {start_date.strftime('%Y-%m-%d')})...")

            for item in dataset_items:
                raw_date = item.get('created_at')
                if not raw_date: continue
                try:
                    post_date = parser.parse(raw_date)
                    if post_date >= start_date:
                        valid_posts.append(item)
                except: continue

            print(f"🦅 Trump Watch: Selezionati {len(valid_posts)} post validi.")
            return valid_posts

        except Exception as e:
            print(f"⚠️ Errore Apify Trump Watch: {e}")
            return []

    def clean_html(self, raw_html):
        if not raw_html: return ""
        return BeautifulSoup(raw_html, "html.parser").get_text(separator=" ").strip()

    def _is_junk_post(self, text):
        """
        Filtra aggressivamente post inutili per risparmiare API.
        Usa Regex per catturare varianti (es. 'RT  @').
        """
        text_lower = text.lower()
        
        # 1. Filtra Retweet (RT @, ReTruth)
        # Cattura "rt @" con spazi variabili
        if re.search(r"rt\s+@", text_lower): return True
        if "retruth" in text_lower: return True

        # 2. Filtra Endorsement Politici
        keywords = [
            "endorse", "endorsement", "honor to endorse", "congressman", 
            "governor", "senator", "maga warrior", "america first patriot",
            "complete and total endorsement"
        ]
        for k in keywords:
            if k in text_lower: return True

        # 3. Filtra Auguri e Ringraziamenti
        if "happy birthday" in text_lower: return True
        if "thank you" in text_lower and len(text) < 50: return True

        # 4. Filtra Link nudi (spesso news senza commento)
        # Se il post inizia con http e non ha molto altro testo
        if text_lower.startswith("http") and len(text) < 100: return True

        return False

    def analyze_market_impact(self, post_item):
        """Analizza con Gemini gestendo Retry su errore 429."""
        raw_text = post_item.get('content') or post_item.get('text') or ""
        clean_text = self.clean_html(raw_text)
        created_at = post_item.get('created_at')

        # 1. FILTRO ANTI-SPAM (Risparmio Token)
        if self._is_junk_post(clean_text):
            # Stampa solo l'inizio per non intasare il log
            print(f"   🗑️  Skipped Junk: {clean_text[:30]}...") 
            return None

        print(f"   🔎 Analizzo Truth: {clean_text[:50]}...")

        prompt = f"""
        Sei un Senior Risk Manager AI. Analizza questo post di Donald Trump.
        DATA: {created_at}
        TESTO: "{clean_text}"
        
        Compito: Identifica annunci su: DAZI, GUERRA, FED, DOLLARO, CRYPTO, ECONOMIA...
        IGNORA: Faide personali, cause legali contro celebrità, auguri, gossip, show TV.
        Se il post parla di questi argomenti "futili", restituisci impact_score: 0 e nessun asset.
        
        Rispondi JSON:
        {{
            "impact_score": (intero 1-5),
            "summary_it": "Sintesi max 10 parole",
            "assets_affected": ["Ticker"],
            "trade_direction": "BULLISH/BEARISH/NEUTRAL"
        }}
        """

        # LOGICA DI RETRY ESPONENZIALE (Fino a 3 tentativi)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.ai_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )

                if not response.text: return None
                
                parsed = json.loads(response.text)
                if isinstance(parsed, list):
                    return parsed[0] if parsed else None
                return parsed

            except Exception as e:
                error_str = str(e)
                # Se è un errore 429 (Resource Exhausted), aspetta MOLTO di più
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    wait_time = (attempt + 1) * 30 # 30s, 60s, 90s
                    print(f"   ⚠️ Quota Gemini (429). Pausa {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"   ⚠️ Errore AI: {e}")
                    return None
        
        return None