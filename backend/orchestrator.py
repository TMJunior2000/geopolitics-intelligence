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
            print(f"   Video: {v['title'][:30]}...")
            
            if repo.video_exists(v['url']):
                print("      ⏭️ Skipped (Exists)")
                continue
            
            transcript = apify.get_transcript(v['url'])
            if not transcript: continue
            
            v['content'] = transcript
            analysis = ai.analyze(transcript)
            
            if analysis:
                repo.save_analysis_transaction(v, analysis)