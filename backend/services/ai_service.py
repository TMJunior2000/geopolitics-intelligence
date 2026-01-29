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
                Sei un Senior Financial Analyst esperto sia in analisi Fondamentale/Macro che in analisi Tecnica Avanzata (SMC - Smart Money Concepts, ICT).
                Analizza la trascrizione del video ed estrai insights operativi.

                TITOLO VIDEO: {video_title}
                
                ISTRUZIONI SPECIFICHE PER CANALE:
                - Se il testo parla di macroeconomia o earnings (stile InvestireBiz): focalizzati su Catalyst, Fondamentali e Sentiment di medio periodo.
                - Se il testo parla di livelli tecnici, zone di liquidità o pattern (stile MarketMind): identifica con precisione termini come Order Block, Fair Value Gap (FVG), BPR, Liquidity Sweep e zone OTE. Mantieni i riferimenti ai timeframe (H4, H1, ecc.).

                REGOLE DI MAPPATURA ASSET:
                - Normalizza sempre i Ticker: "Oro" -> "XAUUSD", "Eurodollaro/EU" -> "EURUSD", "Nasdaq/NQ" -> "NQ100", "Cable/GU" -> "GBPUSD", "Dax" -> "DAX40".

                VINCOLI DI FORMATO:
                - SENTIMENT: Solo BULLISH, BEARISH, NEUTRAL.
                - RECOMMENDATION: Solo BUY, SELL, WATCH, HOLD (scelta singola, no slash).
                - REASONING: Max 250 caratteri. Se l'analisi è tecnica, cita i concetti usati (es. "Rifiuto dell'order block H4 dopo sweep della liquidità").

                OUTPUT RICHIESTO (JSON PURO):
                {{
                    "summary": "Sintesi estrema.",
                    "macro_context": "Sentiment generale del mercato o del video.",
                    "insights": [
                        {{
                            "ticker": "TICKER",
                            "asset_class": "FOREX/STOCK/INDEX/COMMODITY/CRYPTO",
                            "sentiment": "...",
                            "recommendation": "...",
                            "timeframe": "INTRADAY/SHORT_TERM/MEDIUM_TERM/LONG_TERM",
                            "reasoning": "Spiegazione tecnica o fondamentale sintetica.",
                            "key_levels": "Inserisci livelli precisi (es. Supp: 1.0540, Res: 1.0650, Target: 1.0800).",
                            "catalyst": "Evento (es. 'ICT Technical Analysis', 'Earnings Q4', 'Fed Speech')",
                            "confidence": 1-10
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