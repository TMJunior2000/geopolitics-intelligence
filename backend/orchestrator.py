import time
import sys
from core.config import Config
from database.repository import MarketRepository
from backend.services.youtube_service import YouTubeService
from backend.services.apify_service import ApifyService
from backend.services.ai_service import AIService
from backend.services.trump_service import TrumpWatchService

def run_pipeline(mode: str):
    print(f"🚀 PIPELINE START | Mode: {mode}")
    
    # Iniezione dipendenze
    repo = MarketRepository()
    yt = YouTubeService()
    trump_truth = TrumpWatchService()
    apify = ApifyService()
    ai = AIService()

    # ==============================================================================
    # 1. BLOCCO YOUTUBE (Analisi Tecnica / Macro)
    # ==============================================================================
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
            
            # Analisi AI
            analysis = ai.analyze_video(transcript, v['title'])
            
            if analysis:
                # Salvataggio Video + Insights
                repo.save_analysis_transaction(v, analysis)
            else:
                print("      ❌ Analisi AI fallita o vuota.")
            
            # Pausa per evitare rate limit aggressivi di Gemini
            print("      ⏳ Attesa per rispetto quote Gemini (30s)...")
            time.sleep(30)

    # ==============================================================================
    # 2. BLOCCO TRUMP WATCH (Truth Social - Geopolitica/News)
    # ==============================================================================
    print(f"\n🦅 Analyzing Trump Post (Truth Social)...")
    
    # Se mode="BACKFILL" scarica storico, altrimenti solo nuovi
    is_backfill = (mode == "BACKFILL")
    post_trump_truth = trump_truth.get_latest_truths(mode=mode)

    if not post_trump_truth:
        print("   💤 Nessun post da analizzare.")
    else:
        print(f"   ⚡ Trovati {len(post_trump_truth)} post. Avvio analisi AI...")
    
    for post_trump in post_trump_truth:
        # A. Analisi AI (Impact Score & Asset Detection)
        analysis = trump_truth.analyze_market_impact(post_trump)
        
        if not analysis:
            continue

        # B. Alerting Console
        score = analysis.get('impact_score', 0)
        summary = analysis.get('summary_it', 'N/A')
        print(f"   📊 Score: {score}/5 | {summary}")
        
        # C. Salvataggio DB
        # Salviamo se lo score è rilevante (>=3) oppure se siamo in BACKFILL
        if score >= 3 or is_backfill:
            
            if score >= 4:
                print(f"   🚨 HIGH IMPACT ALERT: {analysis.get('assets_affected', [])}")
                
            # Costruzione pacchetto dati semplificato
            signal_data = {
                "url": post_trump['url'],
                # Gestione robusta del contenuto (Truth Social usa 'content' o 'text')
                "content": post_trump.get('content') or post_trump.get('text', ''),
                "created_at": post_trump['created_at'],
                "ai_analysis": analysis # Passiamo tutto il JSON (score, assets, sentiment)
            }
            
            # CHIAMATA AL NUOVO METODO SPECIFICO
            repo.save_trump_signal(signal_data)
            
        # Piccola pausa per cortesia verso le API
        time.sleep(5)