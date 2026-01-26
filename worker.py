import os
import sys
import json
import re
import datetime as dt
from typing import List
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
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
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# URL dei canali
YOUTUBE_CHANNELS = {
    "InvestireBiz": "https://www.youtube.com/@InvestireBiz",
    "MarketMind": "https://www.youtube.com/@MarketMind" 
}

BACKFILL_START = dt.date(2026, 1, 1)
BACKFILL_END = dt.date(2026, 1, 25)

# =========================
# INIT CLIENTS
# =========================

if not GOOGLE_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Mancano delle variabili d'ambiente")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
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

# =========================
# YOUTUBE LOGIC
# =========================
def fetch_youtube_videos(channel_url) -> List[dict]:
    # Configurazione "Stealth"
    # Usiamo 'extract_flat' per prendere solo i metadati dalla playlist/feed
    # SENZA aprire la pagina del singolo video (che triggera il blocco)
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,  # FONDAMENTALE: Non scarica info video, solo lista
        'playlist_items': '1-10', # Controlliamo gli ultimi 10 video
        'ignoreerrors': True,
    }

    videos = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            
            entries = info.get('entries', [])
            if not entries:
                log(f"Nessun video trovato per {channel_url}")
                return []

            for video in entries:
                if not video: continue
                
                # In modalità flat, a volte mancano alcuni campi, gestiamo i fallback
                video_id = video.get('id')
                title = video.get('title')
                url = video.get('url') or f"https://www.youtube.com/watch?v={video_id}"
                
                # Gestione Data: extract_flat a volte non da la data esatta.
                # Se manca, assumiamo sia oggi per LIVE o saltiamo per BACKFILL se siamo incerti
                # Tuttavia, spesso 'upload_date' c'è nel feed JSON iniziale.
                raw_date = video.get('upload_date')
                
                if raw_date:
                    dt_video = datetime.strptime(raw_date, "%Y%m%d").date()
                else:
                    # Fallback: Se non c'è la data, nel dubbio processiamo solo se siamo in LIVE
                    # e assumiamo sia recente. Rischioso ma necessario se l'API blocca.
                    log(f"Data mancante per {title}, skip precauzionale.")
                    continue

                # FILTRI DATE
                now = datetime.now(timezone.utc).date()
                if MODE == "LIVE":
                    # Accetta video di oggi o ieri (per fuso orario)
                    if (now - dt_video).days > 1: continue
                else: 
                    if not (BACKFILL_START <= dt_video <= BACKFILL_END):
                        continue

                videos.append({
                    'id': video_id,
                    'title': title,
                    'url': url,
                    'published_at': dt_video,
                })
                
    except Exception as e:
        log(f"Errore nel fetch lista YouTube per {channel_url}: {e}")
        
    return videos

def get_transcript_text(video_id: str) -> str:
    """
    Usa youtube-transcript-api invece di yt-dlp/audio download.
    Molto più leggero e meno soggetto a blocchi IP sui data center.
    """
    try:
        # Cerca prima in Italiano, poi Inglese
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['it', 'en'])
        
        # Concatena il testo
        full_text = " ".join([item['text'] for item in transcript_list])
        return full_text
        
    except Exception as e:
        # Se fallisce (es. sottotitoli disabilitati o blocco estremo)
        log(f"Impossibile ottenere trascrizione per {video_id}: {e}")
        return ""

def analyze_with_gemini(text: str) -> dict:
    if not text or len(text) < 50:
        return {"summary": "Contenuto non disponibile/No audio", "risk_level": "LOW", "countries_involved": [], "keywords": []}

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
    for name, channel_url in YOUTUBE_CHANNELS.items():
        try:
            log(f"Scansione canale: {name}")
            source_id = get_or_create_source(name, "youtube", channel_url)
            videos = fetch_youtube_videos(channel_url)
            log(f"Trovati {len(videos)} video potenziali per {name}")

            for v in videos:
                if url_exists(v["url"]):
                    log(f"Saltato (esistente): {v['title']}")
                    continue

                log(f"Elaborazione: {v['title']}")
                
                # 1. Ottieni Trascrizione (Metodo API Sottotitoli)
                text = get_transcript_text(v['id'])
                
                if not text:
                    log(f"Skipping analisi AI per mancanza testo: {v['title']}")
                    analysis = {"summary": "Trascrizione non disponibile", "risk_level": "LOW"}
                else:
                    # 2. Analisi AI
                    analysis = analyze_with_gemini(text)

                # 3. Salvataggio
                supabase.table("intelligence_feed").insert({
                    "source_id": source_id,
                    "title": v["title"],
                    "url": v["url"],
                    "published_at": v["published_at"].isoformat(),
                    "content": text,
                    "analysis": analysis,
                    "raw_metadata": {"id": v["id"]}
                }).execute()
                
        except Exception as e:
            log(f"Errore processamento canale {name}: {e}")

def process_calendar():
    source_id = get_or_create_source("Investing.com Calendar", "calendar", "https://www.investing.com/economic-calendar/")
    
    events = []
    if MODE == "LIVE":
        events.append({
            "title": "Daily Market Update", 
            "date": dt.date.today().isoformat(),
            "impact": "MEDIUM", 
            "country": "Global"
        })
    else:
        for d in range(1, 26):
            events.append({
                "title": f"Historical Event {d} Jan", 
                "date": dt.date(2026, 1, d).isoformat(),
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
            "published_at": e["date"],
            "content": f"Event data: {e}",
            "analysis": {"impact": e["impact"]},
            "raw_metadata": e
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