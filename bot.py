import os
import requests
import json
import base64

# --- KONFIGURACIJA ---
PORTAL_API_URL = "https://portal.sokobanja.org.rs/api/get_latest.php"
WP_URL = "https://sokobanja.org.rs/wp-json/wp/v2"

# Ovi podaci se citaju iz GitHub Secrets (ili Environment varijabli)
WP_USER = os.environ.get("WP_USERNAME")
WP_PASS = os.environ.get("WP_APP_PASSWORD") # Application Password, ne tvoj login pass!

def get_latest_news():
    """Skida najnoviju pripremljenu vest sa Portala."""
    print(f"Connecting to {PORTAL_API_URL}...")
    try:
        response = requests.get(PORTAL_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            print(f"Portal kaze: {data['error']}")
            return None
        return data
    except Exception as e:
        print(f"Greska pri preuzimanju vesti: {e}")
        return None

def upload_image_to_wp(image_url, auth):
    """Skida sliku sa Portala i uploaduje je u WordPress Media Library."""
    if not image_url:
        return None
        
    print(f"Downloading image: {image_url}")
    try:
        img_response = requests.get(image_url)
        img_response.raise_for_status()
        
        filename = "ai-news-sokobanja.jpg"
        headers = {
            'Content-Type': 'image/jpeg',
            'Content-Disposition': f'attachment; filename={filename}'
        }
        
        print("Uploading to WordPress...")
        wp_response = requests.post(
            f"{WP_URL}/media",
            headers=headers,
            data=img_response.content,
            auth=auth
        )
        wp_response.raise_for_status()
        media_id = wp_response.json()['id']
        print(f"Image uploaded! ID: {media_id}")
        return media_id
    except Exception as e:
        print(f"Image upload failed: {e}")
        return None

def publish_post(news_data, media_id, auth):
    """Objavljuje konacan post na WordPress."""
    
    # Formatiranje HTML-a (pretvaramo nove redove u paragrafe ako vec nisu)
    content_html = news_data['content']
    
    post_data = {
        "title": news_data['title'],
        "content": content_html,
        "status": "publish", # Ili 'draft' ako zelis da pregledas pre objave
        "categories": [1], # ID kategorije 'Vesti' (promeni po potrebi)
        "featured_media": media_id if media_id else None
    }
    
    try:
        response = requests.post(
            f"{WP_URL}/posts",
            json=post_data,
            auth=auth
        )
        response.raise_for_status()
        link = response.json()['link']
        print(f"SUCCESS! Post published at: {link}")
    except Exception as e:
        print(f"Failed to publish post: {e}")

def main():
    if not WP_USER or not WP_PASS:
        print("CRITICAL: Nedostaju WP credentials u environment varijablama!")
        return

    auth = (WP_USER, WP_PASS)
    
    # 1. Uzmi vest
    news = get_latest_news()
    if not news:
        print("Nema novih vesti za objavu.")
        return

    print(f"Pronadjena vest: {news['title']}")

    # 2. Upload slike
    media_id = upload_image_to_wp(news.get('image_url'), auth)

    # 3. Objavi
    publish_post(news, media_id, auth)

if __name__ == "__main__":
    main()
