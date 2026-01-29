import time
from core.config import Config
from database.repository import MarketRepository
from backend.services.youtube_service import YouTubeService
from backend.services.apify_service import ApifyService
from backend.services.ai_service import AIService

def run_pipeline(mode: str):
    print(f"🚀 PIPELINE START | Mode: {mode}")
    
    # Iniezione dipendenze
    repo = MarketRepository()
    yt = YouTubeService()
    apify = ApifyService()
    ai = AIService()

    for handle in Config.YOUTUBE_HANDLES:
        print(f"\n🔍 Channel: {handle}")
        videos = yt.get_videos(handle, mode)
        
        for v in videos:
            print(f"   Video: {v['title'][:40]}...")
            
            # Controllo esistenza nel DB
            if repo.video_exists(v['url']):
                print("      ⏭️ Skipped (Exists)")
                continue
            
            # Scarico Trascrizione
            transcript = apify.get_transcript(v['url'])
            if not transcript: 
                print("      ⚠️ No transcript found")
                continue
            
            v['content'] = transcript
            
            # --- CORREZIONE QUI ---
            # Passiamo sia la trascrizione CHE il titolo del video
            analysis = ai.analyze_video(transcript, v['title'])
            # ----------------------
            
            if analysis:
                repo.save_analysis_transaction(v, analysis)
            else:
                print("      ❌ Analisi AI fallita o vuota.")
            
            # Pausa per evitare rate limit aggressivi
            print("      ⏳ Attesa per rispetto quote Gemini (35s)...")
            time.sleep(35)