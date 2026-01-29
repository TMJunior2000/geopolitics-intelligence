import json
import time
import re
from typing import Dict, Any, cast
from google import genai
from google.genai import types
from config import Config

class AIService:
    def __init__(self):
        self.client = genai.Client(api_key=Config.GOOGLE_API_KEY)

    def analyze_video(self, text: str) -> Dict[str, Any]:
        """Analizza il testo con gestione avanzata dei Rate Limits (429)."""
        if not text or len(text) < 100: return {}
        
        # Tronca per sicurezza
        truncated_text = text[:Config.MAX_CHARS_AI]
        
        prompt = f"""
        Sei un analista finanziario istituzionale senior.
        Analizza questa trascrizione video da 'Investire.biz'.
        
        OBIETTIVO: Estrarre dati strutturati per un database di trading decisionale.
        
        ISTRUZIONI:
        1. Identifica il SENTIMENT MACRO generale (RISK_ON / RISK_OFF / NEUTRAL).
        2. Per ogni ASSET finanziario menzionato (Azioni, Forex, Crypto, Indici, Commodities):
           - Estrai il Ticker standard (es. usa XAUUSD per l'Oro, EURUSD per EuroDollaro, SPX500 per S&P).
           - Determina il sentiment specifico (BULLISH / BEARISH / NEUTRAL).
           - Cita i livelli chiave (supporti/resistenze) se detti.
           - Indica il timeframe suggerito (SHORT = Intraday, MEDIUM = Multiday/Settimanale).
        
        OUTPUT FORMAT (JSON ONLY):
        {{
            "summary": "Riassunto esecutivo in 3 frasi",
            "macro_sentiment": "RISK_ON",
            "assets_analyzed": [
                {{
                    "ticker": "XAUUSD",
                    "name": "Gold",
                    "sentiment": "BULLISH",
                    "timeframe": "MEDIUM",
                    "reasoning": "Debolezza dollaro e rottura resistenza 2050",
                    "key_levels": "Supp: 2040, Res: 2075"
                }}
            ]
        }}
        
        TRASCRIZIONE:
        {truncated_text}
        """

        # --- LOGICA DI RETRY (Exponential Backoff) ---
        max_retries = 5
        wait_time = 40 # Secondi di attesa base (Gemini chiedeva ~30-47s)

        for attempt in range(max_retries):
            try:
                print(f"   🧠 [AI] Tentativo {attempt+1}/{max_retries} ({len(truncated_text)} chars)...")
                
                res = self.client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                
                raw_json = res.text if res.text else "{}"
                clean_json = raw_json.replace("```json", "").replace("```", "").strip()
                
                # Se arriviamo qui, ha funzionato!
                return cast(Dict[str, Any], json.loads(clean_json))

            except Exception as e:
                error_msg = str(e)
                # Se è un errore di quota (429), aspettiamo e riproviamo
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    print(f"      ⚠️ Quota Gemini esaurita. Attesa {wait_time}s prima di riprovare...")
                    time.sleep(wait_time)
                    wait_time += 20 # Aumentiamo l'attesa per il prossimo tentativo (40, 60, 80...)
                else:
                    # Se è un altro errore (es. JSON malformato), ci fermiamo
                    print(f"      ❌ Errore AI irrecuperabile: {e}")
                    return {}
        
        print("      ❌ Falliti tutti i tentativi di analisi AI.")
        return {}