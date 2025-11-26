# Guide de déploiement sur Google Cloud Run

## Prérequis
- Compte Google Cloud (avec votre email d'entreprise)
- Projet Google Cloud créé
- Facturation activée (mais Cloud Run a un quota gratuit généreux)

## Étapes de déploiement

### 1. Installer Google Cloud CLI
Téléchargez depuis : https://cloud.google.com/sdk/docs/install

### 2. Initialiser gcloud
```powershell
gcloud init
gcloud auth login
```

### 3. Configurer votre projet
```powershell
# Créer un nouveau projet (ou utiliser un existant)
gcloud projects create votre-projet-scraper --name="Scraper API"

# Définir le projet actif
gcloud config set project votre-projet-scraper

# Activer les APIs nécessaires
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
```

### 4. Déployer l'application
Depuis le dossier FastAPI :

```powershell
cd C:\Users\nmusicki\Documents\Python_Scripts\scrap_code\FastAPI

# Build et déploiement en une commande
gcloud run deploy scraper-api `
  --source . `
  --platform managed `
  --region europe-west1 `
  --allow-unauthenticated `
  --memory 2Gi `
  --cpu 2 `
  --timeout 300
```

### 5. Récupérer l'URL
Après le déploiement, vous obtiendrez une URL comme :
```
https://scraper-api-xxxxx-ew.a.run.app
```

Partagez cette URL avec vos collègues !

## Sécurité (optionnel)

### Ajouter une authentification
Si vous voulez restreindre l'accès :

```powershell
# Déployer en mode authentifié
gcloud run deploy scraper-api --no-allow-unauthenticated

# Donner accès à des utilisateurs spécifiques
gcloud run services add-iam-policy-binding scraper-api `
  --member="user:collegue@entreprise.com" `
  --role="roles/run.invoker"
```

## Coûts estimés
- **Gratuit** : 2 millions de requêtes/mois
- **Au-delà** : ~0.40€ par million de requêtes
- Le scraping prend ~5-10 secondes, donc très économique

## Support
- Documentation : https://cloud.google.com/run/docs
- Console : https://console.cloud.google.com/run
