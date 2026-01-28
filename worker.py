import os
import json
import time
import uuid
import datetime as dt
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, cast

# --- LIBRERIE ---
import yt_dlp
import assemblyai as aai
from youtube_transcript_api import YouTubeTranscriptApi
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
# STRATEGIA 1: AUDIO DOWNLOAD (POTENZIATO CON CURL_CFFI)
# =========================

def download_audio_impersonate(video_url: str) -> Optional[str]:
    """
    Scarica l'audio usando l'impersonificazione TLS (curl_cffi) come da documentazione.
    Bypassa il blocco bot simulando un browser Chrome reale.
    """
    temp_dir = "temp_audio"
    if not os.path.exists(temp_dir): os.makedirs(temp_dir)
    
    unique_name = f"audio_{uuid.uuid4()}"
    output_path = os.path.join(temp_dir, unique_name)

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
        'noplaylist': True,
        
        # --- OPZIONI ANTI-BLOCCO DALLA DOCS ---
        # Richiede pip install "yt-dlp[default,curl-cffi]"
        'impersonate': 'chrome', 
        
        # Forza l'uso di client Android (spesso non bloccati)
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web_creator'],
                'skip': ['hls', 'dash']
            }
        },
        
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        print(f"   🎙️  Tentativo download con impersonate='chrome'...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        final_path = output_path + ".mp3"
        if os.path.exists(final_path) and os.path.getsize(final_path) > 1000:
            return final_path
        return None
    except Exception as e:
        print(f"   ❌ Errore yt-dlp impersonate: {e}")
        return None

def transcribe_assemblyai(file_path: str) -> str:
    try:
        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(language_code="it")
        transcript = transcriber.transcribe(file_path, config=config)
        if transcript.status == aai.TranscriptStatus.error: return ""
        return transcript.text if transcript.text else ""
    except: return ""

# =========================
# STRATEGIA 2: SOTTOTITOLI (FALLBACK)
# =========================

def get_transcript_text(video_id: str) -> str:
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        try:
            transcript = transcript_list.find_transcript(['it', 'en'])
        except:
            transcript = next(iter(transcript_list)).translate('it')
        
        data = transcript.fetch()
        text_parts = []
        for item in data:
            if isinstance(item, dict): text_parts.append(item.get('text', ''))
            elif hasattr(item, 'text'): text_parts.append(item.text)
        return " ".join(text_parts)
    except: return ""

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

    # PRIORITÀ 1: DOWNLOAD AUDIO con IMPERSONATE
    mp3_path = download_audio_impersonate(video['url'])
    if mp3_path:
        print("   🎙️  Audio scaricato (Impersonate)! Trascrivo...")
        full_text = transcribe_assemblyai(mp3_path)
        if full_text: 
            used_method = "Audio (AssemblyAI)"
            os.remove(mp3_path)
    
    # PRIORITÀ 2: SOTTOTITOLI
    if not full_text:
        print("   ⚠️ Audio fallito. Provo Sottotitoli...")
        full_text = get_transcript_text(video['id'])
        if full_text: used_method = "Transcript"

    # PRIORITÀ 3: DESCRIZIONE
    if not full_text:
        print("   ⚠️ Fallback finale: Uso Descrizione.")
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