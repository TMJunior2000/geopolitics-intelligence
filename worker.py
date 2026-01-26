import os
import sys
import json
import tempfile
import re
import datetime as dt
from typing import List
import yt_dlp
import requests
import assemblyai as aai
from google import genai
from google.genai import types
from supabase import create_client, Client
from datetime import datetime, timezone

# =========================
# CONFIG
# =========================
MODE = os.getenv("MODE", "LIVE").upper()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
ASSEMBLYAI_KEY = os.environ.get("ASSEMBLYAI_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Rimosso /videos per evitare errori se la tab non esiste
YOUTUBE_CHANNELS = {
    "InvestireBiz": "https://www.youtube.com/@InvestireBiz",
    "MarketMind": "https://www.youtube.com/@MarketMind" 
}

BACKFILL_START = dt.date(2026, 1, 1)
BACKFILL_END = dt.date(2026, 1, 25)

os.makedirs("transcripts", exist_ok=True)

# =========================
# INIT CLIENTS
# =========================

if not GOOGLE_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Mancano delle variabili d'ambiente")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    aai.settings.api_key = ASSEMBLYAI_KEY
    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
except Exception as e:
    raise RuntimeError(f"Errore inizializzazione var. d'ambiente: {e}")

# =========================
# UTILS
# =========================
def log(msg):
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)

def url_exists(url: str) -> bool:
    res = supabase.table("intelligence_feed").select("id").eq("url", url).execute()
    return len(res.data) > 0

def get_or_create_source(name, type_, base_url):
    res = supabase.table("sources").select("*").eq("name", name).execute()
    data = getattr(res, 'data', [])
    if data:
        return data[0]["id"]
    
    new_res = supabase.table("sources").insert({
        "name": name,
        "type": type_,
        "base_url": base_url 
    }).execute()
    new_data = getattr(new_res, 'data', [])
    return new_data[0]["id"] if new_data else None

def clean_vtt(vtt_text: str) -> str:
    lines = vtt_text.splitlines()
    clean_lines = []
    for line in lines:
        if "-->" in line or line.startswith("WEBVTT") or not line.strip():
            continue
        line = re.sub(r'<[^>]+>', '', line).strip()
        if line and (not clean_lines or line != clean_lines[-1]):
            clean_lines.append(line)
    return " ".join(clean_lines)

# =========================
# YOUTUBE LOGIC
# =========================
def fetch_youtube_videos(channel_url) -> List[dict]:
    # Configurazione anti-bot aggressiva
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False, # Necessario False per avere i metadati completi subito
        'playlist_items': '1-5', # Scarica solo gli ultimi 5 video per evitare blocchi massivi
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['it'],
        'subtitlesformat': 'vtt',
        'outtmpl': {'default': 'transcripts/%(id)s.%(ext)s'},
        
        # Trucco per bypassare "Sign in to confirm you’re not a bot"
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'skip': ['dash', 'hls']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }

    videos = []
    # Riprova in caso di errore
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Scarica info canale
            info = ydl.extract_info(channel_url, download=True)
            
            # Gestione caso "entries" (playlist/canale) o singolo video
            entries = info.get('entries', [])
            if not entries and 'title' in info:
                entries = [info]

            for video in entries:
                if not video: continue
                
                # Gestione data: yt-dlp a volte torna stringhe diverse
                raw_date = video.get('upload_date')
                if not raw_date:
                    continue
                    
                dt_video = datetime.strptime(raw_date, "%Y%m%d").date()
                now = datetime.now(timezone.utc).date()

                if MODE == "LIVE":
                    if dt_video != now: continue
                else: 
                    if not (BACKFILL_START <= dt_video <= BACKFILL_END):
                        continue

                vtt_file = None
                expected_vtt = f"transcripts/{video['id']}.it.vtt"
                if os.path.exists(expected_vtt):
                    vtt_file = expected_vtt

                videos.append({
                    'id': video.get('id'),
                    'title': video.get('title'),
                    'url': video.get('webpage_url'),
                    'published_at': dt_video,
                    'transcript_path': vtt_file
                })
                log(f"Trovato video: {video.get('title')} ({dt_video})")
                
    except Exception as e:
        log(f"Errore nel fetch YouTube per {channel_url}: {e}")
        
    return videos

def transcribe_audio(v_info: dict) -> str:
    if v_info['transcript_path'] and os.path.exists(v_info['transcript_path']):
        log(f"Utilizzo sottotitoli locali per {v_info['title']}")
        with open(v_info['transcript_path'], 'r', encoding='utf-8') as f:
            text = clean_vtt(f.read())
        try:
            os.remove(v_info['transcript_path'])
        except: pass
        return text

    log(f"Nessun sottotitolo per {v_info['title']}, avvio AssemblyAI...")
    with tempfile.TemporaryDirectory() as tmp:
        audio_opts = {
            "format": "m4a/bestaudio/best",
            "outtmpl": f"{tmp}/audio.%(ext)s",
            "quiet": True,
            # Anche qui, configurazione anti-bot
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            'http_headers': {'User-Agent': 'Mozilla/5.0'}
        }
        try:
            with yt_dlp.YoutubeDL(audio_opts) as ydl:
                ydl.download([v_info['url']])
            
            audio_files = [f for f in os.listdir(tmp) if not f.startswith('.')]
            if not audio_files: return ""
            
            audio_path = os.path.join(tmp, audio_files[0])
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(audio_path)

            if not transcript.text: return ""
            return transcript.text
        except Exception as e:
            log(f"Errore download/trascrizione audio: {e}")
            return ""

def analyze_with_gemini(text: str) -> dict:
    if not text or len(text) < 50:
        return {"summary": "Contenuto insufficiente/Non disponibile", "risk_level": "LOW", "countries_involved": [], "keywords": []}

    prompt = """
    Sei un analista geopolitico esperto. Analizza la trascrizione e restituisci SOLO JSON valido:
    {
        "summary": "riassunto in italiano max 3 frasi",
        "countries_involved": ["paese1", "paese2"],
        "risk_level": "LOW" | "MEDIUM" | "HIGH",
        "keywords": ["tag1", "tag2"]
    }
    """
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"{prompt}\n\nTesto:\n{text[:25000]}",
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )

        if not response.text: return {}
        return json.loads(response.text)
    except Exception as e:
        log(f"Errore Gemini: {e}")
        return {"summary": "Errore analisi AI", "risk_level": "LOW"}

# =========================
# PROCESSORS
# =========================
def process_youtube():
    for name, url in YOUTUBE_CHANNELS.items():
        try:
            source_id = get_or_create_source(name, "youtube", url)
            videos = fetch_youtube_videos(url)

            for v in videos:
                if url_exists(v["url"]):
                    log(f"Saltato (esistente): {v['title']}")
                    continue

                log(f"Elaborazione: {v['title']}")
                text = transcribe_audio(v)
                analysis = analyze_with_gemini(text)

                supabase.table("intelligence_feed").insert({
                    "source_id": source_id,
                    "title": v["title"],
                    "url": v["url"],
                    "published_at": v["published_at"].isoformat(), # Data convertita in stringa
                    "content": text,
                    "analysis": analysis,
                    "raw_metadata": {"id": v["id"]}
                }).execute()
        except Exception as e:
            log(f"Errore processamento canale {name}: {e}")

def process_calendar():
    source_id = get_or_create_source("Investing.com Calendar", "calendar", "https://www.investing.com/economic-calendar/")
    
    events = []
    # FIX: Convertiamo le date in stringa subito per renderle JSON serializable
    if MODE == "LIVE":
        events.append({
            "title": "Daily Market Update", 
            "date": dt.date.today().isoformat(), # STRINGA!
            "impact": "MEDIUM", 
            "country": "Global"
        })
    else:
        for d in range(1, 26):
            events.append({
                "title": f"Historical Event {d} Jan", 
                "date": dt.date(2026, 1, d).isoformat(), # STRINGA!
                "impact": "LOW", 
                "country": "IT"
            })

    for e in events:
        fake_url = f"calendar://{e['title']}-{e['date']}"
        if url_exists(fake_url): continue
        
        supabase.table("intelligence_feed").insert({
            "source_id": source_id,
            "title": e["title"],
            "url": fake_url,
            "published_at": e["date"], # Già stringa
            "content": f"Event data: {e}",
            "analysis": {"impact": e["impact"]},
            "raw_metadata": e # Ora 'e' contiene solo stringhe/tipi semplici, è serializzabile
        }).execute()

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    log(f"--- WORKER START (MODE={MODE}) ---")
    try:
        process_youtube()
        process_calendar()
        log("--- WORKER DONE ---")
    except Exception as e:
        log(f"ERRORE CRITICO GLOBALE: {e}")