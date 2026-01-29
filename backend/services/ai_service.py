import json
import time
from typing import Dict, Any
from google import genai
from google.genai import types
from core.config import Config

class AIService:
    def __init__(self):
        self.client = genai.Client(api_key=Config.GOOGLE_API_KEY)

    def analyze(self, text: str) -> Dict[str, Any]:
        if not text or len(text) < 100: return {}
        truncated = text[:Config.MAX_CHARS_AI]
        
        prompt = f"""
        Sei un analista finanziario. Analizza la trascrizione.
        OUTPUT JSON ONLY:
        {{
            "summary": "...",
            "assets_analyzed": [
                {{ "ticker": "XAUUSD", "sentiment": "BULLISH", "reasoning": "...", "timeframe": "MEDIUM" }}
            ]
        }}
        TRASCRIZIONE: {truncated}
        """
        
        # Logica Retry semplificata
        for _ in range(3):
            try:
                res = self.client.models.generate_content(
                    model="gemini-2.0-flash", # o il modello che preferisci
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                if res.text is None:
                    continue
                clean = res.text.replace("```json", "").replace("```", "").strip()
                return json.loads(clean)
            except Exception as e:
                if "429" in str(e):
                    time.sleep(30)
                    continue
                break
        return {}