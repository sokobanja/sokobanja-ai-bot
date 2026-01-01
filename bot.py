import os
import requests
import json
import time
import sys
import base64

# --- CONFIG ---
WP_USER = os.environ.get("WP_USERNAME")
WP_PASS = os.environ.get("WP_APP_PASSWORD")
WP_URL = "https://sokobanja.org.rs/wp-json/wp/v2"
API_BASE = "https://portal.sokobanja.org.rs/api"

# --- HEADERS ---
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

# Globalna promenljiva za Auth Header (moze se promeniti tokom rada)
AUTH_HEADERS = {} 

def log(msg):
    print(f"[BOT] {msg}")
    sys.stdout.flush()

def setup_auth():
    """Pokusava da nadje pravu auth metodu (Standard ili Bypass)"""
    global AUTH_HEADERS
    
    if not WP_USER or not WP_PASS:
        log("❌ CRITICAL: Nema WP credencijala!")
        return False
        
    # Priprema Basic Auth stringa
    token = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    auth_val = f"Basic {token}"
    
    # 1. TEST STANDARDNOG AUTHA
    log("🔑 Testiram Standardni Auth...")
    try:
        test_headers = COMMON_HEADERS.copy()
        test_headers["Authorization"] = auth_val
        
        resp = requests.get(f"{WP_URL}/users/me", headers=test_headers, timeout=10)
        
        if resp.status_code == 200:
            log("✅ Standardni Auth RADI!")
            AUTH_HEADERS = test_headers
            return True
        else:
            log(f"⚠️ Standardni Auth odbijen ({resp.status_code}).")
    except Exception as e:
        log(f"⚠️ Greska pri standardnom authu: {e}")

    # 2. TEST BYPASS AUTHA (X-WP-Auth)
    log("🛡️ Pokrecem 'Silver Bullet' Bypass (X-WP-Auth)...")
    try:
        bypass_headers = COMMON_HEADERS.copy()
        # Saljemo lozinku u nasem custom headeru koga server nece obrisati
        bypass_headers["X-WP-Auth"] = auth_val 
        
        resp = requests.get(f"{WP_URL}/users/me", headers=bypass_headers, timeout=10)
        
        if resp.status_code == 200:
            log("✅ BYPASS AUTH RADI! Koristimo tajni kanal.")
            AUTH_HEADERS = bypass_headers
            return True
        else:
            log(f"❌ I Bypass Auth je odbijen ({resp.status_code}).")
            log(f"   Response: {resp.text[:100]}")
            return False
            
    except Exception as e:
        log(f"❌ Greska pri bypass authu: {e}")
        return False

def get_latest_news():
    log(f"📥 Dohvatam vesti iz reda: {API_BASE}/get_latest.php")
    try:
        resp = requests.get(f"{API_BASE}/get_latest.php", headers=COMMON_HEADERS, timeout=30)
        if resp.status_code != 200: return None
        
        try:
            data = resp.json()
        except: return None
            
        if "id" in data:
            log(f"   -> Nasao vest ID: {data['id']}")
            return data
        return None
    except: return None

def upload_image(image_url):
    if not image_url: return None
    log(f"🖼️ Uploadujem sliku...")
    try:
        img_resp = requests.get(image_url, headers=COMMON_HEADERS, timeout=30)
        if img_resp.status_code != 200: return None
        
        filename = f"ai_news_{int(time.time())}.png"
        
        # Kombinujemo Auth headers sa Image headers
        headers = {**AUTH_HEADERS, **COMMON_HEADERS}
        headers["Content-Type"] = "image/png"
        headers["Content-Disposition"] = f"attachment; filename={filename}"
        
        resp = requests.post(f"{WP_URL}/media", data=img_resp.content, headers=headers, timeout=30)
        
        if resp.status_code == 201:
            return resp.json().get('id')
        return None
    except: return None

def post_article(news):
    title = news.get('title')
    
    # 1. Upload slike
    media_id = upload_image(news.get('image_url'))
    
    # 2. Kreiranje posta
    log("🚀 Objavljujem clanak...")
    post_data = {
        'title': title,
        'content': news.get('content'),
        'status': 'publish',
        'categories': [1] # Default ID
    }
    if media_id: post_data['featured_media'] = media_id
    
    headers = {**AUTH_HEADERS, **COMMON_HEADERS}
    
    resp = requests.post(f"{WP_URL}/posts", json=post_data, headers=headers)
    
    if resp.status_code == 201:
        log("✅ USPEH! Vest objavljena.")
        # Brisanje iz reda
        try:
            requests.post(f"{API_BASE}/queue.php", json={"action":"delete", "id":int(news['id'])}, headers=COMMON_HEADERS)
            log("🗑️ Obrisano iz reda.")
        except: pass
        return True
    else:
        log(f"❌ Greska pri objavi: {resp.status_code}")
        log(resp.text[:200])
        return False

if __name__ == "__main__":
    print("--- 🤖 SOKOBANJA BOT v4.2 (Silver Bullet) ---")
    
    # 1. Prvo auth check
    if not setup_auth():
        print("❌ Ne mogu da se ulogujem. Proverite WPCode snippet.")
        sys.exit(1)
        
    # 2. Onda posao
    news = get_latest_news()
    if news:
        post_article(news)
    else:
        print("--- 💤 Nema vesti ---")
