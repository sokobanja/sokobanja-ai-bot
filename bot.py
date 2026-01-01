import os
import requests
import json
import time

# --- CONFIG ---
WP_USER = os.environ.get("WP_USERNAME")
WP_PASS = os.environ.get("WP_APP_PASSWORD")
WP_URL = "https://sokobanja.org.rs/wp-json/wp/v2"

# API endpoints vaseg React Portala
API_BASE = "https://portal.sokobanja.org.rs/api"
GET_LATEST_URL = f"{API_BASE}/get_latest.php"
QUEUE_URL = f"{API_BASE}/queue.php"

# VAZNO: Headeri da imitiramo pravi pretrazivac (da nas server ne blokira)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def get_latest_news():
    try:
        print("1. Trazim vesti na cekanju (u Redu/Queue)...")
        print(f"   -> URL: {GET_LATEST_URL}")
        
        # Dodati headers=HEADERS da izbegnemo 403 Forbidden
        resp = requests.get(GET_LATEST_URL, headers=HEADERS, timeout=30)
        
        # Prikazi sta server tacno vraca (debug)
        print(f"   -> SERVER STATUS: {resp.status_code}")
        print(f"   -> SERVER ODGOVOR (Prvih 500 karaktera):")
        print(resp.text[:500])
        print("------------------------------------------------")

        try:
            data = resp.json()
        except Exception as json_err:
            print(f"   -> GRESKA PRI PARSIRANJU JSON-a: {json_err}")
            print("   -> MOGUCI UZROK: Server je vratio HTML (Cloudflare zastita ili greska) umesto JSON-a.")
            return None
        
        if "id" not in data:
            print("VAZNO: API je vratio validan JSON, ali nema polja 'id'.")
            print(f"Sadrzaj odgovora: {data}")
            if "message" in data:
                 print(f"Poruka servera: {data['message']}")
            return None
            
        return data
    except Exception as e:
        print(f"Greska pri dohvatanju vesti (Network): {e}")
        return None

def find_category_id(category_name="Vesti"):
    print(f"2. Trazim ID za kategoriju: '{category_name}'...")
    try:
        resp = requests.get(
            f"{WP_URL}/categories?search={category_name}", 
            auth=(WP_USER, WP_PASS),
            headers=HEADERS
        )
        if resp.status_code == 200:
            cats = resp.json()
            if cats and len(cats) > 0:
                cat_id = cats[0]['id']
                print(f"   -> Pronadjena kategorija '{cats[0]['name']}' sa ID: {cat_id}")
                return cat_id
    except:
        pass
    print(f"   -> Kategorija nije nadjena ili greska. Koristim Default ID: 1")
    return 1

def upload_image_to_wp(image_url):
    if not image_url: return None
    try:
        print(f"3. Preuzimam sliku: {image_url}")
        img_resp = requests.get(image_url, headers=HEADERS)
        if img_resp.status_code != 200:
            print(f"   -> Greska pri downloadu slike: {img_resp.status_code}")
            return None
            
        filename = f"ai_gen_{int(time.time())}.png"
        wp_headers = HEADERS.copy()
        wp_headers["Content-Type"] = "image/png"
        wp_headers["Content-Disposition"] = f"attachment; filename={filename}"
        
        print("4. Saljem sliku na WordPress...")
        wp_resp = requests.post(
            f"{WP_URL}/media",
            data=img_resp.content,
            headers=wp_headers,
            auth=(WP_USER, WP_PASS)
        )
        
        if wp_resp.status_code == 201:
            media_id = wp_resp.json().get('id')
            print(f"   -> Slika uploadovana! ID: {media_id}")
            return media_id
        else:
            print(f"   -> WP Upload Error: {wp_resp.text}")
            return None
    except Exception as e:
        print(f"   -> Image Upload Exception: {e}")
        return None

def post_article(news_item):
    if not WP_USER or not WP_PASS:
        print("CRITICAL: WP_USERNAME ili WP_APP_PASSWORD nisu podeseni u GitHub Secrets!")
        return False

    title = news_item.get('title', 'Sokobanja Info')
    content = news_item.get('content', '')
    news_id = news_item.get('id')
    image_url = news_item.get('image_url')

    cat_id = find_category_id("Vesti") 
    media_id = None
    
    if image_url:
        media_id = upload_image_to_wp(image_url)

    post_data = {
        'title': title,
        'content': content,
        'status': 'publish', 
        'categories': [cat_id] 
    }
    if media_id:
        post_data['featured_media'] = media_id

    print("5. Objavljujem clanak na WP...")
    resp = requests.post(
        f"{WP_URL}/posts",
        json=post_data,
        auth=(WP_USER, WP_PASS),
        headers=HEADERS
    )

    if resp.status_code == 201:
        link = resp.json().get('link')
        print(f"✅ USPEH! Clanak objavljen: {link}")
        
        print("6. Brisem vest iz reda cekanja...")
        requests.post(QUEUE_URL, json={
            "action": "delete",
            "id": news_id
        }, headers=HEADERS)
        return True
    else:
        print(f"❌ WP Post Error: {resp.status_code} - {resp.text}")
        return False

if __name__ == "__main__":
    print("--- SOKOBANJA BOT v3.0 (BROWSER MODE) ---")
    news = get_latest_news()
    if news:
        print(f"Processing: {news.get('title')}")
        post_article(news)
    else:
        print("--- NEMA POSLA ILI GRESKA U KOMUNIKACIJI ---")
