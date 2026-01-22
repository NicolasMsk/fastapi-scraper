# Dockerfile pour FastAPI + Playwright sur Google Cloud Run
# Image officielle Playwright avec Python - inclut tous les navigateurs et dépendances

FROM mcr.microsoft.com/playwright/python:v1.57.0-jammy

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Répertoire de travail
WORKDIR /app

# Copier requirements et installer dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le dossier credentials (doit être copié dans Playwright/ avant build)
COPY credentials /app/credentials

# Copier tout le code de Playwright/
COPY . /app

# Exposer le port Cloud Run
EXPOSE 8080

# Lancer FastAPI avec uvicorn
CMD ["uvicorn", "api_scraper:app", "--host", "0.0.0.0", "--port", "8080"]
