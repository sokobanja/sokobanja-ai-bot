import os
import requests
import json
import time
import sys

# --- CONFIG ---
WP_USER = os.environ.get("WP_USERNAME")
WP_PASS = os.environ.get("WP_APP_PASSWORD")
WP_URL = "https://sokobanja.org.rs/wp-json/wp/v2"

# API endpoints vaseg React Portala
API_BASE = "https://portal.sokobanja.org.rs/api"
GET_LATEST_URL = f"{API_BASE}/get_latest.php"
QUEUE_URL = f"{API_BASE}/queue.php"

# --- STEALTH HEADERS ---
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

def log(msg):
    print(f"[BOT] {msg}")
    sys.stdout.flush()

def check_wp_auth():
    log("🔧 0. DIAGNOSTICS: Checking WordPress Connection...")
    
    if not WP_USER or not WP_PASS:
        log("❌ CRITICAL: Secrets (WP_USERNAME ili WP_APP_PASSWORD) nedostaju u GitHub Settings!")
        return False
        
    # Maskirana lozinka za debug
    pass_len = len(WP_PASS) if WP_PASS else 0
    masked = "*" * pass_len
    log(f"   User: {WP_USER}")
    log(f"   Pass Length: {pass_len} chars")

    url = f"{WP_URL}/users/me"
    try:
        resp = requests.get(url, auth=(WP_USER, WP_PASS), headers=COMMON_HEADERS, timeout=15)
        
        if resp.status_code == 200:
            user = resp.json()
            log(f"✅ AUTH SUCCESS! Ulogovan kao: {user.get('name')}")
            return True
        elif resp.status_code == 401:
            log(f"⛔ AUTH FAILED (401). Lozinka je stigla do servera ali je odbijena ili obrisana.")
            log("   AKCIJA: Proverite da li ste ubacili 'Restore Authorization Header' kod u WPCode plugin (Tab 8).")
            return False
        elif resp.status_code == 403:
            log(f"⛔ FORBIDDEN (403). Wordfence ili firewall blokira.")
            return False
        else:
            log(f"⚠️ HTTP ERROR {resp.status_code}: {resp.text[:100]}")
            return False
    except Exception as e:
        log(f"❌ CONNECTION ERROR: {str(e)}")
        return False

def get_latest_news():
    log(f"📥 1. Dohvatam vesti sa: {GET_LATEST_URL}")
    try:
        resp = requests.get(GET_LATEST_URL, headers=COMMON_HEADERS, timeout=30)
        
        if resp.status_code != 200:
            log(f"❌ API Error {resp.status_code}")
            return None

        text = resp.text.strip()
        if text.startswith('\ufeff'): text = text[1:]
            
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            log(f"❌ JSON PARSE ERROR.")
            return None
        
        if "id" not in data:
            if "message" in data: log(f"ℹ️ Info: {data['message']}")
            return None
            
        log(f"   -> Nasao vest ID: {data['id']} - {data.get('title')}")
        return data
    except Exception as e:
        log(f"❌ FETCH ERROR: {e}")
        return None

def find_category_id(category_name="Vesti"):
    log(f"🔎 2. Trazim ID Kategorije '{category_name}'...")
    try:
        resp = requests.get(
            f"{WP_URL}/categories?search={category_name}", 
            auth=(WP_USER, WP_PASS),
            headers=COMMON_HEADERS,
            timeout=10
        )
        if resp.status_code == 200:
            cats = resp.json()
            if cats and len(cats) > 0:
                return cats[0]['id']
    except Exception:
        pass
    return 1 

def upload_image(image_url):
    if not image_url: return None
    log(f"🖼️ 3. Obradjujem sliku: {image_url}")
    try:
        img_resp = requests.get(image_url, headers=COMMON_HEADERS, timeout=30)
        if img_resp.status_code != 200: return None
            
        filename = f"ai_news_{int(time.time())}.png"
        media_headers = COMMON_HEADERS.copy()
        media_headers["Content-Type"] = "image/png"
        media_headers["Content-Disposition"] = f"attachment; filename={filename}"
        
        wp_resp = requests.post(
            f"{WP_URL}/media",
            data=img_resp.content,
            headers=media_headers,
            auth=(WP_USER, WP_PASS),
            timeout=30
        )
        
        if wp_resp.status_code == 201:
            return wp_resp.json().get('id')
        return None
    except Exception:
        return None

def post_article(news_item):
    if not check_wp_auth():
        log("🛑 PREKIDAM: Autentifikacija nije prosla.")
        sys.exit(1)

    title = news_item.get('title', 'Info')
    content = news_item.get('content', '')
    news_id = news_item.get('id')
    image_url = news_item.get('image_url')

    cat_id = find_category_id("Vesti") 
    media_id = upload_image(image_url)

    post_data = {
        'title': title,
        'content': content,
        'status': 'publish', 
        'categories': [cat_id] 
    }
    if media_id:
        post_data['featured_media'] = media_id

    log("🚀 4. Objavljujem clanak na WordPress...")
    post_headers = COMMON_HEADERS.copy()
    post_headers["Content-Type"] = "application/json"

    try:
        resp = requests.post(
            f"{WP_URL}/posts",
            json=post_data,
            auth=(WP_USER, WP_PASS),
            headers=post_headers,
            timeout=30
        )

        if resp.status_code == 201:
            link = resp.json().get('link')
            log(f"✅ USPEH! Objavljeno na: {link}")
            
            log(f"🗑️ 5. Brisem vest {news_id} iz reda...")
            try:
                requests.post(QUEUE_URL, json={"action": "delete", "id": int(news_id)}, headers=post_headers, timeout=10)
            except: pass
            return True
        else:
            log(f"❌ PUBLISH FAILED: {resp.status_code}")
            sys.exit(1)

    except Exception as e:
        log(f"❌ POST EXCEPTION: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("--- 🤖 SOKOBANJA BOT v4.1 (Header Restore Check) ---")
    news = get_latest_news()
    if news:
        post_article(news)
    else:
        print("--- 💤 NEMA NOVIH VESTI ---")
