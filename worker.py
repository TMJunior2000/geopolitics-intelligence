import os
import json
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

YOUTUBE_CHANNELS = {
    "InvestireBiz": "https://www.youtube.com/@InvestireBiz/video"
}

BACKFILL_START = dt.date(2026, 1, 1)
BACKFILL_END = dt.date(2026, 1, 25)

# =========================
# INIT CLIENTS
# =========================
if not GOOGLE_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Mancano variabili d'ambiente critiche")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
except Exception as e:
    raise RuntimeError(f"Errore init client: {e}")

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
# CORE LOGIC
# =========================

def get_transcript_safe(video_id: str) -> str:
    """
    Usa l'API dei sottotitoli diretta per evitare il blocco IP su GitHub Actions.
    """
    try:
        # Cerca sottotitoli in Italiano, poi Inglese
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['it', 'en'])
        
        # Unisce i frammenti di testo
        full_text = " ".join([item['text'] for item in transcript_list])
        return full_text
    except Exception as e:
        # Se fallisce (es. sottotitoli disabilitati), logga ma non crashare
        # log(f"Niente sottotitoli per {video_id}: {e}")
        return ""

def process_youtube_channel(channel_name, channel_url):
    source_id = get_or_create_source(channel_name, "youtube", channel_url)
    
    # OPZIONI STEALTH:
    # 'extract_flat': True è FONDAMENTALE. 
    # Impedisce a yt-dlp di aprire la pagina del video (che triggera il blocco).
    # Scarica solo il JSON del feed del canale.
    ydl_opts = {
        'quiet': True,
        'extract_flat': True, 
        'playlist_items': '1-10', # Ultimi 10 video
        'ignoreerrors': True,
    }

    log(f"Scansione feed canale: {channel_name}...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(channel_url, download=False)
            entries = info.get('entries', [])

            if not entries:
                log(f"Nessun video trovato per {channel_name}")
                return

            for video in entries:
                if not video: continue

                # Dati dal feed (modalità flat)
                video_id = video.get('id')
                title = video.get('title')
                url = video.get('url') or f"https://www.youtube.com/watch?v={video_id}"
                
                # In flat mode, a volte la data non c'è o è parziale.
                # Tuttavia, di solito 'upload_date' è presente nel feed.
                raw_date = video.get('upload_date') 
                
                # Se manca la data, saltiamo per sicurezza nel backfill
                if not raw_date:
                    continue
                    
                dt_video = datetime.strptime(raw_date, "%Y%m%d").date()
                now = datetime.now(timezone.utc).date()

                # FILTRI DATE
                if MODE == "LIVE":
                    if (now - dt_video).days > 1: continue
                else: # BACKFILL
                    if not (BACKFILL_START <= dt_video <= BACKFILL_END): continue

                # CHECK DUPLICATI
                if url_exists(url):
                    log(f"Saltato (esistente): {title}")
                    continue

                log(f"Elaborazione: {title}")

                # 1. Recupero Testo (Nuovo Metodo API)
                text = get_transcript_safe(video_id)
                
                if not text:
                    # Fallback: usiamo la descrizione se non ci sono sub
                    text = " ".join([title, video.get('description', '')])
                    log("Usata descrizione (no sub)")

                # 2. Analisi AI
                analysis = analyze_with_gemini(text)

                # 3. Salvataggio
                supabase.table("intelligence_feed").insert({
                    "source_id": source_id,
                    "title": title,
                    "url": url,
                    "published_at": dt_video.isoformat(),
                    "content": text,
                    "analysis": analysis,
                    "raw_metadata": {"id": video_id}
                }).execute()
                
                log(f"✅ Salvato: {title}")

        except Exception as e:
            log(f"Errore scansione {channel_name}: {e}")

def analyze_with_gemini(text: str) -> dict:
    if not text or len(text) < 50:
        return {"summary": "N/A", "risk_level": "LOW", "countries_involved": [], "keywords": []}

    prompt = """
    Sei un analista geopolitico. Analizza il testo e restituisci JSON:
    {
        "summary": "riassunto italiano max 3 frasi",
        "countries_involved": ["paese1"],
        "risk_level": "LOW" | "MEDIUM" | "HIGH",
        "keywords": ["tag1"]
    }
    """
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"{prompt}\n\nTesto:\n{text[:20000]}",
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text) if response.text else {}
    except Exception as e:
        log(f"Errore AI: {e}")
        return {"summary": "Errore AI"}

def process_calendar():
    # ... (Il codice calendario rimane invariato, o copialo dallo step precedente se serve)
    pass

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    log(f"--- WORKER START (MODE={MODE}) ---")
    
    for name, url in YOUTUBE_CHANNELS.items():
        process_youtube_channel(name, url)

    # Decommenta se vuoi anche il calendario
    # try: process_calendar()
    # except: pass

    log("--- WORKER DONE ---")