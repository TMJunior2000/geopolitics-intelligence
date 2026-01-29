from datetime import datetime
from googleapiclient.discovery import build
from core.config import Config

class YouTubeService:
    def __init__(self):
        self.service = build('youtube', 'v3', developerKey=Config.GOOGLE_API_KEY)

    def get_videos(self, handle: str, mode: str = "LIVE") -> list:
        videos = []
        
        # --- CONFIGURAZIONE DATE PER BACKFILL ---
        BACKFILL_START_DATE = datetime(2026, 1, 12)
        BACKFILL_END_DATE = datetime(2026, 1, 13, 23, 59, 59)
        
        print(f"   📡 YouTube Fetch: {handle} | Mode: {mode}")

        try:
            # 1. Ottieni ID Uploads del canale
            res = self.service.channels().list(part="contentDetails,snippet", forHandle=handle).execute()
            if not res.get('items'):
                print(f"      ⚠️ Canale non trovato: {handle}")
                return []
            
            upl_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            ch_title = res['items'][0]['snippet']['title']
            
            # 2. Loop di Paginazione (Fondamentale per il Backfill)
            next_page_token = None
            searching = True
            
            while searching:
                # Richiediamo sempre 50 item per pagina per ottimizzare le quote API
                pl = self.service.playlistItems().list(
                    part="snippet", 
                    playlistId=upl_id, 
                    maxResults=50, 
                    pageToken=next_page_token
                ).execute()
                
                items = pl.get('items', [])
                if not items:
                    break

                for i in items:
                    video_id = i['snippet']['resourceId']['videoId']
                    title = i['snippet']['title']
                    pub_str = i['snippet']['publishedAt'] # Es: 2026-01-28T10:00:00Z
                    
                    # Parsifica la data (rimuovendo la Z finale per compatibilità datetime base)
                    pub_dt = datetime.strptime(pub_str.replace('Z', ''), "%Y-%m-%dT%H:%M:%S")

                    # --- LOGICA LIVE ---
                    if mode == "LIVE":
                        # In Live prendiamo solo gli ultimi 3 video in assoluto e ci fermiamo
                        videos.append({
                            "id": video_id,
                            "title": title,
                            "date": pub_str,
                            "url": f"https://www.youtube.com/watch?v={video_id}",
                            "ch_title": ch_title
                        })
                        if len(videos) >= 3:
                            searching = False
                            break
                    
                    # --- LOGICA BACKFILL ---
                    elif mode == "BACKFILL":
                        # Se il video è nel range, lo prendiamo
                        if BACKFILL_START_DATE <= pub_dt <= BACKFILL_END_DATE:
                            videos.append({
                                "id": video_id,
                                "title": title,
                                "date": pub_str,
                                "url": f"https://www.youtube.com/watch?v={video_id}",
                                "ch_title": ch_title
                            })
                        
                        # Se il video è più vecchio della data di inizio, STOP (abbiamo finito)
                        elif pub_dt < BACKFILL_START_DATE:
                            print(f"      🛑 Trovato video del {pub_dt.date()} (pre-range). Stop.")
                            searching = False
                            break
                        
                        # Se il video è più recente della data di fine (futuro rispetto al range), continuiamo a cercare
                        # (non facciamo nulla in questo ramo else)

                # Gestione Paginazione
                next_page_token = pl.get('nextPageToken')
                if not next_page_token or not searching:
                    break
                    
        except Exception as e:
            print(f"❌ YouTube API Error ({handle}): {e}")
            
        return videos