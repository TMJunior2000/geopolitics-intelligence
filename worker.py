import os
import json
import time
import requests
import traceback
from datetime import datetime

from googleapiclient.discovery import build
from google import genai
from google.genai import types
from supabase import create_client, Client

# --- CONFIG ---
print("🔧 INIT...")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or not GOOGLE_API_KEY:
    raise ValueError("❌ Variabili mancanti.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)

YOUTUBE_CHANNELS = ["@InvestireBiz"]

# --- IL CUORE DELLA SOLUZIONE ---
def get_transcript_via_proxy(video_id: str) -> str:
    print(f"   🕵️  Scarico sottotitoli per {video_id} (Invidious + Proxy WARP)...")
    
    # Lista di istanze Invidious affidabili
    instances = [
        "https://inv.tux.pizza",
        "https://invidious.drgns.space",
        "https://vid.puffyan.us",
        "https://inv.zzls.xyz",
        "https://yt.artemislena.eu"
    ]
    
    # CONFIGURAZIONE PROXY: Fondamentale!
    # Tutto il traffico verso Invidious passa da WARP (IP Cloudflare)
    proxies = {
        "http": "socks5h://127.0.0.1:40000",
        "https": "socks5h://127.0.0.1:40000"
    }

    for instance in instances:
        try:
            # 1. Chiediamo la lista dei sottotitoli all'istanza
            url_list = f"{instance}/api/v1/captions/{video_id}"
            
            # Timeout breve per scorrere veloce le istanze lente
            res = requests.get(url_list, proxies=proxies, timeout=10)
            
            if res.status_code != 200: continue
            
            captions = res.json()
            if not isinstance(captions, list): continue

            # 2. Cerchiamo Italiano > Inglese > Auto-generato
            target = None
            # Cerca Italiano
            for c in captions:
                if c.get('language') == 'Italian' or c.get('code') == 'it':
                    target = c; break
            
            # Se no, cerca Inglese
            if not target:
                for c in captions:
                    if 'en' in c.get('code', ''): target = c; break
            
            # Se no, prendi il primo (spesso è l'auto-generato locale)
            if not target: 
                 if len(captions) > 0: target = captions[0]

            if target:
                # 3. Scarichiamo il testo vero e proprio
                full_url = f"{instance}{target['url']}"
                text_res = requests.get(full_url, proxies=proxies, timeout=10)
                
                if text_res.status_code == 200:
                    # Pulizia brutale del formato VTT/JSON
                    raw_text = text_res.text
                    
                    # Se è JSON (alcune API tornano JSON)
                    if raw_text.startswith('{') or raw_text.startswith('['):
                        try:
                            data = json.loads(raw_text)
                            text_content = " ".join([x.get('content', '') for x in data if 'content' in x])
                            if text_content:
                                print(f"   ✅ Trovati su {instance} (JSON)!")
                                return text_content
                        except: pass

                    # Se è VTT (testo con timestamp)
                    lines = [
                        l.strip() for l in raw_text.splitlines() 
                        if "-->" not in l and l.strip() and not l.startswith(("WEBVTT", "NOTE", "Kind:", "Language:"))
                    ]
                    # Rimuove duplicati consecutivi
                    clean_lines = []
                    for l in lines:
                        if not clean_lines or clean_lines[-1] != l:
                            clean_lines.append(l)
                    
                    final_text = " ".join(clean_lines)
                    if len(final_text) > 50:
                        print(f"   ✅ Trovati su {instance} (VTT)!")
                        return final_text

        except Exception as e:
            # print(f"      Errore su {instance}: {e}") # Decommenta per debug profondo
            continue
            
    print("   ❌ Sottotitoli non trovati su nessuna istanza.")
    return ""

def analyze_gemini(text: str) -> dict:
    if not text or len(text) < 50: return {"summary": "N/A"}
    print("   🧠 Analisi Gemini...")
    try:
        res = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f'Analizza JSON: {{ "summary": "...", "risk_level": "LOW", "countries_involved": [] }}\nTEXT:{text[:20000]}',
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(res.text.replace("```json","").replace("```","").strip())
    except Exception as e: 
        print(f"   ❌ Errore Gemini: {e}")
        return {}

def get_source_id(name, ch_id):
    try:
        res = supabase.table("sources").select("id").eq("name", name).execute()
        if res.data: return str(res.data[0]['id'])
        new = supabase.table("sources").insert({"name": name, "type": "yt", "base_url": ch_id}).execute()
        return str(new.data[0]['id']) if new.data else None
    except: return None

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
    print("--- 🚀 START WORKER (PROXY -> INVIDIOUS) ---")
    for handle in YOUTUBE_CHANNELS:
        for v in get_channel_videos(handle):
            # Controllo esistenza (riattivato)
            try:
                exists = supabase.table("intelligence_feed").select("id").eq("url", v['url']).execute()
                if exists.data: continue
            except: pass
            
            print(f"🔄 Processing: {v['title'][:40]}...")
            
            # 1. TENTA INVIDIOUS VIA PROXY
            text = get_transcript_via_proxy(v['id'])
            method = "Invidious+Proxy"
            
            # 2. FALLBACK
            if not text:
                print("   ⚠️ Fallback Descrizione.")
                text = f"{v['title']}\n{v['desc']}"
                method = "Descrizione"
            
            # 3. ANALISI & SALVATAGGIO
            analysis = analyze_gemini(text)
            sid = get_source_id(v['ch_title'], v['ch_id'])
            
            if sid:
                try:
                    data = {
                        "source_id": sid, 
                        "title": v['title'], 
                        "url": v['url'],
                        "published_at": v['date'], 
                        "content": text, 
                        "analysis": analysis,
                        "raw_metadata": {"vid": v['id'], "method": method}
                    }
                    supabase.table("intelligence_feed").insert(data).execute()
                    print(f"   💾 Salvato.")
                except Exception as e:
                    print(f"   ❌ Errore DB: {e}")
            
            time.sleep(1)
    print("--- END ---")