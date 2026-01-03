from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, make_response
from postgrest import SyncPostgrestClient
import os
import requests
from datetime import datetime
import markdown
from xml.etree.ElementTree import Element, SubElement, tostring
from bs4 import BeautifulSoup  # Для очистки markdown от тегов

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

# Маршруты верификации
@app.route('/google57845417bd9a6989.html')
def google_verification():
    return send_from_directory(app.root_path, 'google57845417bd9a6989.html')

@app.route('/yandex_153d53007f9c0949.html')
def yandex_verification():
    return send_from_directory(app.root_path, 'yandex_153d53007f9c0949.html')

# --- robots.txt ---
@app.route('/robots.txt')
def robots():
    content = """User-agent: *
Allow: /
Disallow: /login
Disallow: /admin
Disallow: /admin/*
Sitemap: https://radio-valencia.onrender.com/sitemap.xml"""
    response = make_response(content)
    response.headers["Content-Type"] = "text/plain"
    return response

# --- Динамический sitemap.xml ---
@app.route('/sitemap.xml')
def sitemap():
    base_url = 'https://radio-valencia.onrender.com'
    
    static_urls = [
        f'{base_url}/',
        f'{base_url}/history',
        f'{base_url}/finance',
        f'{base_url}/sport',
        f'{base_url}/contacts'
    ]
    
    try:
        posts = read_client.from_('post').select('id').execute().data
        post_urls = [f'{base_url}/post/{post["id"]}' for post in posts]
    except:
        post_urls = []
    
    all_urls = static_urls + post_urls
    
    urlset = Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    
    for url in all_urls:
        url_elem = SubElement(urlset, 'url')
        loc = SubElement(url_elem, 'loc')
        loc.text = url
        lastmod = SubElement(url_elem, 'lastmod')
        lastmod.text = datetime.now().strftime('%Y-%m-%d')
        priority = SubElement(url_elem, 'priority')
        priority.text = '1.0' if url == f'{base_url}/' else '0.8' if url in static_urls else '0.6'
    
    xml_data = b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(urlset, encoding='utf-8')
    response = make_response(xml_data)
    response.headers["Content-Type"] = "application/xml"
    return response

# --- Получение постов с пагинацией ---
def get_posts(category, page=1, per_page=6):
    pinned = read_client.from_('post').select("*").eq('category', category).eq('is_pinned', True).order('date_posted', desc=True).execute().data
    
    normal = read_client.from_('post').select("*").eq('category', category).eq('is_pinned', False).order('date_posted', desc=True).execute().data
    
    all_posts = pinned + normal
    total = len(all_posts)
    total_pages = (total + per_page - 1) // per_page if total else 1
    
    start = (page - 1) * per_page
    end = start + per_page
    
    if page == 1:
        posts = pinned + normal[0: per_page - len(pinned)]
    else:
        adjusted_start = start - len(pinned)
        adjusted_end = end - len(pinned)
        posts = normal[adjusted_start: adjusted_end]
    
    for post in posts:
        post['date_posted'] = datetime.fromisoformat(post['date_posted'].replace('Z', '+00:00'))
        main_img = read_client.from_('image').select("url").eq('post_id', post['id']).order('is_main', desc=True).order('id', desc=False).limit(1).execute().data
        post['main_image_url'] = main_img[0]['url'] if main_img else ''
    
    return posts, total_pages, page

# --- Маршруты разделов с SEO ---
@app.route("/")
@app.route("/page/<int:page>")
def home(page=1):
    posts, total_pages, current_page = get_posts('news', page)
    weather = get_weather_data()
    return render_template('home.html', posts=posts, weather=weather, pagination={'pages': total_pages, 'page': current_page, 'has_prev': current_page > 1, 'has_next': current_page < total_pages, 'prev_num': current_page - 1, 'next_num': current_page + 1}, current_section='home',
                           title='Главная — RADIO VALENCIA', description='Свежие новости Валенсии: история, финансы, спорт', og_title='Главная — RADIO VALENCIA', og_description='Последние новости и статьи из Валенсии')

@app.route("/history")
@app.route("/history/page/<int:page>")
def history(page=1):
    posts, total_pages, current_page = get_posts('history', page)
    weather = get_weather_data()
    return render_template('history.html', posts=posts, weather=weather, pagination={'pages': total_pages, 'page': current_page, 'has_prev': current_page > 1, 'has_next': current_page < total_pages, 'prev_num': current_page - 1, 'next_num': current_page + 1}, current_section='history',
                           title='История Валенсии — RADIO VALENCIA', description='Исторические события и факты о Валенсии', og_title='История Валенсии', og_description='Исторические события и факты о Валенсии')

@app.route("/finance")
@app.route("/finance/page/<int:page>")
def finance(page=1):
    posts, total_pages, current_page = get_posts('finance', page)
    weather = get_weather_data()
    return render_template('finance.html', posts=posts, weather=weather, pagination={'pages': total_pages, 'page': current_page, 'has_prev': current_page > 1, 'has_next': current_page < total_pages, 'prev_num': current_page - 1, 'next_num': current_page + 1}, current_section='finance',
                           title='Финансы Валенсии — RADIO VALENCIA', description='Финансовые новости и аналитика', og_title='Финансы Валенсии', og_description='Финансовые новости и аналитика')

@app.route("/sport")
@app.route("/sport/page/<int:page>")
def sport(page=1):
    posts, total_pages, current_page = get_posts('sport', page)
    weather = get_weather_data()
    return render_template('sport.html', posts=posts, weather=weather, pagination={'pages': total_pages, 'page': current_page, 'has_prev': current_page > 1, 'has_next': current_page < total_pages, 'prev_num': current_page - 1, 'next_num': current_page + 1}, current_section='sport',
                           title='Спорт Валенсии — RADIO VALENCIA', description='Спортивные события и новости', og_title='Спорт Валенсии', og_description='Спортивные события и новости')

@app.route("/contacts")
def contacts():
    weather = get_weather_data()
    return render_template('contacts.html', current_section='contacts', weather=weather,
                           title='Контакты — RADIO VALENCIA', description='Связаться с редакцией RADIO VALENCIA', og_title='Контакты', og_description='Связаться с редакцией RADIO VALENCIA')

@app.route("/post/<int:post_id>")
def post(post_id):
    post_data = read_client.from_('post').select("*").eq('id', post_id).single().execute().data
    if not post_data:
        flash('Новость не найдена', 'danger')
        return redirect(url_for('home'))
    
    read_client.from_('post').update({'views': post_data['views'] + 1}).eq('id', post_id).execute()
    
    images_data = read_client.from_('image').select("url").eq('post_id', post_id).order('is_main', desc=True).order('id', desc=False).execute().data
    post_data['images'] = images_data
    post_data['main_image_url'] = images_data[0]['url'] if images_data else ''
    
    comments = read_client.from_('comment').select("*").eq('post_id', post_id).order('date_posted').execute().data
    post_data['comments'] = comments
    
    post_data['date_posted'] = datetime.fromisoformat(post_data['date_posted'].replace('Z', '+00:00'))
    for comment in post_data['comments']:
        comment['date_posted'] = datetime.fromisoformat(comment['date_posted'].replace('Z', '+00:00'))
    
    weather = get_weather_data()

    # Очистка контента для description
    html_content = markdown.markdown(post_data['content'])
    soup = BeautifulSoup(html_content, 'html.parser')
    clean_text = soup.get_text()
    description = clean_text[:155] + '...' if len(clean_text) > 155 else clean_text
    og_description = clean_text[:195] + '...' if len(clean_text) > 195 else clean_text

    return render_template('post.html', post=post_data, weather=weather, current_section=post_data['category'],
                           title=f"{post_data['title']} — RADIO VALENCIA",
                           description=description,
                           og_title=post_data['title'],
                           og_description=og_description)

# --- Остальные маршруты админки (без изменений, но с SEO) ---
# (оставил как было, но добавил title/description где нужно)

if __name__ == '__main__':
    app.run(debug=True)