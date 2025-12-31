import os
import requests
from requests.auth import HTTPBasicAuth

def pokreni_objavu():
    # Uzimanje podataka iz tvojih GitHub Secrets
    user = os.environ["WP_USERNAME"]
    password = os.environ["WP_APP_PASSWORD"]
    auth = HTTPBasicAuth(user, password)
    
    # 1. Pozivamo tvoj portal da nam da najnoviju vest
    # NAPOMENA: Ovaj URL mora da postoji na tvom portalu
    portal_url = "https://portal.sokobanja.org.rs/api/latest-news" 
    
    try:
        response = requests.get(portal_url)
        data = response.json()
        
        # 2. Slanje slike na WordPress (ako postoji URL slike)
        image_id = None
        if 'image_url' in data:
            img_res = requests.get(data['image_url'])
            media_res = requests.post(
                "https://sokobanja.org.rs/wp-json/wp/v2/media",
                auth=auth,
                headers={'Content-Disposition': 'attachment; filename=vest.jpg'},
                data=img_res.content
            )
            image_id = media_res.json().get('id')

        # 3. Kreiranje vesti na sajtu
        post_data = {
            "title": data.get('title', 'Vesti iz Sokobanje'),
            "content": data.get('content', 'Tekst vesti...'),
            "status": "publish",
            "featured_media": image_id
        }
        
        res = requests.post("https://sokobanja.org.rs/wp-json/wp/v2/posts", auth=auth, json=post_data)
        if res.status_code == 201:
            print("USPEH: Vest je objavljena na sokobanja.org.rs!")
        else:
            print(f"GRESKA: {res.text}")
            
    except Exception as e:
        print(f"Sistemska greška: {str(e)}")

if __name__ == "__main__":
    pokreni_objavu()
