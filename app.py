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

# Клиент для чтения (anon key)
read_client = SyncPostgrestClient(f"{SUPABASE_URL}/rest/v1", headers={
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
})

# Клиент для записи (service_role если есть, иначе anon)
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

# --- Получение постов с пагинацией ---
def get_posts(category, page=1, per_page=6):
    pinned = read_client.from_('post').select("*").eq('category', category).eq('is_pinned', True).order('date_posted', desc=True).execute().data
    
    start = (page - 1) * per_page
    end = start + per_page - 1 - len(pinned)
    if end < start:
        end = start - 1
    normal = read_client.from_('post').select("*").eq('category', category).eq('is_pinned', False).order('date_posted', desc=True).range(start, end).execute().data if end >= start else []
    
    posts = pinned + normal
    
    # Парсим date_posted в datetime для шаблона
    for post in posts:
        post['date_posted'] = datetime.fromisoformat(post['date_posted'].replace('Z', '+00:00'))
    
    total = read_client.from_('post').select("id", count='exact').eq('category', category).execute().count
    total_pages = (total + per_page - 1) // per_page if total else 1
    
    return posts, total_pages, page

# --- Маршруты разделов ---
@app.route("/")
@app.route("/page/<int:page>")
def home(page=1):
    posts, total_pages, current_page = get_posts('news', page)
    weather = get_weather_data()
    return render_template('home.html', posts=posts, weather=weather, pagination={'pages': total_pages, 'page': current_page, 'has_prev': current_page > 1, 'has_next': current_page < total_pages, 'prev_num': current_page - 1, 'next_num': current_page + 1}, current_section='home')

@app.route("/history")
@app.route("/history/page/<int:page>")
def history(page=1):
    posts, total_pages, current_page = get_posts('history', page)
    weather = get_weather_data()
    return render_template('history.html', posts=posts, weather=weather, pagination={'pages': total_pages, 'page': current_page, 'has_prev': current_page > 1, 'has_next': current_page < total_pages, 'prev_num': current_page - 1, 'next_num': current_page + 1}, current_section='history')

@app.route("/finance")
@app.route("/finance/page/<int:page>")
def finance(page=1):
    posts, total_pages, current_page = get_posts('finance', page)
    weather = get_weather_data()
    return render_template('finance.html', posts=posts, weather=weather, pagination={'pages': total_pages, 'page': current_page, 'has_prev': current_page > 1, 'has_next': current_page < total_pages, 'prev_num': current_page - 1, 'next_num': current_page + 1}, current_section='finance')

@app.route("/sport")
@app.route("/sport/page/<int:page>")
def sport(page=1):
    posts, total_pages, current_page = get_posts('sport', page)
    weather = get_weather_data()
    return render_template('sport.html', posts=posts, weather=weather, pagination={'pages': total_pages, 'page': current_page, 'has_prev': current_page > 1, 'has_next': current_page < total_pages, 'prev_num': current_page - 1, 'next_num': current_page + 1}, current_section='sport')

@app.route("/contacts")
def contacts():
    weather = get_weather_data()
    return render_template('contacts.html', current_section='contacts', weather=weather)

@app.route("/post/<int:post_id>")
def post(post_id):
    post_data = read_client.from_('post').select("*").eq('id', post_id).single().execute().data
    if not post_data:
        flash('Новость не найдена', 'danger')
        return redirect(url_for('home'))
    
    read_client.from_('post').update({'views': post_data['views'] + 1}).eq('id', post_id).execute()
    
    images = read_client.from_('image').select("url").eq('post_id', post_id).order('is_main', desc=True).order('id').execute().data
    post_data['images'] = [img['url'] for img in images]
    post_data['main_image_url'] = post_data['images'][0] if post_data['images'] else ''
    
    comments = read_client.from_('comment').select("*").eq('post_id', post_id).order('date_posted').execute().data
    post_data['comments'] = comments
    
    # Парсим date_posted для поста и комментариев
    post_data['date_posted'] = datetime.fromisoformat(post_data['date_posted'].replace('Z', '+00:00'))
    for comment in post_data['comments']:
        comment['date_posted'] = datetime.fromisoformat(comment['date_posted'].replace('Z', '+00:00'))
    
    weather = get_weather_data()
    return render_template('post.html', post=post_data, weather=weather, current_section=post_data['category'])

# --- Админка ---
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('Вход выполнен', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Неверный логин или пароль', 'danger')
    return render_template('login.html')

@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    flash('Вы вышли', 'info')
    return redirect(url_for('home'))

@app.route("/admin")
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    all_posts = read_client.from_('post').select("*").order('date_posted', desc=True).execute().data
    for post in all_posts:
        post['date_posted'] = datetime.fromisoformat(post['date_posted'].replace('Z', '+00:00'))
    return render_template('admin.html', posts=all_posts)

@app.route("/admin/new", methods=['GET', 'POST'])
def new_post():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        data = {
            'title': request.form['title'],
            'content': request.form['content'],
            'is_pinned': request.form.get('is_pinned') == 'on',
            'category': request.form.get('category', 'news')
        }
        new_post = write_client.from_('post').insert(data).execute().data[0]
        
        urls = [u.strip() for u in request.form.get('image_urls', '').split(',') if u.strip()]
        for i, url in enumerate(urls):
            write_client.from_('image').insert({'post_id': new_post['id'], 'url': url, 'is_main': i == 0}).execute()
        
        flash('Новость создана', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('create_post.html')

@app.route("/admin/edit/<int:post_id>", methods=['GET', 'POST'])
def edit_post(post_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    post_data = read_client.from_('post').select("*").eq('id', post_id).single().execute().data
    
    current_urls = ', '.join([img['url'] for img in read_client.from_('image').select("url").eq('post_id', post_id).execute().data])
    
    if request.method == 'POST':
        data = {
            'title': request.form['title'],
            'content': request.form['content'],
            'is_pinned': request.form.get('is_pinned') == 'on',
            'category': request.form.get('category', 'news')
        }
        write_client.from_('post').update(data).eq('id', post_id).execute()
        
        write_client.from_('image').delete().eq('post_id', post_id).execute()
        urls = [u.strip() for u in request.form.get('image_urls', '').split(',') if u.strip()]
        for i, url in enumerate(urls):
            write_client.from_('image').insert({'post_id': post_id, 'url': url, 'is_main': i == 0}).execute()
        
        flash('Новость обновлена', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_post.html', post=post_data, current_urls=current_urls)

@app.route("/admin/delete/<int:post_id>", methods=['POST'])
def delete_post(post_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    write_client.from_('post').delete().eq('id', post_id).execute()
    flash('Новость удалена', 'warning')
    return redirect(url_for('admin_dashboard'))

# --- Комментарии ---
@app.route("/post/<int:post_id>/comment", methods=['POST'])
def add_comment(post_id):
    username = request.form['username']
    content = request.form['content']
    if username and content:
        write_client.from_('comment').insert({'post_id': post_id, 'username': username, 'content': content}).execute()
        flash('Комментарий добавлен', 'success')
    return redirect(url_for('post', post_id=post_id) + '#comments')

# --- Реакции ---
@app.route("/post/<int:post_id>/react/<reaction_type>", methods=['POST'])
def react(post_id, reaction_type):
    column_map = {'like': 'likes', 'dislike': 'dislikes'}
    col = column_map.get(reaction_type)
    if not col:
        flash('Неверный тип реакции', 'danger')
        return redirect(url_for('post', post_id=post_id))
    
    post_data = read_client.from_('post').select(col).eq('id', post_id).single().execute().data
    current = post_data[col]
    write_client.from_('post').update({col: current + 1}).eq('id', post_id).execute()
    flash('Реакция учтена', 'success')
    return redirect(url_for('post', post_id=post_id))

if __name__ == '__main__':
    app.run(debug=True)