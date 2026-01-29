from apify_client import ApifyClient
from core.config import Config

class ApifyService:
    def __init__(self):
        self.client = ApifyClient(Config.APIFY_TOKEN)

    def get_transcript(self, video_url: str) -> str:
        print(f"   ☁️ [APIFY] Fetching: {video_url}")
        try:
            run = self.client.actor(Config.APIFY_ACTOR_ID).call(run_input={"videoUrls": [video_url]})
            if not run: return ""
            
            full_text = []
            dataset = self.client.dataset(run["defaultDatasetId"]).iterate_items()
            
            for item in dataset:
                data = item.get("data")
                if isinstance(data, list):
                    for seg in data:
                        if isinstance(seg, dict):
                            txt = seg.get("text") or seg.get("caption")
                            if txt: full_text.append(str(txt))
                elif isinstance(data, str):
                    full_text.append(data)
                else:
                    txt = item.get("text")
                    if txt: full_text.append(str(txt))

            return " ".join(full_text).strip()
        except Exception as e:
            print(f"      ❌ Apify Error: {e}")
            return ""