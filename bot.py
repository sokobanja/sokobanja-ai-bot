import os
import requests

def get_data_from_portal():
    url = "https://portal.sokobanja.org.rs/api/get_latest.php"
    
    # IQ 180 Trik: Dodajemo "User-Agent" da server misli da smo čovek, a ne robot
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Dodajemo headers u zahtev
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status() # Ovo će baciti grešku ako server vrati 404 ili 500
        return response.json()
    except Exception as e:
        print(f"Greska na portalu: {e}")
        return None
