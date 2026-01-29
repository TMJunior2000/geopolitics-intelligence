from datetime import datetime
from googleapiclient.discovery import build
from core.config import Config

class YouTubeService:
    def __init__(self):
        self.service = build('youtube', 'v3', developerKey=Config.GOOGLE_API_KEY)

    def get_videos(self, handle: str, mode: str = "LIVE") -> list:
        videos = []
        try:
            res = self.service.channels().list(part="contentDetails,snippet", forHandle=handle).execute()
            if not res.get('items'): return []
            
            upl_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            ch_title = res['items'][0]['snippet']['title']
            
            # Logica LIVE vs BACKFILL semplificata per brevità
            # (Nel backfill reale useresti la logica delle date che avevi nel worker.py originale)
            max_res = 50 if mode == "BACKFILL" else 3
            
            pl = self.service.playlistItems().list(
                part="snippet", playlistId=upl_id, maxResults=max_res
            ).execute()
            
            for i in pl.get('items', []):
                videos.append({
                    "id": i['snippet']['resourceId']['videoId'],
                    "title": i['snippet']['title'],
                    "date": i['snippet']['publishedAt'],
                    "url": f"https://www.youtube.com/watch?v={i['snippet']['resourceId']['videoId']}",
                    "ch_title": ch_title
                })
        except Exception as e:
            print(f"❌ YouTube Error ({handle}): {e}")
        return videos