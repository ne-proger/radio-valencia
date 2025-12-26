from flask import Flask, render_template, request, redirect, url_for, flash, session
from postgrest import SyncPostgrestClient
import os
import requests
from datetime import datetime
import markdown

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Тут_нужно_очень_секретный_ключ_для_сессий'

# --- Supabase подключение ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://cjxiwdkxrmjndnjmoftc.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "sb_publishable_NOECPXgqO0Q7IeqUf650bw_IjbWeAYB")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

read_client = SyncPostgrestClient(f"{SUPABASE_URL}/rest/v1", headers={
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
})

if SUPABASE_SERVICE_ROLE_KEY:
    write_client = SyncPostgrestClient(f"{SUPABASE_URL}/rest/v1", headers={
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"
    })
else:
    write_client = read_client

# --- Настройки ---
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = '9mmPMam4527'

WEATHER_API_KEY = 'e247b1e3b030c1380b6120e5dd339e65'
WEATHER_URL = f"http://api.openweathermap.org/data/2.5/weather?lat=39.47&lon=-0.37&appid={WEATHER_API_KEY}&units=metric&lang=ru"

# --- Погода ---
def get_weather_data():
    try:
        response = requests.get(WEATHER_URL)
        response.raise_for_status()
        data = response.json()
        temperature = int(data['main']['temp'])
        description = data['weather'][0]['description'].capitalize()
        icon_url = 'https://storage.googleapis.com/radio-valensia-news-uploads/wether_icons/termom.png'
        weather_main = data['weather'][0]['main'].lower()
        if 'clear' in weather_main:
            icon_url = 'https://storage.googleapis.com/radio-valensia-news-uploads/wether_icons/sol.png'
        elif 'clouds' in weather_main:
            icon_url = 'https://storage.googleapis.com/radio-valensia-news-uploads/wether_icons/clo.png'
        elif 'rain' in weather_main or 'drizzle' in weather_main:
            icon_url = 'https://storage.googleapis.com/radio-valensia-news-uploads/wether_icons/rein.png'
        elif 'thunderstorm' in weather_main:
            icon_url = 'https://storage.googleapis.com/radio-valensia-news-uploads/wether_icons/storm.png'
        elif 'snow' in weather_main:
            icon_url = 'https://storage.googleapis.com/radio-valensia-news-uploads/wether_icons/snow.png'
        return {'temperature': temperature, 'description': description, 'icon': icon_url}
    except Exception:
        return None

# --- Вспомогательные ---
@app.context_processor
def inject_datetime():
    return {'datetime': datetime}

@app.template_filter('markdown')
def convert_markdown(text):
    return markdown.markdown(text)

# --- Получение постов с пагинацией + main_image_url + total из header ---
def get_posts(category, page=1, per_page=6):
    # Pinned
    pinned = read_client.from_('post').select("*").eq('category', category).eq('is_pinned', True).order('date_posted', desc=True).execute().data

    # Total count with Prefer: count=exact
    count_response = read_client.from_('post').select("id").eq('category', category).execute(headers={"Prefer": "count=exact"})
    content_range = count_response.headers.get('Content-Range', '*/0')
    total = int(content_range.split('/')[-1]) if '/' in content_range else 0

    # Normal posts with range
    start = (page - 1) * per_page - len(pinned)
    end = start + per_page - 1
    start = max(start, 0)
    normal = []
    if start <= total and end >= start:
        normal = read_client.from_('post').select("*").eq('category', category).eq('is_pinned', False).order('date_posted', desc=True).range(start, end).execute().data

    posts = pinned + normal

    for post in posts:
        post['date_posted'] = datetime.fromisoformat(post['date_posted'].replace('Z', '+00:00'))
        # Main image for list
        main_img = read_client.from_('image').select("url").eq('post_id', post['id']).order('is_main', desc=True).order('id', desc=False).limit(1).execute().data
        post['main_image_url'] = main_img[0]['url'] if main_img else ''

    total_pages = (total + per_page - 1) // per_page if total else 1

    return posts, total_pages, page

# --- Маршруты разделов (остальное без изменений) ---
@app.route("/")
@app.route("/page/<int:page>")
def home(page=1):
    posts, total_pages, current_page = get_posts('news', page)
    weather = get_weather_data()
    return render_template('home.html', posts=posts, weather=weather, pagination={'pages': total_pages, 'page': current_page, 'has_prev': current_page > 1, 'has_next': current_page < total_pages, 'prev_num': current_page - 1, 'next_num': current_page + 1}, current_section='home')

# (аналогично для history, finance, sport)

# (остальной код app.py без изменений — админка, post, комментарии, реакции)

if __name__ == '__main__':
    app.run(debug=True)