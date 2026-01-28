import os
import json
import time
import uuid
import shutil
import datetime as dt
from datetime import datetime, timezone
from typing import List, Optional, Dict

# --- LIBRERIE ESTERNE ---
import yt_dlp
import assemblyai as aai
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
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
BACKFILL_START = dt.date(2026, 1, 1)
BACKFILL_END = dt.date(2026, 1, 31)

YOUTUBE_CHANNELS = ["@InvestireBiz"]

# Init Clients
aai.settings.api_key = ASSEMBLYAI_KEY
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)

# =========================
# LOGICA DI DOWNLOAD (STRATEGIA TRIPLA)
# =========================

def download_audio_android_strategy(video_url: str) -> Optional[str]:
    """Prova a scaricare usando l'API Android (spesso non bloccata)."""
    temp_dir = "temp_audio"
    if not os.path.exists(temp_dir): os.makedirs(temp_dir)
    
    unique_name = f"audio_{uuid.uuid4()}"
    output_path = os.path.join(temp_dir, unique_name)

    # Configurazione "Android Mobile"
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
        'noplaylist': True,
        # TRUCCO: Usiamo il client Android che è meno controllato
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return output_path + ".mp3"
    except Exception as e:
        print(f"   ⚠️ Metodo Android fallito: {e}")
        return None

def get_transcript_text(video_id: str) -> str:
    """FALLBACK: Scarica i sottotitoli se l'audio è bloccato."""
    try:
        # Usa proxy vuoto o configurazione base
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Cerca IT o EN
        try:
            transcript = transcript_list.find_transcript(['it', 'en'])
        except:
            transcript = transcript_list[0].translate('it')

        transcript_data = transcript.fetch()
        return " ".join([item['text'] for item in transcript_data])
    except Exception as e:
        print(f"   ⚠️ Fallback Transcript fallito: {e}")
        return ""

def transcribe_with_assemblyai(file_path: str) -> str:
    """Trascrive file audio."""
    transcriber = aai.Transcriber()
    config = aai.TranscriptionConfig(language_code="it")
    try:
        transcript = transcriber.transcribe(file_path, config=config)
        return transcript.text if transcript.status != aai.TranscriptStatus.error else ""
    except:
        return ""

# =========================
# INTELLIGENZA ARTIFICIALE
# =========================

def analyze_with_gemini(text: str) -> dict:
    if not text or len(text) < 50:
        return {"summary": "N/A", "risk_level": "LOW", "countries_involved": []}
        
    prompt = """
    Analizza il testo. Restituisci JSON:
    { "summary": "...", "countries_involved": [], "risk_level": "LOW/MEDIUM/HIGH", "keywords": [] }
    """
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"{prompt}\n\nTESTO:\n{text[:30000]}",
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text.replace("```json", "").replace("```", "").strip())
    except Exception as e:
        return {"summary": f"Errore AI: {str(e)}"}

# =========================
# MAIN LOOP
# =========================

def process_video(video):
    print(f"🔄 Processing: {video['title'][:40]}...")
    full_text = ""

    # TENTATIVO 1: SCARICA AUDIO (Massima Qualità)
    mp3_path = download_audio_android_strategy(video['url'])
    
    if mp3_path and os.path.exists(mp3_path):
        print("   🎙️  Audio scaricato! Trascrivo con AssemblyAI...")
        full_text = transcribe_with_assemblyai(mp3_path)
        os.remove(mp3_path) # Pulizia
    
    # TENTATIVO 2: FALLBACK SOTTOTITOLI (Se audio bloccato)
    if not full_text:
        print("   ⚠️ Audio bloccato/fallito. Passo ai Sottotitoli YouTube...")
        full_text = get_transcript_text(video['id'])

    # TENTATIVO 3: DESCRIZIONE (Disperazione)
    if not full_text:
        print("   ⚠️ Sottotitoli assenti. Uso la Descrizione.")
        full_text = f"{video['title']}\n{video['description']}"

    # ANALISI E SALVATAGGIO
    print("   🧠 Analisi Gemini...")
    analysis = analyze_with_gemini(full_text)

    # Salva DB (Logica semplificata)
    # ... (Il tuo codice di salvataggio Supabase qui) ...
    # Assicurati di usare get_or_create_source e insert come nel tuo vecchio script
    
    # ESEMPIO RAPIDO SALVATAGGIO:
    source_id = get_or_create_source_helper(video['channel_title'], video['channel_id'])
    supabase.table("intelligence_feed").insert({
        "source_id": source_id,
        "title": video['title'],
        "url": video['url'],
        "published_at": video['published_at'].isoformat(),
        "content": full_text,
        "analysis": analysis,
        "raw_metadata": {"video_id": video['id']}
    }).execute()
    print("   💾 Salvato.")
    time.sleep(5)

# Helper funzioni rimaste uguali (get_channel_videos, etc...)
# Inserisci qui le funzioni helper dal codice precedente (get_channel_videos_official, url_exists, ecc.)
# Per brevità non le riscrivo tutte, ma SONO NECESSARIE.
# Assicurati di includere: get_channel_videos_official, url_exists, get_or_create_source

# --- AGGIUNGI QUI SOTTO LE FUNZIONI HELPER CHE AVEVI NEL CODICE PRECEDENTE ---
def get_channel_videos_official(handle):
    # ... (Copia dal codice precedente) ...
    videos = []
    try:
        ch_res = youtube_service.channels().list(part="id,contentDetails,snippet", forHandle=handle).execute()
        if not ch_res['items']: return []
        uploads = ch_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        ch_title = ch_res['items'][0]['snippet']['title']
        ch_id = ch_res['items'][0]['id']
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

def url_exists(url):
    res = supabase.table("intelligence_feed").select("id").eq("url", url).execute()
    return len(res.data) > 0

def get_or_create_source_helper(name, ch_id):
    res = supabase.table("sources").select("id").eq("name", name).execute()
    if res.data: return res.data[0]['id']
    new = supabase.table("sources").insert({"name": name, "type": "youtube", "base_url": f"https://youtube.com/channel/{ch_id}"}).execute()
    return new.data[0]['id'] if new.data else None

if __name__ == "__main__":
    print(f"--- START (MODE={MODE}) ---")
    for handle in YOUTUBE_CHANNELS:
        videos = get_channel_videos_official(handle)
        for video in videos:
            if url_exists(video['url']): continue
            process_video(video)