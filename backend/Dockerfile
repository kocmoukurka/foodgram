FROM python:3.12

RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    libfreetype6-dev \
    zlib1g-dev \
    libpng-dev \
    libwebp-dev \
    libtiff-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt --no-cache-dir

COPY . .


CMD ["gunicorn", "foodgram.wsgi:application", "--bind", "0.0.0.0:8000"]
    