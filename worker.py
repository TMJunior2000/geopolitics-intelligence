import os
import json
import time
import glob
import re
from typing import cast, List, Dict, Any

import yt_dlp
from googleapiclient.discovery import build
from google import genai
from google.genai import types
from supabase import create_client, Client

# --- CONFIGURAZIONE ---
print("\n🔧 [INIT] Avvio script (COOKIES AUTH MODE)...")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
YOUTUBE_COOKIES = os.getenv("YOUTUBE_COOKIES") # <--- IL PASSPARTOUT

if not SUPABASE_URL or not SUPABASE_KEY or not GOOGLE_API_KEY:
    print("❌ ERRORE: Variabili mancanti.")
    exit(1)

if not YOUTUBE_COOKIES:
    print("⚠️ ATTENZIONE: Secret 'YOUTUBE_COOKIES' non trovato. Probabile fallimento.")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
    youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)
    print("✅ Client inizializzati.")
except Exception as e:
    print(f"❌ ERRORE INIT: {e}")
    exit(1)

YOUTUBE_CHANNELS = ["@InvestireBiz"]

# --- GESTIONE COOKIE ---
def create_cookie_file():
    """Crea il file cookie temporaneo dal Secret"""
    if not YOUTUBE_COOKIES: return None
    path = "/tmp/cookies.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(YOUTUBE_COOKIES)
    print("   🍪 File cookie creato in /tmp/cookies.txt")
    return path

# --- PULIZIA TESTO ---
def clean_vtt_text(vtt_content: str) -> str:
    lines = vtt_content.splitlines()
    text_lines = []
    seen = set()
    for line in lines:
        line = line.strip()
        if (not line or line.startswith("WEBVTT") or "-->" in line or 
            line.startswith(("Kind:", "Language:")) or re.match(r'^\d+$', line)):
            continue
        line = re.sub(r'<[^>]+>', '', line).replace("&nbsp;", " ")
        if line and line not in seen:
            text_lines.append(line)
            seen.add(line)
    return " ".join(text_lines)

# --- SCARICAMENTO (yt-dlp + COOKIES + PROXY) ---
def get_transcript_ytdlp(video_url: str, cookie_path: str) -> str:
    print(f"   🔐 [YT-DLP] Scarico con autenticazione: {video_url}...")
    
    ydl_opts = {
        'proxy': 'socks5://127.0.0.1:40000', # Proxy WARP (manteniamolo per sicurezza)
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['it', 'en'],
        'outtmpl': '/tmp/%(id)s',
        'quiet': True,
        'no_warnings': True,
    }

    # SE ABBIAMO I COOKIE, USIAMOLI!
    if cookie_path:
        ydl_opts['cookiefile'] = cookie_path
    else:
        # Fallback disperato su Android se mancano i cookie
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android']}}

    try:
        # Pulisce vecchi file
        for f in glob.glob("/tmp/*.vtt"): os.remove(f)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        files = glob.glob("/tmp/*.vtt")
        if not files:
            print("      ⚠️ Nessun file sottotitoli trovato.")
            return ""
        
        target_file = files[0]
        for f in files:
            if ".it." in f: target_file = f; break
        
        print(f"      ✅ File scaricato: {os.path.basename(target_file)}")
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        clean_text = clean_vtt_text(content)
        
        if len(clean_text) > 50:
            print(f"      ✅ Testo estratto: {len(clean_text)} chars.")
            return clean_text
        else:
            return ""

    except Exception as e:
        print(f"      ❌ Errore yt-dlp: {e}")
        return ""

# --- ANALISI GEMINI ---
def analyze_gemini(text: str) -> dict:
    if not text or len(text) < 50: return {"summary": "N/A"}
    print(f"   🧠 [AI] Invio {len(text)} chars...")
    for attempt in range(3):
        try:
            res = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f'Analizza JSON: {{ "summary": "Riassunto", "risk_level": "LOW", "countries_involved": [], "key_takeaway": "Main" }}\nTEXT:{text[:28000]}',
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(res.text.replace("```json","").replace("```","").strip())
        except Exception as e:
            if "429" in str(e): 
                print("      ⚠️ Quota AI 429. Wait 35s...")
                time.sleep(35)
            else: return {}
    return {}

# --- DB ---
def get_source_id(name, ch_id):
    try:
        res = supabase.table("sources").select("id").eq("name", name).execute()
        data = cast(List[Dict[str, Any]], res.data)
        if data: return str(data[0]['id'])
        
        new = supabase.table("sources").insert({
            "name": name, "type": "youtube", "base_url": ch_id
        }).execute()
        new_data = cast(List[Dict[str, Any]], new.data)
        if new_data: return str(new_data[0]['id'])
    except: pass
    return None

def get_channel_videos(handle):
    videos = []
    try:
        res = youtube_service.channels().list(part="contentDetails,snippet", forHandle=handle).execute()
        if not res.get('items'): return []
        upl = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        ch_title = res['items'][0]['snippet']['title']
        ch_id = res['items'][0]['id']
        pl = youtube_service.playlistItems().list(part="snippet", playlistId=upl, maxResults=5).execute()
        for i in pl.get('items', []):
            videos.append({
                "id": i['snippet']['resourceId']['videoId'],
                "title": i['snippet']['title'],
                "desc": i['snippet']['description'],
                "date": i['snippet']['publishedAt'],
                "url": f"https://www.youtube.com/watch?v={i['snippet']['resourceId']['videoId']}",
                "ch_title": ch_title, "ch_id": ch_id
            })
    except: pass
    return videos

# --- MAIN ---
if __name__ == "__main__":
    print("\n--- 🚀 START WORKER (COOKIES ENABLED) ---")
    
    # 1. Crea il file cookie
    cookie_path = create_cookie_file()
    
    for handle in YOUTUBE_CHANNELS:
        videos = get_channel_videos(handle)
        
        for v in videos:
            print(f"\n🔄 {v['title'][:40]}...")
            
            try:
                if supabase.table("intelligence_feed").select("id").eq("url", v['url']).execute().data:
                    print("   ⏭️  Già presente."); continue
            except: pass

            # 2. Scarica usando il file cookie
            text = get_transcript_ytdlp(v['url'], cookie_path)
            method = "yt-dlp+Cookies"
            
            if not text:
                print("   ⚠️ Fallback Descrizione.")
                text = f"{v['title']}\n{v['desc']}"
                method = "Descrizione"
            else:
                print("   🔥 SUBS TROVATI!")

            # 3. Analisi e Save
            analysis = analyze_gemini(text)
            sid = get_source_id(v['ch_title'], v['ch_id'])
            
            if sid:
                try:
                    supabase.table("intelligence_feed").insert({
                        "source_id": sid, "title": v['title'], "url": v['url'],
                        "published_at": v['date'], "content": text, "analysis": analysis,
                        "raw_metadata": {"vid": v['id'], "method": method}
                    }).execute()
                    print(f"   💾 SALVATO")
                except Exception as e:
                    if "duplicate" not in str(e): print(f"   ❌ DB: {e}")
            
            print("   💤 5s...")
            time.sleep(5)
            
    # 4. Rimuovi il file cookie per sicurezza
    if cookie_path and os.path.exists(cookie_path):
        os.remove(cookie_path)
        print("   🧹 Cookie file rimosso.")

    print("\n--- ✅ FINITO ---")