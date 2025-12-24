from app import db, app
from sqlalchemy import text

with app.app_context():
    # Добавляем колонку category, если её ещё нет
    db.session.execute(text("ALTER TABLE post ADD COLUMN category TEXT NOT NULL DEFAULT 'news'"))
    db.session.commit()
    
    # На всякий случай создаём все таблицы (если новых моделей добавим позже)
    db.create_all()
    
    print("Миграция завершена успешно: добавлено поле 'category' в таблицу post.")
    print("Все существующие посты теперь имеют category='news'.")