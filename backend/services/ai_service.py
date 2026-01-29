import json
import time
import re
from typing import Dict, Any, List
from google import genai
from google.genai import types
from core.config import Config

class AIService:
    def __init__(self):
        self.client = genai.Client(api_key=Config.GOOGLE_API_KEY)

    def analyze_video(self, text: str, video_title: str) -> Dict[str, Any]:
        """
        Analizza la trascrizione ed estrae insights strutturati per il DB.
        """
        if not text or len(text) < 100: return {}
        
        # Troncatura per sicurezza (Gemini 2.0 Flash ha una finestra ampia, ma stiamo sicuri)
        truncated_text = text[:Config.MAX_CHARS_AI]
        
        prompt = f"""
        # Ruolo
        Agisci come un Analista Finanziario AI Senior. Analizza la trascrizione del video, identifica il tipo di analisi e estrai dati strutturati per una Dashboard di Trading.

        # Contesto Input
        Identifica lo stile di analisi per ogni asset basandoti sulle keyword:
        1. **Analisi Tecnica (MarketMind)**: Cerca "BPR", "FVG", "Order Block", "Sweep", "Liquidity", "H1/H4". Focus su livelli di prezzo precisi.
        2. **Analisi Fondamentale (Investire.biz)**: Cerca "EPS", "Fatturato", "Capex", "Macro", "Fed", "Geopolitica". Focus su driver economici.
        3. **Analisi Quantitativa (Investire.biz Trading)**: Cerca "Stagionalità", "COT Report", "Forecaster", "Probabilità", "Correlazioni". Focus su finestre temporali.

        # Istruzioni Estrazione Campi
        - **asset_ticker**: Ticker standard (es. EURUSD, NVDA, BTC).
        - **recommendation**: Scegli tra "LONG" (o BUY), "SHORT" (o SELL), "WATCH" (osservare livello), "HOLD" (mantenere).
        - **sentiment**: "Bullish", "Bearish", "Neutral/Range".
        - **time_horizon**: "Intraday", "Multiday/Weekly", "Medium Term", "Long Term".
        - **entry_zone / target / stop**: Estrai SOLO se vengono citati numeri o zone specifiche (es. "Order Block H1", "zona 4800"). Altrimenti null.
        - **key_drivers**: Lista sintetica dei motivi (max 3, es. ["Rottura struttura H4", "Stagionalità negativa Febbraio"]).

        # Formato Output (JSON Rigoroso)
        Restituisci ESCLUSIVAMENTE un oggetto JSON valido, senza markdown:
        {{
            "video_summary": "Sintesi del tema principale del video (max 200 caratteri).",
            "macro_sentiment": "Sentiment globale del video (es. RISK_ON, DOLLAR_WEAKNESS, TECH_EARNINGS_FOCUS).",
            "assets": [
                {{
                    "asset_ticker": "...",
                    "asset_name": "...",
                    "channel_style": "Tecnica" | "Fondamentale" | "Quantitativa",
                    "sentiment": "...",
                    "recommendation": "...",
                    "time_horizon": "...",
                    "entry_zone": "...",
                    "target_price": "...",
                    "stop_invalidation": "...",
                    "key_drivers": ["...", "..."],
                    "summary_card": "Frase operativa breve per la card UI (max 25 parole)."
                }}
            ]
        }}

        # Input Dati
        Titolo Video: {video_title}
        Trascrizione:
        {truncated_text}
        """

        # --- LOGICA DI RETRY (Exponential Backoff) ---
        max_retries = 5
        wait_time = 60 

        for attempt in range(max_retries):
            try:
                res = self.client.models.generate_content(
                    model="gemini-flash-latest", 
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.0 # Temperatura bassa per output deterministico
                    )
                )
                
                raw_json = res.text
                if not raw_json:
                    continue
                # Pulizia nel caso Gemini inserisca markdown
                clean_json = raw_json.replace("```json", "").replace("```", "").strip()
                
                return json.loads(clean_json)

            except Exception as e:
                print(f"      ⚠️ Errore AI (Tentativo {attempt+1}): {e}")
                if "429" in str(e): # Rate limit
                    time.sleep(wait_time)
                    wait_time += 30
                else:
                    break
        
        return {}