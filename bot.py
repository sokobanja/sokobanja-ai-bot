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

def get_latest_news():
    try:
        print("1. Trazim vesti na cekanju (u Redu/Queue)...")
        print(f"   -> URL: {GET_LATEST_URL}")
        
        resp = requests.get(GET_LATEST_URL, timeout=30)
        print(f"   -> SERVER ODGOVOR (Raw): {resp.text[:200]}") # Prikazi prvih 200 karaktera odgovora
        
        try:
            data = resp.json()
        except:
            print(f"   -> GRESKA: Server nije vratio validan JSON.")
            return None
        
        if "id" not in data:
            print("----------------------------------------------------------------")
            print("VAZNO: Nema novih vesti na cekanju (Queue je prazan).")
            print("AKCIJA: Idite na portal.sokobanja.org.rs, generisite vest i kliknite 'Sacuvaj za Auto-Pilot'.")
            print("----------------------------------------------------------------")
            return None
            
        return data
    except Exception as e:
        print(f"Greska pri dohvatanju vesti: {e}")
        return None

def find_category_id(category_name="Vesti"):
    """
    Pokusava da nadje ID kategorije na osnovu imena.
    Ako ne nadje, vraca 1 (Default).
    """
    print(f"2. Trazim ID za kategoriju: '{category_name}'...")
    try:
        resp = requests.get(f"{WP_URL}/categories?search={category_name}", auth=(WP_USER, WP_PASS))
        if resp.status_code == 200:
            cats = resp.json()
            if cats and len(cats) > 0:
                cat_id = cats[0]['id']
                print(f"   -> Pronadjena kategorija '{cats[0]['name']}' sa ID: {cat_id}")
                return cat_id
            else:
                print(f"   -> Kategorija '{category_name}' nije pronadjena. Koristim default ID: 1")
                return 1
        else:
             print(f"   -> Greska pri trazenju kategorije: {resp.status_code}. Koristim default ID: 1")
             return 1
    except Exception as e:
        print(f"   -> Exception pri trazenju kategorije: {e}. Koristim default ID: 1")
        return 1

def upload_image_to_wp(image_url):
    if not image_url: return None
    
    try:
        print(f"3. Preuzimam sliku: {image_url}")
        img_resp = requests.get(image_url)
        if img_resp.status_code != 200:
            print("Neuspesno preuzimanje slike.")
            return None
            
        filename = f"ai_gen_{int(time.time())}.png"
        headers = {
            "Content-Type": "image/png",
            "Content-Disposition": f"attachment; filename={filename}"
        }
        
        print("4. Saljem sliku na WordPress...")
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

    # Pronadji pravu kategoriju
    cat_id = find_category_id("Vesti") 

    # Upload slike (ako postoji)
    media_id = None
    if image_url:
        media_id = upload_image_to_wp(image_url)

    # Kreiranje posta
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
        auth=(WP_USER, WP_PASS)
    )

    if resp.status_code == 201:
        link = resp.json().get('link')
        print(f"✅ USPEH! Clanak objavljen: {link}")
        
        # Mark as Done
        print("6. Azuriram status u redu cekanja...")
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
    print("--- SOKOBANJA BOT STARTED (DEBUG MODE) ---")
    news = get_latest_news()
    if news:
        print(f"Pronadjena vest: {news.get('title')} (ID: {news.get('id')})")
        post_article(news)
    else:
        print("--- NISTA NIJE URADJENO (Procitaj logove iznad) ---")
    print("--- END ---")
