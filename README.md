#  Как работать с репозиторием финального задания

# Foodgram 

Социальная сеть для обмена фотографиями котиков с возможностью отмечать достижения питомцев.

## О проекте

Foodgram - это fullstack-приложение, позволяющее:
-  Рецеты блюд
-  Подписываться на понравившыеся вам рецепты и блогиров
-  Формировать список попукоп для рецептов

## Технологический стек

**Frontend:**
- React.js
- Redux Toolkit
- Axios
- Material-UI

**Backend:**
- Python 3.12
- Django
- Django REST Framework
- PostgreSQL
- Gunicorn
- Nginx

**Инфраструктура:**
- Docker
- Docker Compose
- GitHub Actions (CI/CD)

### Требования:
- Docker 20.10+
- Docker Compose 1.29+

## Инструкция:
1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/kocmoukurka/foodgram.git
   cd foodgram
   ```

2. Заполнить .env в дериктории проекта:
```bash
    nano .env
```
- POSTGRES_DB=имя базы данных
- POSTGRES_USER=имя пользователя
- POSTGRES_PASSWORD=пароль пользователя
- DB_NAME=адрес базы данных Docker network, по умолчанию db
- DB_PORT=5432
- SECRET_KEY=SECRET_KEY django
- DEBUG=False django
- ALLOWED_HOSTS=ALLOWED_HOSTS django
- FRONTEND_URL= URl вашего сайта

## Запуск проекта:
```bash
   sudo docker compose -f docker-compose.production.yml up -d
   sudo docker compose -f docker-compose.production.yml exec backend python manage.py migrate # При первом запуске
   sudo docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic # При первом запуске
   sudo docker compose -f docker-compose.production.yml exec backend python manage.py loaddata ingredients # При первом запуске
```
## APi
- Api документация доступна по адресу 
- ваш_url//api/docs/

# Автор
GitHub: @kocmoukurka
ФИО Шаронов И.С.

