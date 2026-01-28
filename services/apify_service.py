from typing import Optional, Dict, Any, List, cast
from apify_client import ApifyClient
from config import Config

class ApifyService:
    def __init__(self):
        self.client = ApifyClient(Config.APIFY_TOKEN)

    def get_transcript(self, video_url: str) -> str:
        """Scarica e pulisce la trascrizione gestendo le stranezze dell'Actor."""
        print(f"   ☁️ [APIFY] Richiesta per: {video_url}")
        
        try:
            run = self.client.actor(Config.APIFY_ACTOR_ID).call(run_input={"videoUrls": video_url})
            if not run: return ""
            
            full_text = []
            dataset_items = self.client.dataset(run["defaultDatasetId"]).iterate_items()
            
            for item in dataset_items:
                if not isinstance(item, dict): continue
                
                # Logica "scavatrice" per pintostudio
                data_content = item.get("data")
                
                # Caso Lista (comune)
                if isinstance(data_content, list):
                    for segment in data_content:
                        if isinstance(segment, dict):
                            # Priorità alle chiavi comuni
                            txt = segment.get("text") or segment.get("caption") or segment.get("transcript")
                            if txt: full_text.append(str(txt))
                            
                # Caso Stringa 
                elif isinstance(data_content, str):
                    full_text.append(data_content)
                
                # Caso Fallback (livello radice)
                else:
                    txt = item.get("text") or item.get("transcript")
                    if txt: full_text.append(str(txt))

            clean_text = " ".join(full_text).strip()
            if clean_text:
                print(f"      ✅ Testo scaricato: {len(clean_text)} caratteri")
            return clean_text
            
        except Exception as e:
            print(f"      ❌ Errore Apify: {e}")
            return ""