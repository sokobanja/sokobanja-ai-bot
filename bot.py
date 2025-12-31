import os
import requests
import google.generativeai as genai

# Podešavanje Geminija
# Koristimo API ključ koji si generisao u Google AI Studiju
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 1. Povlačenje sirovih podataka sa tvog portala
try:
    # URL tvoje aplikacije koja daje sirove vesti
    response = requests.get("https://portal.sokobanja.org.rs/api/latest-news", timeout=10)
    raw_data = response.text
except Exception as e:
    raw_data = f"Greška pri preuzimanju vesti: {str(e)}"

# 2. AI transformacija u stil "Sokobanjskog Hroničara"
# Ovde Gemini dobija instrukciju da piše kao lokalni novinar
prompt = f"""Ti si 'Sokobanjski Hroničar'. Na osnovu ovih sirovih podataka:
{raw_data}

Sastavi jedan zanimljiv, srdačan i informativan izveštaj za portal sokobanja.org.rs. 
Koristi HTML tagove (<h3>, <p>, <ul>) za formatiranje. 
Obavezno koristi emojije da tekst bude pregledniji. 
Fokusiraj se na manifestacije, servisne informacije i lepotu Sokobanje."""

ai_response = model.generate_content(prompt)
final_content = ai_response.text

# 3. Slanje objave na WordPress sajt sokobanja.org.rs
# Koristimo tvoj aibot nalog i Application Password
wp_url = "https://sokobanja.org.rs/wp-json/wp/v2/posts"
wp_auth = (os.environ["WP_USERNAME"], os.environ["WP_APP_PASSWORD"])

post_data = {
    "title": "Sokobanjski dnevnik: Najnovije vesti i dešavanja",
    "content": final_content,
    "status": "publish" # Menjaj u 'draft' ako želiš prvo da pregledaš u WP panelu
}

try:
    res = requests.post(wp_url, json=post_data, auth=wp_auth)
    if res.status_code == 201:
        print("Vesti su uspešno objavljene na sajtu!")
    else:
        print(f"Greška pri objavi: {res.status_code} - {res.text}")
except Exception as e:
    print(f"Sistem nije uspeo da se poveže sa WordPressom: {str(e)}")
