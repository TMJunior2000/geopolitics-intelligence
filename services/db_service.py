from typing import List, Dict, Any, Optional, cast
from supabase import create_client, Client
from config import Config

class DBService:
    def __init__(self):
        self.client: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

    def video_exists(self, url: str) -> bool:
        res = self.client.table("intelligence_feed").select("id").eq("url", url).execute()
        return len(res.data) > 0

    def get_source_id(self, name: str) -> int:
        """Ottiene ID sorgente o lo crea se non esiste."""
        res = self.client.table("sources").select("id").eq("name", name).execute()
        if res.data and len(res.data) > 0:
            return int(cast(Dict[str, Any], res.data[0]).get('id', 0))
        
        # Crea se manca
        new = self.client.table("sources").insert({"name": name}).execute()

        if new.data and len(new.data) > 0:
            return int(cast(Dict[str, Any], new.data[0]).get('id', 0))
        
        raise Exception(f"Failed to create or retrieve source: {name}")

    def save_analysis(self, video_data: Dict[str, Any], analysis: Dict[str, Any]):
        """Transazione logica: salva video e poi i suoi insights."""
        try:
            # 1. Salva Feed
            source_id = self.get_source_id(video_data['ch_title'])
            
            feed_payload = {
                "source_id": source_id,
                "title": video_data['title'],
                "url": video_data['url'],
                "published_at": video_data['date'],
                "content": video_data['content'], # Testo completo
                "summary": analysis.get("summary", "N/A"),
                "raw_metadata": {"vid": video_data['id']}
            }
            
            res_feed = self.client.table("intelligence_feed").insert(feed_payload).execute()
            if not res_feed.data: raise Exception("Errore insert feed")
            
            video_db_id = int(cast(Dict[str, Any], res_feed.data[0]).get('id', 0))
            print(f"      💾 Feed salvato (ID: {video_db_id})")

            # 2. Salva Market Insights (Iteriamo sugli asset trovati)
            insights = analysis.get("assets_analyzed", [])
            if insights:
                rows_to_insert = []
                for item in insights:
                    rows_to_insert.append({
                        "video_id": video_db_id,
                        "asset_ticker": item.get("ticker", "UNKNOWN").upper(),
                        "sentiment": item.get("sentiment", "NEUTRAL"),
                        "timeframe": item.get("timeframe", "MEDIUM"),
                        "key_levels": item.get("key_levels", ""),
                        "ai_reasoning": item.get("reasoning", "")
                    })
                
                self.client.table("market_insights").insert(rows_to_insert).execute()
                print(f"      💾 Salvati {len(rows_to_insert)} insights operativi.")
                
        except Exception as e:
            print(f"      ❌ Errore DB Transaction: {e}")

    def get_dashboard_data(self):
        """Query complessa per la dashboard: Insights recenti + Segnali."""
        # Nota: Supabase-py non supporta join facili come SQLAlchemy, facciamo due chiamate
        # In produzione useremmo una VIEW SQL o una RPC function.
        
        # Prendiamo gli ultimi insights
        insights = self.client.table("market_insights")\
            .select("*, intelligence_feed(title, published_at, source_id)")\
            .order("created_at", desc=True).limit(50).execute()
            
        # Prendiamo i segnali tecnici attivi
        signals = self.client.table("technical_signals")\
            .select("*").eq("status", "PENDING").execute()
            
        return insights.data, signals.data