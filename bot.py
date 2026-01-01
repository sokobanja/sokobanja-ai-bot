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

# VAZNO: Headeri da imitiramo pravi pretrazivac
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def log(msg):
    print(f"[BOT] {msg}")

def get_latest_news():
    log("1. Trazim vesti na cekanju...")
    try:
        resp = requests.get(GET_LATEST_URL, headers=HEADERS, timeout=30)
        
        if resp.status_code != 200:
            log(f"CRITICAL: Server returned status {resp.status_code}")
            log(f"Response: {resp.text[:500]}")
            sys.exit(1) # Forsiraj gresku u Action-u

        try:
            data = resp.json()
        except Exception:
            log(f"CRITICAL: Ne mogu da parsiram JSON. Server je vratio:")
            log(resp.text[:500])
            sys.exit(1)
        
        if "id" not in data:
            if "message" in data:
                 log(f"Info: {data['message']}")
            else:
                 log(f"Info: Prazan odgovor ili nema 'id' polja. Response: {data}")
            return None
            
        return data
    except Exception as e:
        log(f"CRITICAL NETWORK ERROR: {e}")
        sys.exit(1)

def find_category_id(category_name="Vesti"):
    log(f"2. Trazim ID za kategoriju: '{category_name}'...")
    try:
        resp = requests.get(
            f"{WP_URL}/categories?search={category_name}", 
            auth=(WP_USER, WP_PASS),
            headers=HEADERS
        )
        if resp.status_code == 200:
            cats = resp.json()
            if cats and len(cats) > 0:
                return cats[0]['id']
    except:
        pass
    return 1

def upload_image_to_wp(image_url):
    if not image_url: return None
    log(f"3. Uploadujem sliku na WP: {image_url}")
    try:
        img_resp = requests.get(image_url, headers=HEADERS)
        if img_resp.status_code != 200:
            log(f"Greska pri downloadu slike: {img_resp.status_code}")
            return None
            
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
            return wp_resp.json().get('id')
        
        log(f"WP Media Upload Failed: {wp_resp.text}")
        return None
    except Exception as e:
        log(f"Media Exception: {e}")
        return None

def post_article(news_item):
    if not WP_USER or not WP_PASS:
        log("CRITICAL: Nedostaju WP tajne (Secrets)!")
        sys.exit(1)

    title = news_item.get('title', 'Sokobanja Info')
    content = news_item.get('content', '')
    news_id = news_item.get('id')
    image_url = news_item.get('image_url')

    log(f"Pripremam objavu: {title}")

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

    log("4. Saljem post na WP...")
    resp = requests.post(
        f"{WP_URL}/posts",
        json=post_data,
        auth=(WP_USER, WP_PASS),
        headers=HEADERS
    )

    if resp.status_code == 201:
        link = resp.json().get('link')
        log(f"✅ USPEH! Link: {link}")
        
        log("5. Brisem iz reda...")
        del_resp = requests.post(QUEUE_URL, json={"action": "delete", "id": news_id}, headers=HEADERS)
        if del_resp.status_code != 200:
             log(f"WARNING: Nisam uspeo da obrisem iz reda. Status: {del_resp.status_code}")
        
        return True
    else:
        log(f"❌ WP ERROR {resp.status_code}: {resp.text}")
        sys.exit(1) # Forsiraj gresku

if __name__ == "__main__":
    print("--- SOKOBANJA BOT v3.1 (STRICT DEBUG MODE) ---")
    news = get_latest_news()
    if news:
        post_article(news)
    else:
        print("--- NEMA VESTI ZA OBJAVU ---")
