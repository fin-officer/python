FROM python:3.11-slim

WORKDIR /app

# Instalacja zależności systemowych
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Kopiowanie plików z zależnościami
COPY requirements.txt .

# Instalacja zależności Pythona
RUN pip install --no-cache-dir -r requirements.txt

# Utwórz katalogi dla danych
RUN mkdir -p /data/templates /data/archive

# Kopiowanie kodu aplikacji
COPY ./app /app/

# Ustawienie zmiennych środowiskowych
ENV PYTHONUNBUFFERED=1

# Ekspozycja portu
EXPOSE 8000

# Polecenie uruchomienia aplikacji
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]