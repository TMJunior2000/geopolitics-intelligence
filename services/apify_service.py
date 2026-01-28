from urllib.parse import urlparse, parse_qs
from apify_client import ApifyClient
from config import Config

class ApifyService:
    def __init__(self):
        self.client = ApifyClient(Config.APIFY_TOKEN)

    def extract_video_id(self, url: str) -> str:
            """Estrae l'ID del video in modo sicuro per Pylance."""
            try:
                parsed = urlparse(url)
                if "youtube.com" in parsed.netloc:
                    # parse_qs restituisce un dizionario di liste: {"v": ["7zbV0cORqJc"]}
                    query_params = parse_qs(parsed.query)
                    v_params = query_params.get("v")
                    
                    # Verifichiamo che la lista esista e non sia vuota
                    if v_params and len(v_params) > 0:
                        return str(v_params[0])
                        
                elif "youtu.be" in parsed.netloc:
                    # Per gli URL accorciati tipo youtu.be/7zbV0cORqJc
                    return parsed.path.lstrip("/")
            except Exception:
                pass
                
            # In ogni altro caso (errore o URL non valido), restituiamo una stringa vuota
            return ""

    def get_transcript(self, video_url: str) -> str:
        """Scarica la trascrizione passando l'ID video invece dell'URL."""
        print(f"   ☁️ [APIFY] Richiesta per: {video_url}")
        
        video_id = self.extract_video_id(video_url)
        if not video_id:
            print("      ❌ Errore: Impossibile estrarre ID video dall'URL.")
            return ""

        # CONFIGURAZIONE CORRETTA PER ACTOR BASATI SU VIDEO_IDS
        run_input = {
            "video_ids": [video_id],  # <--- Ecco la correzione: Array di ID
            "languages": ["it"],      # Specifica la lingua
            "preferredLanguage": "it",
            "includeGenerated": True, # Accetta i sottotitoli automatici
            "format": "json"          # O "text" a seconda dell'actor
        }

        try:
            run = self.client.actor(Config.APIFY_ACTOR_ID).call(run_input=run_input)
            
            if not run: return ""
            
            items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            
            if not items:
                print("      ⚠️ Dataset vuoto (Nessun sottotitolo trovato).")
                return ""

            full_text = []
            
            # Parser Universale
            for item in items:
                # 1. Caso diretto (text/transcript)
                text_part = (
                    item.get("text") or 
                    item.get("transcript") or 
                    item.get("caption") or
                    item.get("fullText")
                )
                
                # 2. Caso lista di segmenti (comune quando si usano gli ID)
                if not text_part and isinstance(item, dict):
                     # Alcuni actor restituiscono: [{'text': 'ciao', 'start': 0}, ...]
                    if "text" in item and "start" in item:
                        text_part = item["text"]
                
                if text_part:
                    full_text.append(str(text_part))

            clean_text = " ".join(full_text).strip()
            
            if clean_text:
                print(f"      ✅ Testo scaricato: {len(clean_text)} caratteri")
                return clean_text
            else:
                print(f"      ⚠️ Parser fallito. Chiavi trovate: {list(items[0].keys())}")
                return ""
            
        except Exception as e:
            print(f"      ❌ Errore critico Apify: {e}")
            return ""