import os
import sys
import json
import datetime as dt
from typing import List
import yt_dlp
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
    "InvestireBiz": "https://www.youtube.com/@InvestireBiz"
}

# Date per backfill
BACKFILL_START = dt.date(2026, 1, 1)
BACKFILL_END = dt.date(2026, 1, 25)

# Assicuriamo che la cartella esista
os.makedirs("transcripts", exist_ok=True)

# =========================
# INIT CLIENTS
# =========================
if not GOOGLE_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Mancano delle variabili d'ambiente critiche")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
except Exception as e:
    raise RuntimeError(f"Errore inizializzazione client: {e}")

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
# CORE LOGIC (Adattata dal tuo script locale)
# =========================
def fetch_and_process_youtube(channel_name, channel_url):
    source_id = get_or_create_source(channel_name, "youtube", channel_url)
    
    # OPZIONI IDENTICHE AL TUO SCRIPT LOCALE
    # Ma adattate per Linux (Deno è nel PATH)
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'extract_flat': False, # IMPORTANTE: Scarica i metadati completi subito
        
        # Usa 'deno' dal sistema (installato via scraper.yml) per bypassare i bot check
        # Nota: Su linux basta dire che il path è 'deno' se è nel PATH globale
        'js_runtimes': {
            'deno': {'path': 'deno'} 
        },
        
        'playlist_items': '1-10', # Controlliamo gli ultimi 10 video
        'skip_download': True,
        'writesubtitles': True,             
        'writeautomaticsub': True,          
        'subtitleslangs': ['it'],     
        'subtitlesformat': 'vtt',    
        'outtmpl': {'default': 'transcripts/%(id)s.%(ext)s'},       
    }

    log(f"Avvio scansione canale: {channel_name}...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(channel_url, download=True)
            entries = info.get('entries', [])

            if not entries:
                log(f"Nessun video trovato nel feed di {channel_name}")
                return

            for video in entries:
                if video is None: continue

                # 1. Gestione Data
                raw_date = video.get('upload_date')
                if not raw_date: continue
                
                dt_video = datetime.strptime(raw_date, "%Y%m%d").date()
                now = datetime.now(timezone.utc).date()

                # Filtro DATE
                if MODE == "LIVE":
                    # Accetta video di oggi o ieri
                    if (now - dt_video).days > 1: continue
                else: 
                    # Backfill range
                    if not (BACKFILL_START <= dt_video <= BACKFILL_END): continue

                # Controllo Duplicati DB
                video_url = video.get('webpage_url')
                if url_exists(video_url):
                    log(f"Saltato (già presente): {video.get('title')}")
                    continue

                log(f"Elaborazione: {video.get('title')} ({dt_video})")

                # 2. Recupero Percorso Sottotitoli (Metodo Robusto)
                transcript_path = None
                requested_subtitles = video.get('requested_subtitles')
                if requested_subtitles and 'it' in requested_subtitles:
                    transcript_path = requested_subtitles['it'].get('filepath')

                # 3. Lettura Contenuto
                full_text = ""
                if transcript_path and os.path.exists(transcript_path):
                    try:
                        with open(transcript_path, 'r', encoding='utf-8') as f:
                            # Pulizia base VTT
                            raw_content = f.read()
                            lines = raw_content.splitlines()
                            clean_lines = []
                            for line in lines:
                                if "-->" in line or line.startswith("WEBVTT") or not line.strip(): continue
                                # Rimuovi tag <c>...</c> ecc
                                import re
                                line = re.sub(r'<[^>]+>', '', line).strip()
                                if line and (not clean_lines or line != clean_lines[-1]):
                                    clean_lines.append(line)
                            full_text = " ".join(clean_lines)
                            
                        # Pulizia file
                        os.remove(transcript_path)
                    except Exception as e:
                        log(f"Errore lettura VTT: {e}")

                # Se non abbiamo sottotitoli, usiamo la descrizione
                if not full_text:
                    full_text = video.get('description', '')
                    log("Usata descrizione video (sottotitoli mancanti)")

                # 4. Analisi AI
                analysis = analyze_with_gemini(full_text)

                # 5. Salvataggio su Supabase
                supabase.table("intelligence_feed").insert({
                    "source_id": source_id,
                    "title": video.get('title'),
                    "url": video_url,
                    "published_at": dt_video.isoformat(),
                    "content": full_text,
                    "analysis": analysis,
                    "raw_metadata": {"id": video.get('id')}
                }).execute()

                log(f"✅ Salvato: {video.get('title')}")

        except Exception as e:
            log(f"Errore critico durante scansione {channel_name}: {e}")

def analyze_with_gemini(text: str) -> dict:
    if not text or len(text) < 50:
        return {"summary": "Contenuto non disponibile", "risk_level": "LOW", "countries_involved": [], "keywords": []}

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
    
    # Processa YouTube
    for name, url in YOUTUBE_CHANNELS.items():
        fetch_and_process_youtube(name, url)
        
    ## Processa Calendario
    #try:
    #    process_calendar()
    #except Exception as e:
    #    log(f"Errore calendario: {e}")

    log("--- WORKER DONE ---")