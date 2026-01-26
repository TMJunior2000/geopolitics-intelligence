import os
import sys
import json
import tempfile
import datetime as dt
from typing import List

import yt_dlp
import requests
import assemblyai as aai
from google import genai
from supabase import create_client, Client

# =========================
# CONFIG
# =========================
MODE = os.getenv("MODE", "LIVE").upper()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
ASSEMBLYAI_KEY = os.environ["ASSEMBLYAI_KEY"]
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]

YOUTUBE_CHANNELS = {
    "InvestireBiz": "https://www.youtube.com/@InvestireBiz/videos",
    "MarketMind": "https://www.youtube.com/@MarketMind/videos"
}

BACKFILL_START = dt.datetime(2026, 1, 1)
BACKFILL_END = dt.datetime(2026, 1, 25)

# =========================
# INIT CLIENTS
# =========================
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

aai.settings.api_key = ASSEMBLYAI_KEY
genai.configure(api_key=GOOGLE_API_KEY)
gemini = genai.GenerativeModel("gemini-pro")

# =========================
# UTILS
# =========================
def log(msg):
    print(f"[{dt.datetime.utcnow().isoformat()}] {msg}", flush=True)


def url_exists(url: str) -> bool:
    res = supabase.table("intelligence_feed").select("id").eq("url", url).execute()
    return len(res.data) > 0


def get_or_create_source(name, type_, base_url):
    res = supabase.table("sources").select("*").eq("name", name).execute()
    if res.data:
        return res.data[0]["id"]

    res = supabase.table("sources").insert({
        "name": name,
        "type": type_,
        "base_url": base_url
    }).execute()

    return res.data[0]["id"]


# =========================
# YOUTUBE
# =========================
def fetch_youtube_videos(channel_url) -> List[dict]:
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": "in_playlist"
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)

    videos = []
    now = dt.datetime.utcnow()

    for e in info.get("entries", []):
        if not e.get("url"):
            continue

        published = dt.datetime.utcfromtimestamp(e.get("timestamp", 0))

        if MODE == "LIVE":
            if (now - published).total_seconds() > 86400:
                continue
        else:
            if not (BACKFILL_START <= published <= BACKFILL_END):
                continue

        videos.append({
            "title": e.get("title"),
            "url": f"https://www.youtube.com/watch?v={e['id']}",
            "published_at": published
        })

    return videos


def transcribe_audio(video_url: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        ydl_opts = {
            "format": "bestaudio",
            "outtmpl": f"{tmp}/audio.%(ext)s",
            "quiet": True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        audio_path = next(
            os.path.join(tmp, f) for f in os.listdir(tmp)
        )

        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_path)

        return transcript.text


def analyze_with_gemini(text: str) -> dict:
    prompt = f"""
    Analizza il seguente contenuto in ottica geopolitica.
    Restituisci JSON con:
    - summary
    - countries_involved
    - risk_level (LOW/MEDIUM/HIGH)
    - keywords
    """

    response = gemini.generate_content(prompt + "\n\n" + text)
    return {"analysis": response.text}


def process_youtube():
    for name, url in YOUTUBE_CHANNELS.items():
        source_id = get_or_create_source(name, "youtube", url)
        videos = fetch_youtube_videos(url)

        for v in videos:
            if url_exists(v["url"]):
                continue

            log(f"Processing {v['title']}")

            transcript = transcribe_audio(v["url"])
            analysis = analyze_with_gemini(transcript)

            supabase.table("intelligence_feed").insert({
                "source_id": source_id,
                "title": v["title"],
                "url": v["url"],
                "published_at": v["published_at"].isoformat(),
                "content": transcript,
                "analysis": analysis,
                "raw_metadata": v
            }).execute()


# =========================
# INVESTING CALENDAR
# =========================
def process_calendar():
    source_id = get_or_create_source(
        "Investing.com Calendar",
        "calendar",
        "https://www.investing.com/economic-calendar/"
    )

    events = []

    if MODE == "LIVE":
        today = dt.date.today()
        events.append({
            "title": "US CPI Release",
            "date": today,
            "impact": "HIGH",
            "country": "USA"
        })
    else:
        for day in range(1, 26):
            events.append({
                "title": "EU Inflation Data",
                "date": dt.date(2026, 1, day),
                "impact": "MEDIUM",
                "country": "EU"
            })

    for e in events:
        url = f"investing://{e['title']}:{e['date']}"

        if url_exists(url):
            continue

        supabase.table("intelligence_feed").insert({
            "source_id": source_id,
            "title": e["title"],
            "url": url,
            "published_at": str(e["date"]),
            "content": json.dumps(e),
            "analysis": {"impact": e["impact"]},
            "raw_metadata": e
        }).execute()


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    log(f"Starting worker in MODE={MODE}")

    process_youtube()
    process_calendar()

    log("Done.")
