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
                Sei un Senior Financial Analyst istituzionale. Il tuo compito è analizzare la trascrizione di un video finanziario ed estrarre segnali di trading e analisi di mercato strutturate.

                TITOLO VIDEO: {video_title}
                
                ISTRUZIONI DI ANALISI:
                1. Identifica ogni ASSET finanziario menzionato (Azioni, Forex, Crypto, Indici, Commodities).
                2. Normalizza il TICKER. Se parli di un settore o certificato, usa il ticker del componente principale o un ETF rappresentativo (es. 'URA' per Nucleare, 'QUBT' per Quantum). Se è una stock, usa il ticker ufficiale (es. 'TSLA', 'META')
                3. Determina il SENTIMENT (DEVE essere uno tra: BULLISH, BEARISH, NEUTRAL).
                4. Determina la RACCOMANDAZIONE (DEVE essere uno tra: BUY, SELL, WATCH, HOLD).
                5. Estrai i LIVELLI CHIAVE (Supporti, Resistenze, Target, Stop Loss) se presenti.
                6. Sintetizza il REASONING (Motivazione): max 200 caratteri. Includi se l'analisi è basata su Macro, Tecnica o Fondamentale.
                7. Identifica il CATALYST (es. "Earnings Q4", "Dati Inflazione", "Stagionalità Febbraio").

                VINCOLI DI FORMATO (IMPORTANTE):
                - Non usare mai slash o combinazioni di valori (es. NO "HOLD/BUY", NO "BULLISH/NEUTRAL"). 
                - Scegli sempre e solo UN valore tra quelli permessi.
                - Se sei incerto tra due raccomandazioni, scegli la più prudente (WATCH).

                OUTPUT RICHIESTO (JSON PURO, nessun markdown):
                {{
                    "summary": "Riassunto generale del video in 2 frasi.",
                    "macro_context": "Breve descrizione del sentiment macroeconomico.",
                    "insights": [
                        {{
                            "ticker": "TICKER_SYMBOL",
                            "asset_class": "FOREX, STOCK, CRYPTO, INDEX, o COMMODITY",
                            "sentiment": "BULLISH, BEARISH, o NEUTRAL",
                            "recommendation": "BUY, SELL, WATCH, o HOLD",
                            "timeframe": "INTRADAY, SHORT_TERM, MEDIUM_TERM, o LONG_TERM",
                            "reasoning": "Sintesi operativa.",
                            "key_levels": "Supp: 1.0500, Res: 1.0650",
                            "catalyst": "Evento principale",
                            "confidence": 8
                        }}
                    ]
                }}

                TRASCRIZIONE:
                {truncated_text}
                """

        # --- LOGICA DI RETRY (Exponential Backoff) ---
        max_retries = 3
        wait_time = 10 

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
                    wait_time *= 2
                else:
                    break
        
        return {}