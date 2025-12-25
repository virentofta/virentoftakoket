FROM python:3.12-slim

# Grundläggande Python-inställningar
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Installera beroenden
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Kopiera källkoden
COPY . /app

# Skapa kataloger för data/bilder/backups
RUN mkdir -p /app/data/images /app/data/backups

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
