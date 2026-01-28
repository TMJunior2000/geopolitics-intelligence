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
# Se hai problemi con l'import, assicurati che sia installato nel main.yml
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
# 1. STRATEGIA TESTO (PRIORITÀ 1 - Veloce e Sicura)
# =========================

def get_transcript_text(video_id: str) -> str:
    """Scarica i sottotitoli. Molto meno soggetto a blocchi rispetto a yt-dlp."""
    try:
        ytt_api = YouTubeTranscriptApi()
        # Recupera la lista dei sottotitoli disponibili
        transcript_list = ytt_api.list(video_id)
        
        try:
            # Cerca Italiano o Inglese
            transcript = transcript_list.find_transcript(['it', 'en'])
        except:
            # Se non c'è, prendi il primo (es. auto-generated) e traduci
            first_transcript = next(iter(transcript_list))
            transcript = first_transcript.translate('it')

        transcript_data = transcript.fetch()
        
        # Unisce il testo
        text_parts = []
        for item in transcript_data:
            if isinstance(item, dict):
                text_parts.append(item.get('text', ''))
            elif hasattr(item, 'text'):
                text_parts.append(item.text)
                
        return " ".join(text_parts)
    except Exception:
        # Silenzioso: se fallisce, torneremo stringa vuota e proveremo altro
        return ""

# =========================
# 2. STRATEGIA AUDIO (PRIORITÀ 2 - Fallback)
# =========================

def download_audio_force_ipv4(video_url: str) -> Optional[str]:
    """Scarica audio solo se i sottotitoli falliscono."""
    temp_dir = "temp_audio"
    if not os.path.exists(temp_dir): os.makedirs(temp_dir)
    
    unique_name = f"audio_{uuid.uuid4()}"
    output_path = os.path.join(temp_dir, unique_name)

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
        'noplaylist': True,
        'source_address': '0.0.0.0', # Forza IPv4
        'force_ipv4': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        # User Agent Mobile per tentare di aggirare il blocco "Sign in"
        'user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36',
        'ignoreerrors': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        final_path = output_path + ".mp3"
        if os.path.exists(final_path) and os.path.getsize(final_path) > 1000:
            return final_path
        return None
    except Exception:
        return None

def transcribe_assemblyai(file_path: str) -> str:
    try:
        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(language_code="it")
        transcript = transcriber.transcribe(file_path, config=config)
        
        if transcript.status == aai.TranscriptStatus.error:
            return ""
        return transcript.text if transcript.text else ""
    except:
        return ""

# =========================
# 3. INTELLIGENZA & DB
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
    except Exception as e:
        return {"summary": f"Errore AI: {str(e)}"}

def get_source_id(name: str, ch_id: str) -> Optional[str]:
    try:
        res = supabase.table("sources").select("id").eq("name", name).execute()
        if res.data and len(res.data) > 0:
            first = cast(Dict[str, Any], res.data[0])
            return str(first['id'])
            
        new = supabase.table("sources").insert({
            "name": name, 
            "type": "youtube", 
            "base_url": f"https://youtube.com/channel/{ch_id}"
        }).execute()
        
        if new.data and len(new.data) > 0:
            first_new = cast(Dict[str, Any], new.data[0])
            return str(first_new['id'])
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
# LOOP PRINCIPALE (Logica Invertita)
# =========================

def process_video(video):
    print(f"🔄 Processing: {video['title'][:50]}...")
    full_text = ""
    used_method = "N/A"

    # [PRIORITÀ 1] SOTTOTITOLI (Bypassa il blocco bot di yt-dlp)
    print("   📜 Tentativo 1: Transcript API...")
    full_text = get_transcript_text(video['id'])
    
    if full_text:
        used_method = "Transcript API"
        print("   ✅ Testo recuperato dai sottotitoli.")

    # [PRIORITÀ 2] AUDIO DOWNLOAD (Solo se sopra fallisce)
    if not full_text:
        print("   ⚠️ Sottotitoli assenti. Tentativo 2: Audio Download (yt-dlp)...")
        mp3_path = download_audio_force_ipv4(video['url'])
        if mp3_path:
            print("   🎙️  Audio scaricato! Trascrivo...")
            full_text = transcribe_assemblyai(mp3_path)
            if full_text: 
                used_method = "Audio (AssemblyAI)"
                os.remove(mp3_path)
        else:
            print("   ❌ Audio bloccato da YouTube.")

    # [PRIORITÀ 3] DESCRIZIONE (Ultima spiaggia)
    if not full_text:
        print("   ⚠️ Fallback finale: Uso la Descrizione.")
        full_text = f"TITOLO: {video['title']}\nDESCRIZIONE: {video['description']}"
        used_method = "Descrizione"

    # ANALISI E SALVATAGGIO
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
    except Exception as e:
        print(f"   ❌ Errore DB: {e}")

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