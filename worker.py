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

# --- SETUP & CONFIG ---
print("\n🔧 [INIT] Avvio script e verifica variabili...")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or not GOOGLE_API_KEY:
    print("❌ ERRORE: Variabili d'ambiente mancanti!")
    exit(1)

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
    youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)
    print("✅ Client Supabase, Gemini e YouTube inizializzati.")
except Exception as e:
    print(f"❌ ERRORE Inizializzazione Client: {e}")
    traceback.print_exc()
    exit(1)

YOUTUBE_CHANNELS = ["@InvestireBiz"]

# --- FUNZIONE TRASCRITTO (INVIDIOUS + PROXY) ---
def get_transcript_via_proxy(video_id: str) -> str:
    print(f"\n   🕵️  [DEBUG] Avvio ricerca sottotitoli per: {video_id}")
    
    # Lista istanze
    instances = [
        "https://inv.tux.pizza",
        "https://invidious.drgns.space",
        "https://vid.puffyan.us",
        "https://inv.zzls.xyz",
        "https://yt.artemislena.eu"
    ]
    
    # CONFIGURAZIONE PROXY (WARP LOCALE)
    # Fondamentale: socks5h fa risolvere i DNS a Cloudflare
    proxies = {
        "http": "socks5h://127.0.0.1:40000",
        "https": "socks5h://127.0.0.1:40000"
    }
    print("   👉 [DEBUG] Proxy configurato su socks5h://127.0.0.1:40000")

    for instance in instances:
        try:
            print(f"   👉 [DEBUG] Tento istanza: {instance} ...")
            url_list = f"{instance}/api/v1/captions/{video_id}"
            
            # Request 1: Lista Sottotitoli
            t_start = time.time()
            res = requests.get(url_list, proxies=proxies, timeout=10)
            elapsed = time.time() - t_start
            
            print(f"      [HTTP] Status: {res.status_code} | Tempo: {elapsed:.2f}s")
            
            if res.status_code != 200:
                print(f"      ⚠️ Istanza non valida o errore API (Code: {res.status_code})")
                continue
            
            try:
                captions = res.json()
            except:
                print("      ⚠️ Errore parsing JSON risposta.")
                continue

            if not isinstance(captions, list):
                print("      ⚠️ Formato JSON imprevisto (non è una lista).")
                continue
            
            print(f"      ✅ Trovati {len(captions)} sottotitoli disponibili.")

            # Selezione Lingua
            target = None
            # 1. Cerca Italiano
            for c in captions:
                if c.get('language') == 'Italian' or c.get('code') == 'it':
                    target = c
                    print("      👉 Trovato Italiano nativo.")
                    break
            
            # 2. Cerca Inglese
            if not target:
                for c in captions:
                    if 'en' in c.get('code', ''): 
                        target = c
                        print("      👉 Trovato Inglese (fallback).")
                        break
            
            # 3. Primo disponibile
            if not target and len(captions) > 0:
                target = captions[0]
                print("      👉 Preso il primo disponibile (fallback estremo).")

            if target:
                full_url = f"{instance}{target['url']}"
                print(f"      ⬇️  Scarico testo da: {full_url}")
                
                # Request 2: Testo
                text_res = requests.get(full_url, proxies=proxies, timeout=10)
                
                if text_res.status_code == 200:
                    raw_text = text_res.text
                    clean_text = ""
                    
                    # Parsing JSON vs VTT
                    if raw_text.strip().startswith('{') or raw_text.strip().startswith('['):
                        print("      [PARSING] Rilevato formato JSON.")
                        try:
                            data = json.loads(raw_text)
                            clean_text = " ".join([x.get('content', '') for x in data if 'content' in x])
                        except: pass
                    else:
                        print("      [PARSING] Rilevato formato VTT/Text.")
                        lines = [
                            l.strip() for l in raw_text.splitlines() 
                            if "-->" not in l and l.strip() and not l.startswith(("WEBVTT", "NOTE", "Kind:", "Language:"))
                        ]
                        # Deduplica
                        clean_lines = []
                        for l in lines:
                            if not clean_lines or clean_lines[-1] != l:
                                clean_lines.append(l)
                        clean_text = " ".join(clean_lines)

                    if len(clean_text) > 50:
                        print(f"   ✅ [SUCCESS] Testo estratto: {len(clean_text)} caratteri.")
                        return clean_text
                    else:
                        print("      ⚠️ Testo estratto troppo breve o vuoto.")
                else:
                    print(f"      ❌ Errore download file testo (Status: {text_res.status_code})")

        except requests.exceptions.ProxyError:
            print("      ❌ Errore Proxy: Impossibile connettersi a WARP.")
        except requests.exceptions.ConnectTimeout:
            print("      ❌ Timeout connessione.")
        except Exception as e:
            print(f"      ❌ Errore generico istanza: {e}")
            
    print("   ❌ [FAIL] Sottotitoli non trovati su nessuna istanza.")
    return ""

def analyze_gemini(text: str) -> dict:
    if not text or len(text) < 50: 
        print("   🧠 [DEBUG] Testo insufficiente per Gemini.")
        return {"summary": "N/A"}
    
    print(f"   🧠 [DEBUG] Invio {len(text)} caratteri a Gemini...")
    try:
        res = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f'Analizza JSON: {{ "summary": "Riassunto dettagliato", "risk_level": "LOW", "countries_involved": [], "key_takeaway": "Punto chiave" }}\nTEXT:{text[:25000]}',
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        parsed = json.loads(res.text.replace("```json","").replace("```","").strip())
        print("   ✅ [DEBUG] Risposta Gemini ricevuta e parsata.")
        return parsed
    except Exception as e: 
        print(f"   ❌ [DEBUG] Errore Gemini: {e}")
        return {}

def get_source_id(name, ch_id):
    print(f"   🔎 [DB] Cerco source: {name}")
    try:
        res = supabase.table("sources").select("id").eq("name", name).execute()
        if res.data: 
            sid = str(res.data[0]['id'])
            print(f"      ✅ Trovata ID: {sid}")
            return sid
        
        print("      ➕ Creo nuova source...")
        new = supabase.table("sources").insert({"name": name, "type": "yt", "base_url": ch_id}).execute()
        if new.data:
            sid = str(new.data[0]['id'])
            print(f"      ✅ Creata ID: {sid}")
            return sid
    except Exception as e:
        print(f"   ❌ [DB ERROR] get_source_id: {e}")
    return None

def get_channel_videos(handle):
    print(f"📡 [DEBUG] Scansiono API YouTube per: {handle}")
    videos = []
    try:
        res = youtube_service.channels().list(part="contentDetails,snippet", forHandle=handle).execute()
        if not res.get('items'): 
            print("   ⚠️ Nessun canale trovato.")
            return []
        
        upl = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        ch_title = res['items'][0]['snippet']['title']
        ch_id = res['items'][0]['id']
        
        pl = youtube_service.playlistItems().list(part="snippet", playlistId=upl, maxResults=5).execute()
        for i in pl.get('items', []):
            vid = i['snippet']['resourceId']['videoId']
            print(f"   👉 Video trovato: {vid} - {i['snippet']['title'][:30]}...")
            videos.append({
                "id": vid,
                "title": i['snippet']['title'],
                "desc": i['snippet']['description'],
                "date": i['snippet']['publishedAt'],
                "url": f"https://www.youtube.com/watch?v={vid}",
                "ch_title": ch_title, "ch_id": ch_id
            })
    except Exception as e:
        print(f"   ❌ [API ERROR] YouTube Data: {e}")
    return videos

# --- MAIN ---
if __name__ == "__main__":
    print("\n--- 🚀 START WORKER (DEBUG MODE) ---")
    
    for handle in YOUTUBE_CHANNELS:
        videos = get_channel_videos(handle)
        
        for v in videos:
            print(f"\n🔄 [PROCESSING] {v['title'][:50]}...")
            
            # Check esistenza
            try:
                exists = supabase.table("intelligence_feed").select("id").eq("url", v['url']).execute()
                if exists.data:
                    print("   ⏭️  Già presente nel DB. Salto.")
                    continue
            except Exception as e:
                print(f"   ⚠️ Errore controllo esistenza DB: {e}")

            # 1. RECUPERO TESTO
            text = get_transcript_via_proxy(v['id'])
            method = "Invidious+Proxy"
            
            if not text:
                print("   ⚠️ [FALLBACK] Sottotitoli assenti. Uso descrizione.")
                text = f"{v['title']}\n{v['desc']}"
                method = "Descrizione"
            
            # 2. ANALISI
            analysis = analyze_gemini(text)
            
            # 3. SALVATAGGIO
            sid = get_source_id(v['ch_title'], v['ch_id'])
            
            if sid:
                print("   💾 [DB] Tentativo salvataggio...")
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
                    res = supabase.table("intelligence_feed").insert(data).execute()
                    
                    if res.data:
                        print(f"   ✅ [SUCCESS] Salvato con ID: {res.data[0]['id']}")
                    else:
                        print("   ❓ [WARNING] Insert eseguito ma nessun dato ritornato (RLS attivo?).")
                        
                except Exception as e:
                    print(f"   ❌ [DB INSERT ERROR] : {e}")
                    traceback.print_exc()
            else:
                print("   ❌ [ERROR] Source ID mancante, impossibile salvare.")
            
            time.sleep(1) # Un po' di respiro
            
    print("\n--- ✅ WORKER FINISHED ---")