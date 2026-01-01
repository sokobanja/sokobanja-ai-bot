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
# Pretvaramo se da smo Google Chrome da bi izbegli 403 Forbidden od sigurnosnih plugina
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# Za slike moramo prihvatiti sve
IMAGE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*"
}

def log(msg):
    print(f"[BOT] {msg}")

def verify_wp_connection():
    log("0. DIAGNOSTIKA: Proveravam vezu sa WordPress-om...")
    if not WP_USER or not WP_PASS:
        log("CRITICAL: Nedostaju Secrets (WP_USERNAME ili WP_APP_PASSWORD)!")
        return False
        
    try:
        # Pokusavamo da dohvatimo trenutnog korisnika da testiramo auth
        resp = requests.get(
            f"{WP_URL}/users/me", 
            auth=(WP_USER, WP_PASS),
            headers=HEADERS,
            timeout=10
        )
        
        if resp.status_code == 200:
            user_data = resp.json()
            log(f"   -> USPEH! Ulogovan kao: {user_data.get('name')} (ID: {user_data.get('id')})")
            return True
        elif resp.status_code == 401:
            log(f"   -> GRESKA 401 (Unauthorized): Lozinka je odbijena.")
            log("      SAVET: Proverite .htaccess 'RewriteRule .* - [E=HTTP_AUTHORIZATION...]' ili probajte novu Application Password.")
            return False
        elif resp.status_code == 403:
            log(f"   -> GRESKA 403 (Forbidden): Server blokira bota.")
            log("      SAVET: Security plugin (Wordfence) vas blokira. User-Agent je vec promenjen u Chrome.")
            return False
        else:
            log(f"   -> GRESKA {resp.status_code}: {resp.text[:100]}")
            return False
            
    except Exception as e:
        log(f"   -> CONNECTION ERROR: {e}")
        return False

def get_latest_news():
    log(f"1. Dohvatam vesti sa: {GET_LATEST_URL}")
    try:
        resp = requests.get(GET_LATEST_URL, headers=HEADERS, timeout=30)
        
        if resp.status_code != 200:
            log(f"CRITICAL: API Error {resp.status_code}")
            sys.exit(1)

        try:
            data = resp.json()
        except Exception:
            log(f"CRITICAL: API nije vratio JSON! Sadrzaj: {resp.text[:100]}")
            sys.exit(1)
        
        if "id" not in data:
            if "message" in data:
                 log(f"Info: {data['message']}")
            return None
            
        log(f"   -> Nasao vest ID: {data['id']} - {data.get('title')}")
        return data
    except Exception as e:
        log(f"CRITICAL NETWORK ERROR: {e}")
        sys.exit(1)

def find_category_id(category_name="Vesti"):
    log(f"2. Trazim WP kategoriju: '{category_name}'")
    try:
        resp = requests.get(
            f"{WP_URL}/categories?search={category_name}", 
            auth=(WP_USER, WP_PASS),
            headers=HEADERS
        )
        if resp.status_code == 200:
            cats = resp.json()
            if cats and len(cats) > 0:
                log(f"   -> Kategorija nadjena: {cats[0]['id']}")
                return cats[0]['id']
    except Exception:
        pass
    
    return 1 # Fallback ID

def upload_image_to_wp(image_url):
    if not image_url: return None
    log(f"3. Uploadujem sliku: {image_url}")
    try:
        # 1. Download (Koristimo IMAGE_HEADERS)
        img_resp = requests.get(image_url, headers=IMAGE_HEADERS)
        if img_resp.status_code != 200:
            log(f"   -> Download failed: {img_resp.status_code}")
            return None
            
        # 2. Upload to WP
        filename = f"ai_gen_{int(time.time())}.png"
        wp_headers = HEADERS.copy()
        wp_headers["Content-Type"] = "image/png"
        wp_headers["Content-Disposition"] = f"attachment; filename={filename}"
        
        wp_resp = requests.post(
            f"{WP_URL}/media",
            data=img_resp.content,
            headers=wp_headers,
            auth=(WP_USER, WP_PASS)
        )
        
        if wp_resp.status_code == 201:
            media_id = wp_resp.json().get('id')
            log(f"   -> Slika uploadovana! ID: {media_id}")
            return media_id
        
        log(f"   -> WP Upload Failed: {wp_resp.status_code}")
        return None
    except Exception as e:
        log(f"Media Error: {e}")
        return None

def post_article(news_item):
    if not verify_wp_connection():
        log("ABORTING: Cannot connect to WordPress API.")
        sys.exit(1)

    title = news_item.get('title', 'Info')
    content = news_item.get('content', '')
    news_id = news_item.get('id')
    image_url = news_item.get('image_url')

    cat_id = find_category_id("Vesti") 
    media_id = upload_image_to_wp(image_url)

    post_data = {
        'title': title,
        'content': content,
        'status': 'publish', 
        'categories': [cat_id] 
    }
    if media_id:
        post_data['featured_media'] = media_id

    log("4. Saljem post na WP API...")
    
    # Dodajemo pauzu da ne budemo sumnjivi
    time.sleep(2)
    
    resp = requests.post(
        f"{WP_URL}/posts",
        json=post_data,
        auth=(WP_USER, WP_PASS),
        headers=HEADERS
    )

    if resp.status_code == 201:
        link = resp.json().get('link')
        log(f"✅ USPEH! Objavljeno na: {link}")
        
        log(f"5. Brisem vest ID {news_id} iz reda...")
        del_payload = {"action": "delete", "id": int(news_id)}
        del_resp = requests.post(QUEUE_URL, json=del_payload, headers=HEADERS)
        
        if del_resp.status_code == 200:
             log(f"   -> Obrisano iz reda.")
        else:
             log(f"⚠️ GRESKA PRI BRISANJU IZ REDA: {del_resp.status_code}")
        
        return True
    else:
        log(f"❌ WP POST ERROR {resp.status_code}")
        log(f"   -> {resp.text[:500]}")
        sys.exit(1) 

if __name__ == "__main__":
    print("--- SOKOBANJA BOT v4.0 (STEALTH MODE) ---")
    news = get_latest_news()
    if news:
        post_article(news)
    else:
        print("--- NEMA VESTI ZA OBJAVU ---")
