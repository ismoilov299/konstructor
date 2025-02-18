# Python image
FROM python:3.10-slim

# OS bog'liqliklarini o'rnatish va cache tozalash
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Ishchi katalog
WORKDIR /app

# Avval requirements.txt nusxalash va o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Qolgan fayllarni nusxalash
COPY . .

# Portni ochamiz
EXPOSE 8000

# Konteyner ishga tushganda bajariladigan buyruq
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]