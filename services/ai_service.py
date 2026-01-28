import json
from typing import Dict, Any, cast
from google import genai
from google.genai import types
from config import Config

class AIService:
    def __init__(self):
        self.client = genai.Client(api_key=Config.GOOGLE_API_KEY)

    def analyze_video(self, text: str) -> Dict[str, Any]:
        """Analizza il testo e restituisce un dizionario strutturato."""
        if not text or len(text) < 100: return {}
        
        # Tronca per sicurezza, anche se Gemini regge molto
        truncated_text = text[:Config.MAX_CHARS_AI]
        print(f"   🧠 [AI] Analisi in corso su {len(truncated_text)} caratteri...")

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

        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1 # Bassa temperatura per determinismo
                )
            )
            
            raw_json = res.text if res.text else "{}"
            # Pulizia extra nel caso Gemini aggiunga markdown ```json
            clean_json = raw_json.replace("```json", "").replace("```", "").strip()
            
            return cast(Dict[str, Any], json.loads(clean_json))
            
        except Exception as e:
            print(f"      ❌ Errore AI: {e}")
            return {}