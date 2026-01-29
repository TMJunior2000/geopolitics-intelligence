from apify_client import ApifyClient
from core.config import Config

class ApifyService:
    def __init__(self):
        self.client = ApifyClient(Config.APIFY_TOKEN)

    def get_transcript(self, video_url: str) -> str:
        """
        Scarica la trascrizione usando Apify.
        Logica di parsing ripristinata alla versione originale robusta.
        """
        print(f"   ☁️ [APIFY] Richiesta per: {video_url}")
        
        try:
            # Avvia l'Actor
            run = self.client.actor(Config.APIFY_ACTOR_ID).call(run_input={"videoUrls": [video_url]})
            
            if not run:
                print("      ❌ Apify Run Failed (No run object returned)")
                return ""
            
            # Se lo stato non è SUCCEEDED, è inutile provare a leggere
            if run.get('status') != 'SUCCEEDED':
                print(f"      ❌ Apify Run Failed with status: {run.get('status')}")
                return ""

            full_text = []
            dataset_items = self.client.dataset(run["defaultDatasetId"]).iterate_items()
            
            # --- LOGICA DI ESTRAZIONE ORIGINALE (ROBUSTA) ---
            for item in dataset_items:
                if not isinstance(item, dict): continue
                
                # Cerchiamo i dati dentro 'data' (comune in questo scraper)
                data_content = item.get("data")
                
                # CASO 1: 'data' è una Lista di segmenti (es. timestamp + testo)
                if isinstance(data_content, list):
                    for segment in data_content:
                        if isinstance(segment, dict):
                            # Priorità alle chiavi comuni: text > caption > transcript
                            txt = segment.get("text") or segment.get("caption") or segment.get("transcript")
                            if txt: 
                                full_text.append(str(txt))
                            
                # CASO 2: 'data' è una Stringa diretta
                elif isinstance(data_content, str):
                    full_text.append(data_content)
                
                # CASO 3: Fallback (livello radice dell'item)
                # Se 'data' è vuoto o null, cerchiamo direttamente 'text' o 'transcript' nella root
                else:
                    txt = item.get("text") or item.get("transcript") or item.get("caption")
                    if txt: 
                        full_text.append(str(txt))

            clean_text = " ".join(full_text).strip()
            
            if clean_text:
                print(f"      ✅ Trascrizione OK: {len(clean_text)} caratteri")
                return clean_text
            else:
                print("      ⚠️ Dataset vuoto o formato non riconosciuto.")
                return ""
            
        except Exception as e:
            print(f"      ❌ Eccezione Apify: {e}")
            return ""