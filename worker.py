import os
import json
import time
import uuid
import requests
import datetime as dt
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, cast

# --- LIBRERIE ---
# yt-dlp rimosso (non serve più, usiamo API esterne)
import assemblyai as aai
from googleapiclient.discovery import build
from google import genai
from google.genai import types
from supabase import create_client, Client

# =========================
# CONFIGURAZIONE
# =========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ASSEMBLYAI_KEY = os.getenv("ASSEMBLYAI_KEY")
MODE = os.getenv("MODE", "LIVE").upper()

if not SUPABASE_URL or not SUPABASE_KEY or not GOOGLE_API_KEY or not ASSEMBLYAI_KEY:
    raise ValueError("❌ ERRORE: Variabili d'ambiente mancanti.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)
aai.settings.api_key = ASSEMBLYAI_KEY

YOUTUBE_CHANNELS = ["@InvestireBiz"]

# =========================
# STRATEGIA AUDIO (VIA COBALT API)
# =========================

def download_audio_via_cobalt(video_url: str) -> Optional[str]:
    """
    Usa istanze Cobalt pubbliche per scaricare l'audio MP3.
    Questo bypassa totalmente il blocco IP di GitHub verso YouTube.
    """
    # Lista di istanze Cobalt (API)
    instances = [
        "https://api.cobalt.tools",
        "https://co.wuk.sh",
        "https://cobalt.xy24.eu.org",
        "https://cobalt.q1.si"
    ]
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    temp_dir = "temp_audio"
    if not os.path.exists(temp_dir): os.makedirs(temp_dir)
    filename = os.path.join(temp_dir, f"audio_{uuid.uuid4()}.mp3")

    print("   🎙️  Richiedo Audio a Cobalt (External API)...")

    for base_url in instances:
        try:
            # 1. Chiediamo a Cobalt di preparare l'MP3
            payload = {
                "url": video_url,
                "vCodec": "h264",
                "vQuality": "720",
                "aFormat": "mp3", # Vogliamo MP3
                "isAudioOnly": True # Solo audio
            }
            
            api_url = f"{base_url}/api/json"
            res = requests.post(api_url, json=payload, headers=headers, timeout=15)
            
            if res.status_code != 200:
                continue

            data = res.json()
            
            # 2. Otteniamo il link diretto per il download
            download_url = data.get("url")
            if not download_url:
                continue
                
            # 3. Scarichiamo il file fisicamente
            print(f"   ⬇️  Scaricamento MP3 da: {base_url}...")
            mp3_res = requests.get(download_url, stream=True, timeout=30)
            
            if mp3_res.status_code == 200:
                with open(filename, 'wb') as f:
                    for chunk in mp3_res.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Verifica che il file non sia vuoto
                if os.path.getsize(filename) > 1000:
                    return filename
        
        except Exception as e:
            # print(f"Errore Cobalt {base_url}: {e}")
            continue
            
    return None

def transcribe_assemblyai(file_path: str) -> str:
    """Invia l'audio ad AssemblyAI."""
    try:
        print("   🤖 Invio audio ad AssemblyAI...")
        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(language_code="it")
        transcript = transcriber.transcribe(file_path, config=config)
        
        if transcript.status == aai.TranscriptStatus.error:
            print(f"   ❌ Errore Trascrizione: {transcript.error}")
            return ""
        return transcript.text if transcript.text else ""
    except Exception as e:
        print(f"   ❌ Eccezione AssemblyAI: {e}")
        return ""

# =========================
# UTILS & ANALISI
# =========================

def analyze_gemini(text: str) -> dict:
    if not text or len(text) < 50:
        return {"summary": "N/A", "risk_level": "LOW", "countries_involved": []}
    
    prompt = """
    Analizza il testo. Output JSON ESCLUSIVO:
    {
        "summary": "Riassunto italiano",
        "countries_involved": ["Paese1"],
        "risk_level": "LOW",
        "keywords": ["tag1"],
        "key_takeaway": "Concetto chiave"
    }
    """
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"{prompt}\n\nTESTO:\n{text[:30000]}",
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        if not response.text: return {"summary": "Errore AI vuota"}
        return json.loads(response.text.replace("```json", "").replace("```", "").strip())
    except Exception as e: return {"summary": str(e)}

def get_source_id(name: str, ch_id: str) -> Optional[str]:
    try:
        res = supabase.table("sources").select("id").eq("name", name).execute()
        if res.data: return str(cast(Dict[str, Any], res.data[0])['id'])
        new = supabase.table("sources").insert({"name": name, "type": "youtube", "base_url": f"https://youtube.com/channel/{ch_id}"}).execute()
        if new.data: return str(cast(Dict[str, Any], new.data[0])['id'])
        return None
    except: return None

def url_exists(url: str) -> bool:
    try:
        res = supabase.table("intelligence_feed").select("id").eq("url", url).execute()
        return len(res.data) > 0 if res.data else False
    except: return False

def get_channel_videos(handle):
    videos = []
    try:
        ch_res = youtube_service.channels().list(part="id,contentDetails,snippet", forHandle=handle).execute()
        if not ch_res.get('items'): return []
        item = ch_res['items'][0]
        uploads = item['contentDetails']['relatedPlaylists']['uploads']
        ch_title = item['snippet']['title']
        ch_id = item['id']
        pl_res = youtube_service.playlistItems().list(part="snippet", playlistId=uploads, maxResults=10).execute()
        for item in pl_res.get('items', []):
            s = item['snippet']
            videos.append({
                "id": s['resourceId']['videoId'],
                "title": s['title'],
                "description": s['description'],
                "published_at": datetime.fromisoformat(s['publishedAt'].replace('Z', '+00:00')),
                "url": f"https://www.youtube.com/watch?v={s['resourceId']['videoId']}",
                "channel_title": ch_title, "channel_id": ch_id
            })
    except: pass
    return videos

# =========================
# MAIN LOOP
# =========================

def process_video(video):
    print(f"🔄 Processing: {video['title'][:50]}...")
    full_text = ""
    used_method = "N/A"

    # 1. SCARICA AUDIO (Via Cobalt)
    mp3_path = download_audio_via_cobalt(video['url'])
    
    if mp3_path:
        # TRASCRIZIONE
        full_text = transcribe_assemblyai(mp3_path)
        if full_text: 
            used_method = "Audio (Cobalt+Assembly)"
        else:
            print("   ⚠️ Trascrizione audio fallita.")
        
        # Pulizia file
        if os.path.exists(mp3_path):
            os.remove(mp3_path)
    else:
        print("   ❌ Download Audio Cobalt fallito.")

    # 2. FALLBACK DESCRIZIONE (Se Cobalt fallisce)
    if not full_text:
        print("   ⚠️ Fallback: Uso Descrizione.")
        full_text = f"TITOLO: {video['title']}\nDESCRIZIONE: {video['description']}"
        used_method = "Descrizione"

    print(f"   🧠 Analisi Gemini ({used_method})...")
    analysis = analyze_gemini(full_text)

    try:
        source_id = get_source_id(video['channel_title'], video['channel_id'])
        if source_id:
            supabase.table("intelligence_feed").insert({
                "source_id": source_id,
                "title": video['title'],
                "url": video['url'],
                "published_at": video['published_at'].isoformat(),
                "content": full_text,
                "analysis": analysis,
                "raw_metadata": {"video_id": video['id'], "method": used_method}
            }).execute()
            print("   💾 Salvato.")
    except Exception as e: print(f"❌ DB Error: {e}")

    time.sleep(2)

if __name__ == "__main__":
    print(f"--- 🚀 WORKER START (MODE={MODE}) ---")
    for handle in YOUTUBE_CHANNELS:
        print(f"📡 Scansione: {handle}")
        videos = get_channel_videos(handle)
        for video in videos:
            if url_exists(video['url']): continue
            process_video(video)
    print("--- ✅ WORKER FINISHED ---")