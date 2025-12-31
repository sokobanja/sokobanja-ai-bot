import os
import requests
from requests.auth import HTTPBasicAuth

def automatizuj_objavu():
    # Podaci za pristup (iz GitHub Secrets)
    user = os.environ["WP_USERNAME"]
    password = os.environ["WP_APP_PASSWORD"]
    auth = HTTPBasicAuth(user, password)
    
    # 1. Uzmi podatke sa tvog agregatora (portal.sokobanja.org.rs)
    # Ovaj URL treba da vrati JSON sa naslovom, tekstom i URL-om slike
    api_url = "https://portal.sokobanja.org.rs/api/get-latest-news" 
    data = requests.get(api_url).json()

    # 2. Upload slike na WordPress
    image_res = requests.get(data['image_url'])
    media_payload = {
        'content-disposition': 'attachment; filename=vest_dana.jpg',
        'content-type': 'image/jpeg'
    }
    upload = requests.post(
        "https://sokobanja.org.rs/wp-json/wp/v2/media",
        auth=auth,
        headers=media_payload,
        data=image_res.content
    )
    image_id = upload.json().get('id')

    # 3. Objava vesti na sajt
    post_payload = {
        "title": data['title'],
        "content": data['content'],
        "status": "publish",
        "featured_media": image_id
    }
    
    final_res = requests.post(
        "https://sokobanja.org.rs/wp-json/wp/v2/posts",
        auth=auth,
        json=post_payload
    )
    
    if final_res.status_code == 201:
        print("SISTEM: Vest je uspešno objavljena!")
    else:
        print(f"SISTEM: Greška pri objavi - {final_res.text}")

if __name__ == "__main__":
    automatizuj_objavu()
