import os
import requests
import json
import time

# --- CONFIG ---
# Ovi podaci se citaju iz GitHub Secrets
WP_USER = os.environ.get("WP_USERNAME")
WP_PASS = os.environ.get("WP_APP_PASSWORD")
WP_URL = "https://sokobanja.org.rs/wp-json/wp/v2"

# API endpoints vaseg React Portala
API_BASE = "https://portal.sokobanja.org.rs/api"
GET_LATEST_URL = f"{API_BASE}/get_latest.php"
QUEUE_URL = f"{API_BASE}/queue.php"

def get_latest_news():
    try:
        print("1. Trazim vesti na cekanju...")
        resp = requests.get(GET_LATEST_URL, timeout=30)
        try:
            data = resp.json()
        except:
            print(f"Greska u JSON formatu: {resp.text[:100]}")
            return None
        
        if "id" not in data:
            print("Nema novih vesti na cekanju.")
            return None
            
        return data
    except Exception as e:
        print(f"Greska pri dohvatanju vesti: {e}")
        return None

def upload_image_to_wp(image_url):
    if not image_url: return None
    
    try:
        print(f"2. Preuzimam sliku: {image_url}")
        img_resp = requests.get(image_url)
        if img_resp.status_code != 200:
            print("Neuspesno preuzimanje slike.")
            return None
            
        filename = f"ai_gen_{int(time.time())}.png"
        headers = {
            "Content-Type": "image/png",
            "Content-Disposition": f"attachment; filename={filename}"
        }
        
        print("3. Saljem sliku na WordPress...")
        wp_resp = requests.post(
            f"{WP_URL}/media",
            data=img_resp.content,
            headers=headers,
            auth=(WP_USER, WP_PASS)
        )
        
        if wp_resp.status_code == 201:
            media_id = wp_resp.json().get('id')
            print(f"Slika uploadovana! ID: {media_id}")
            return media_id
        else:
            print(f"WP Upload Error: {wp_resp.text}")
            return None
    except Exception as e:
        print(f"Image Upload Exception: {e}")
        return None

def post_article(news_item):
    if not WP_USER or not WP_PASS:
        print("CRITICAL: WP_USERNAME ili WP_APP_PASSWORD nisu podeseni u GitHub Secrets!")
        return False

    title = news_item.get('title', 'Sokobanja Info')
    content = news_item.get('content', '')
    news_id = news_item.get('id')
    image_url = news_item.get('image_url')

    # 1. Upload slike (ako postoji)
    media_id = None
    if image_url:
        media_id = upload_image_to_wp(image_url)

    # 2. Kreiranje posta
    post_data = {
        'title': title,
        'content': content,
        'status': 'publish', 
        'categories': [1] # ID kategorije 'Vesti', promenite po potrebi
    }
    
    if media_id:
        post_data['featured_media'] = media_id

    print("4. Objavljujem clanak na WP...")
    resp = requests.post(
        f"{WP_URL}/posts",
        json=post_data,
        auth=(WP_USER, WP_PASS)
    )

    if resp.status_code == 201:
        link = resp.json().get('link')
        print(f"✅ USPEH! Clanak objavljen: {link}")
        
        # 3. Mark as Done
        print("5. Azuriram status u redu cekanja...")
        status_resp = requests.post(QUEUE_URL, json={
            "action": "update_status",
            "id": news_id,
            "status": "published"
        })
        print(f"Status update: {status_resp.text}")
        return True
    else:
        print(f"❌ WP Post Error: {resp.status_code} - {resp.text}")
        return False

if __name__ == "__main__":
    print("--- SOKOBANJA BOT STARTED ---")
    news = get_latest_news()
    if news:
        print(f"Pronadjena vest: {news.get('title')} (ID: {news.get('id')})")
        post_article(news)
    else:
        print("Kraj: Nema vesti.")
    print("--- END ---")
