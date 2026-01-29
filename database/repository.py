from typing import List, Dict, Any, cast
import json
from .connection import get_db_client

class MarketRepository:
    def __init__(self):
        self.client = get_db_client()

    def video_exists(self, url: str) -> bool:
        res = self.client.table("intelligence_feed").select("id").eq("url", url).execute()
        return len(res.data) > 0

    def get_source_id(self, name: str, base_url: str = "") -> int:
        res = self.client.table("sources").select("id").eq("name", name).execute()
        if res.data and len(res.data) > 0:
            return int(cast(Dict[str, Any], res.data[0]).get('id', 0))
        
        payload = {"name": name}
        if base_url: payload["base_url"] = base_url
        new = self.client.table("sources").insert(payload).execute()
        
        if new.data:
            return int(cast(Dict[str, Any], new.data[0]).get('id', 0))
        raise Exception(f"Failed to source ID for: {name}")

    def save_analysis_transaction(self, video_data: Dict[str, Any], analysis: Dict[str, Any]):
        try:
            channel_name = video_data.get('ch_title', 'Unknown Channel')
            search_url = f"https://www.youtube.com/results?search_query={channel_name.replace(' ', '+')}"
            source_id = self.get_source_id(channel_name, base_url=search_url)

            # 1. Salva Feed (Intelligence Feed)
            feed_payload = {
                "source_id": source_id,
                "title": video_data['title'],
                "url": video_data['url'],
                "published_at": video_data['date'],
                "content": video_data.get('content', '')[:100000],
                "summary": analysis.get("video_summary", "N/A"),
                "macro_sentiment": analysis.get("macro_sentiment", "NEUTRAL"),
                "raw_metadata": {"vid": video_data['id']}
            }
            
            res_feed = self.client.table("intelligence_feed").insert(feed_payload).execute()
            video_db_id = int(cast(Dict[str, Any], res_feed.data[0]).get('id', 0))
            print(f"      💾 DB: Feed salvato (ID: {video_db_id})")

            # 2. Salva Market Insights
            assets_list = analysis.get("assets", [])
            for item in assets_list:
                # Normalizzazione Recommendation
                rec = str(item.get("recommendation", "WATCH")).upper()
                if any(x in rec for x in ["LONG", "BUY"]): rec = "LONG"
                elif any(x in rec for x in ["SHORT", "SELL"]): rec = "SHORT"
                elif "HOLD" in rec: rec = "HOLD"
                else: rec = "WATCH"

                self.client.table("market_insights").insert({
                    "video_id": video_db_id,
                    "asset_ticker": item.get("asset_ticker", "UNKNOWN").upper(),
                    "asset_name": item.get("asset_name"),
                    "channel_style": item.get("channel_style"),
                    "sentiment": item.get("sentiment"),
                    "recommendation": rec,
                    "time_horizon": item.get("time_horizon"),
                    "entry_zone": item.get("entry_zone"),
                    "target_price": item.get("target_price"),
                    "stop_invalidation": item.get("stop_invalidation"),
                    "key_drivers": item.get("key_drivers", []),
                    "summary_card": item.get("summary_card")
                }).execute()
                
            print(f"      💾 DB: Salvati {len(assets_list)} insights.")
        except Exception as e:
            print(f"      ❌ DB Error: {e}")

    def get_all_insights_flat(self) -> List[Dict[str, Any]]:
        try:
            response = self.client.table("market_insights")\
                .select("*, intelligence_feed(title, published_at, url, source_id, summary, macro_sentiment)")\
                .order("created_at", desc=True)\
                .execute()
            
            flat_data = []
            for item in (response.data or []):
                item = cast(Dict[str, Any], item)
                feed = item.pop('intelligence_feed', {}) or {}
                item['video_title'] = feed.get('title')
                item['published_at'] = feed.get('published_at')
                item['video_url'] = feed.get('url')
                item['video_summary'] = feed.get('summary')
                item['video_macro'] = feed.get('macro_sentiment')
                flat_data.append(item)
            return flat_data
        except Exception as e:
            print(f"❌ DB Fetch Error: {e}")
            return []