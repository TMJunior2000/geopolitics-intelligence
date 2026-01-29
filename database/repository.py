from typing import List, Dict, Any, cast
from .connection import get_db_client

class MarketRepository:
    def __init__(self):
        self.client = get_db_client()

    def video_exists(self, url: str) -> bool:
        res = self.client.table("intelligence_feed").select("id").eq("url", url).execute()
        return len(res.data) > 0

    def get_source_id(self, name: str) -> int:
        res = self.client.table("sources").select("id").eq("name", name).execute()
        if res.data:
            return int(cast(Dict[str, Any], res.data[0]).get('id', 0))
        
        new = self.client.table("sources").insert({"name": name}).execute()
        if new.data:
            return int(cast(Dict[str, Any], new.data[0]).get('id', 0))
        raise Exception(f"Failed to source ID for: {name}")

    def save_analysis_transaction(self, video_data: Dict[str, Any], analysis: Dict[str, Any]):
        """Salva Video e Insights in sequenza."""
        try:
            # 1. Salva Feed
            source_id = self.get_source_id(video_data['ch_title'])
            feed_payload = {
                "source_id": source_id,
                "title": video_data['title'],
                "url": video_data['url'],
                "published_at": video_data['date'],
                "content": video_data.get('content', ''),
                "summary": analysis.get("summary", "N/A"),
                "raw_metadata": {"vid": video_data['id']}
            }
            
            res_feed = self.client.table("intelligence_feed").insert(feed_payload).execute()
            if not res_feed.data: raise Exception("Errore insert feed")
            
            video_db_id = int(cast(Dict[str, Any], res_feed.data[0]).get('id', 0))
            print(f"      💾 DB: Feed salvato (ID: {video_db_id})")

            # 2. Salva Insights
            insights = analysis.get("assets_analyzed", [])
            if insights:
                rows = []
                for item in insights:
                    rows.append({
                        "video_id": video_db_id,
                        "asset_ticker": item.get("ticker", "UNKNOWN").upper(),
                        "sentiment": item.get("sentiment", "NEUTRAL"),
                        "timeframe": item.get("timeframe", "MEDIUM"),
                        "key_levels": item.get("key_levels", ""),
                        "ai_reasoning": item.get("reasoning", "")
                    })
                self.client.table("market_insights").insert(rows).execute()
                print(f"      💾 DB: Salvati {len(rows)} insights.")
                
        except Exception as e:
            print(f"      ❌ DB Error: {e}")

    def get_all_insights_flat(self) -> List[Dict[str, Any]]:
        """Restituisce dati appiattiti per Pandas (Frontend)."""
        try:
            response = self.client.table("market_insights")\
                .select("*, intelligence_feed(title, published_at, url, source_id)")\
                .order("created_at", desc=True)\
                .execute()
            
            data = response.data or []
            flat_data = []
            
            for item in data:
                if not isinstance(item, dict): continue
                feed = item.pop('intelligence_feed', {}) or {}
                
                # Appiattimento
                if isinstance(feed, dict):
                    item['video_title'] = feed.get('title', 'Unknown')
                    item['published_at'] = feed.get('published_at')
                    item['video_url'] = feed.get('url')
                    item['source_id'] = feed.get('source_id')
                else:
                    item['video_title'] = 'Unknown'
                    
                flat_data.append(item)
            return flat_data
        except Exception as e:
            print(f"❌ DB Fetch Error: {e}")
            return []