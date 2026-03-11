"""
FastAPI pour tester les scrapers Playwright en local.
Lance avec: uvicorn api_scraper:app --reload
Accède à: http://127.0.0.1:8000/docs (interface Swagger)
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import sys
import os

# Ajouter le dossier courant au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="🕷️ Scraper API - Missing Codes",
    description="""
    API pour lancer les scrapers de codes promo.
    
    Les résultats sont écrits directement dans Google Sheets (Missing_Code).
    
    ## Scrapers disponibles:
    - 🇦🇺 AU: Lifehacker, Cuponation
    - 🇺🇸 US: RetailMeNot, SimplyCodes, CouponFollow
    - 🇬🇧 UK: HotUKDeals, VoucherCodes
    - 🇩🇪 DE: MyDealz, Sparwelt
    - 🇫🇷 FR: iGraal, Ma-Reduc
    - 🇪🇸 ES: Chollometro, Cuponation
    - 🇮🇹 IT: Codice-Sconto, Cuponation
    - 🇵🇱 PL: Pepper, Rabatio
    """,
    version="1.0.0"
)

# Variable globale pour suivre le statut
scraper_status = {
    "running": False,
    "last_run": None,
    "last_source": None,
    "last_result": None
}


@app.get("/", tags=["Info"])
def root():
    """Page d'accueil - redirige vers /docs pour l'interface Swagger."""
    return {
        "message": "🕷️ Scraper API - Missing Codes",
        "docs": "Accédez à /docs pour l'interface Swagger",
        "status": scraper_status
    }


@app.get("/status", tags=["Info"])
def get_status():
    """Vérifie le statut du scraper."""
    return scraper_status


# ===================================================================
# AUSTRALIE
# ===================================================================

@app.post("/scrape/au/lifehacker", tags=["🇦🇺 Australie"])
def scrape_lifehacker_au():
    """
    🇦🇺 Lance le scraper Lifehacker Australie.
    
    Les codes sont écrits directement dans Google Sheets.
    """
    global scraper_status
    
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")
    
    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "Lifehacker AU"
        scraper_status["last_run"] = datetime.now().isoformat()
        
        # Import et exécution du scraper
        from AU.scrap_lifehacker_AU import main as scrape_lifehacker
        scrape_lifehacker()
        
        scraper_status["last_result"] = "✅ Succès"
        return {"status": "success", "message": "Scraping Lifehacker AU terminé", "source": "Lifehacker AU"}
    
    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        scraper_status["running"] = False


@app.post("/scrape/au/cuponation", tags=["🇦🇺 Australie"])
def scrape_cuponation_au():
    """🇦🇺 Lance le scraper Cuponation Australie."""
    global scraper_status
    
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")
    
    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "Cuponation AU"
        scraper_status["last_run"] = datetime.now().isoformat()
        
        from AU.scrap_cuponation_AU import main as scrape_cuponation
        scrape_cuponation()
        
        scraper_status["last_result"] = "✅ Succès"
        return {"status": "success", "message": "Scraping Cuponation AU terminé"}
    
    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        scraper_status["running"] = False


# ===================================================================
# USA
# ===================================================================

@app.post("/scrape/us/retailmenot", tags=["🇺🇸 USA"])
def scrape_retailmenot_us():
    """🇺🇸 Lance le scraper RetailMeNot USA."""
    global scraper_status
    
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")
    
    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "RetailMeNot US"
        scraper_status["last_run"] = datetime.now().isoformat()
        
        from US.scrap_retailmenot_US import main as scrape_retailmenot
        scrape_retailmenot()
        
        scraper_status["last_result"] = "✅ Succès"
        return {"status": "success", "message": "Scraping RetailMeNot US terminé"}
    
    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        scraper_status["running"] = False


@app.post("/scrape/us/simplycodes", tags=["🇺🇸 USA"])
def scrape_simplycodes_us():
    """🇺🇸 Lance le scraper SimplyCodes USA."""
    global scraper_status
    
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")
    
    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "SimplyCodes US"
        scraper_status["last_run"] = datetime.now().isoformat()
        
        from US.scrap_simplycodes_US import main as scrape_simplycodes
        scrape_simplycodes()
        
        scraper_status["last_result"] = "✅ Succès"
        return {"status": "success", "message": "Scraping SimplyCodes US terminé"}
    
    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        scraper_status["running"] = False


@app.post("/scrape/us/couponfollow", tags=["🇺🇸 USA"])
def scrape_couponfollow_us():
    """🇺🇸 Lance le scraper CouponFollow USA."""
    global scraper_status

    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")

    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "CouponFollow US"
        scraper_status["last_run"] = datetime.now().isoformat()

        from US.scrap_couponfollow_US import main as scrape_couponfollow
        scrape_couponfollow()

        scraper_status["last_result"] = "✅ Succès"
        return {"status": "success", "message": "Scraping CouponFollow US terminé"}

    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        scraper_status["running"] = False


# ===================================================================
# UK
# ===================================================================

@app.post("/scrape/uk/hotukdeals", tags=["🇬🇧 UK"])
def scrape_hotukdeals_uk():
    """🇬🇧 Lance le scraper HotUKDeals UK."""
    global scraper_status
    
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")
    
    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "HotUKDeals UK"
        scraper_status["last_run"] = datetime.now().isoformat()
        
        from UK.scrap_hotukdeals_UK import main as scrape_hotukdeals
        scrape_hotukdeals()
        
        scraper_status["last_result"] = "✅ Succès"
        return {"status": "success", "message": "Scraping HotUKDeals UK terminé"}
    
    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        scraper_status["running"] = False


@app.post("/scrape/uk/vouchercodes", tags=["🇬🇧 UK"])
def scrape_vouchercodes_uk():
    """🇬🇧 Lance le scraper VoucherCodes UK."""
    global scraper_status
    
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")
    
    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "VoucherCodes UK"
        scraper_status["last_run"] = datetime.now().isoformat()
        
        from UK.scrap_vouchercodes_UK import main as scrape_vouchercodes
        scrape_vouchercodes()
        
        scraper_status["last_result"] = "✅ Succès"
        return {"status": "success", "message": "Scraping VoucherCodes UK terminé"}
    
    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        scraper_status["running"] = False


# ===================================================================
# ALLEMAGNE
# ===================================================================

@app.post("/scrape/de/mydealz", tags=["🇩🇪 Allemagne"])
def scrape_mydealz_de():
    """🇩🇪 Lance le scraper MyDealz Allemagne."""
    global scraper_status
    
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")
    
    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "MyDealz DE"
        scraper_status["last_run"] = datetime.now().isoformat()
        
        from DE.scrap_mydealz_DE import main as scrape_mydealz
        scrape_mydealz()
        
        scraper_status["last_result"] = "✅ Succès"
        return {"status": "success", "message": "Scraping MyDealz DE terminé"}
    
    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        scraper_status["running"] = False


@app.post("/scrape/de/sparwelt", tags=["🇩🇪 Allemagne"])
def scrape_sparwelt_de():
    """🇩🇪 Lance le scraper Sparwelt Allemagne."""
    global scraper_status
    
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")
    
    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "Sparwelt DE"
        scraper_status["last_run"] = datetime.now().isoformat()
        
        from DE.scrap_sparwelt_DE import main as scrape_sparwelt
        scrape_sparwelt()
        
        scraper_status["last_result"] = "✅ Succès"
        return {"status": "success", "message": "Scraping Sparwelt DE terminé"}
    
    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        scraper_status["running"] = False


# ===================================================================
# FRANCE
# ===================================================================

@app.post("/scrape/fr/igraal", tags=["🇫🇷 France"])
def scrape_igraal_fr():
    """🇫🇷 Lance le scraper iGraal France."""
    global scraper_status
    
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")
    
    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "iGraal FR"
        scraper_status["last_run"] = datetime.now().isoformat()
        
        from FR.scrap_igraal_FR import main as scrape_igraal
        scrape_igraal()
        
        scraper_status["last_result"] = "✅ Succès"
        return {"status": "success", "message": "Scraping iGraal FR terminé"}
    
    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        scraper_status["running"] = False


@app.post("/scrape/fr/mareduc", tags=["🇫🇷 France"])
def scrape_mareduc_fr():
    """🇫🇷 Lance le scraper Ma-Reduc France."""
    global scraper_status
    
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")
    
    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "Ma-Reduc FR"
        scraper_status["last_run"] = datetime.now().isoformat()
        
        from FR.scrap_mareduc_FR import main as scrape_mareduc
        scrape_mareduc()
        
        scraper_status["last_result"] = "✅ Succès"
        return {"status": "success", "message": "Scraping Ma-Reduc FR terminé"}
    
    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        scraper_status["running"] = False


# ===================================================================
# ESPAGNE
# ===================================================================

@app.post("/scrape/es/chollometro", tags=["🇪🇸 Espagne"])
def scrape_chollometro_es():
    """🇪🇸 Lance le scraper Chollometro Espagne."""
    global scraper_status
    
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")
    
    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "Chollometro ES"
        scraper_status["last_run"] = datetime.now().isoformat()
        
        from ES.scrap_chollometro_ES import main as scrape_chollometro
        scrape_chollometro()
        
        scraper_status["last_result"] = "✅ Succès"
        return {"status": "success", "message": "Scraping Chollometro ES terminé"}
    
    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        scraper_status["running"] = False


@app.post("/scrape/es/cuponation", tags=["🇪🇸 Espagne"])
def scrape_cuponation_es():
    """🇪🇸 Lance le scraper Cuponation Espagne."""
    global scraper_status
    
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")
    
    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "Cuponation ES"
        scraper_status["last_run"] = datetime.now().isoformat()
        
        from ES.scrap_cuponation_ES import main as scrape_cuponation
        scrape_cuponation()
        
        scraper_status["last_result"] = "✅ Succès"
        return {"status": "success", "message": "Scraping Cuponation ES terminé"}
    
    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        scraper_status["running"] = False


# ===================================================================
# ITALIE
# ===================================================================

@app.post("/scrape/it/codicescontonet", tags=["🇮🇹 Italie"])
def scrape_codicescontonet_it():
    """🇮🇹 Lance le scraper Codice-Sconto.net Italie."""
    global scraper_status
    
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")
    
    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "Codicescontonet IT"
        scraper_status["last_run"] = datetime.now().isoformat()
        
        from IT.scrap_codicescontonet_IT import main as scrape_codicescontonet
        scrape_codicescontonet()
        
        scraper_status["last_result"] = "✅ Succès"
        return {"status": "success", "message": "Scraping Codicescontonet IT terminé"}
    
    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        scraper_status["running"] = False


@app.post("/scrape/it/cuponation", tags=["🇮🇹 Italie"])
def scrape_cuponation_it():
    """🇮🇹 Lance le scraper Cuponation Italie."""
    global scraper_status
    
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")
    
    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "Cuponation IT"
        scraper_status["last_run"] = datetime.now().isoformat()
        
        from IT.scrap_cuponation_IT import main as scrape_cuponation
        scrape_cuponation()
        
        scraper_status["last_result"] = "✅ Succès"
        return {"status": "success", "message": "Scraping Cuponation IT terminé"}
    
    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        scraper_status["running"] = False


# ===================================================================
# GROUPES DE SCRAPERS (pour Cloud Scheduler)
# ===================================================================

@app.post("/scrape/group1", tags=["📦 Groupes"])
def scrape_group1():
    """
    📦 Groupe 1: AU + IT (4 scrapers)
    
    - 🇦🇺 Lifehacker AU
    - 🇦🇺 Cuponation AU
    - 🇮🇹 Codicescontonet IT
    - 🇮🇹 Cuponation IT
    
    ⏱️ Durée estimée: 30-45 minutes
    """
    global scraper_status
    
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")
    
    results = []
    errors = []
    
    scrapers = [
        ("AU/Lifehacker", "AU.scrap_lifehacker_AU", "main"),
        ("AU/Cuponation", "AU.scrap_cuponation_AU", "main"),
        ("IT/Codicescontonet", "IT.scrap_codicescontonet_IT", "main"),
        ("IT/Cuponation", "IT.scrap_cuponation_IT", "main"),
    ]
    
    scraper_status["running"] = True
    scraper_status["last_source"] = "GROUP1 (AU+IT)"
    scraper_status["last_run"] = datetime.now().isoformat()
    
    try:
        for name, module, func in scrapers:
            try:
                print(f"\n{'='*60}")
                print(f"🚀 [GROUP1] Lancement de {name}...")
                print(f"{'='*60}")
                
                mod = __import__(module, fromlist=[func])
                getattr(mod, func)()
                results.append(f"✅ {name}")
            except Exception as e:
                errors.append(f"❌ {name}: {str(e)[:50]}")
        
        scraper_status["last_result"] = f"GROUP1: ✅ {len(results)} succès, {len(errors)} erreurs"
        
        return {
            "status": "completed",
            "group": "GROUP1 (AU+IT)",
            "success": results,
            "errors": errors,
            "total_success": len(results),
            "total_errors": len(errors)
        }
    
    finally:
        scraper_status["running"] = False


@app.post("/scrape/group2", tags=["📦 Groupes"])
def scrape_group2():
    """
    📦 Groupe 2: UK + US (5 scrapers)

    - 🇬🇧 HotUKDeals UK
    - 🇬🇧 VoucherCodes UK
    - 🇺🇸 RetailMeNot US
    - 🇺🇸 SimplyCodes US
    - 🇺🇸 CouponFollow US

    ⏱️ Durée estimée: 1h - 1h30
    """
    global scraper_status
    
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")
    
    results = []
    errors = []
    
    scrapers = [
        ("UK/HotUKDeals", "UK.scrap_hotukdeals_UK", "main"),
        ("UK/VoucherCodes", "UK.scrap_vouchercodes_UK", "main"),
        ("US/RetailMeNot", "US.scrap_retailmenot_US", "main"),
        ("US/SimplyCodes", "US.scrap_simplycodes_US", "main"),
        ("US/CouponFollow", "US.scrap_couponfollow_US", "main"),
    ]

    scraper_status["running"] = True
    scraper_status["last_source"] = "GROUP2 (UK+US)"
    scraper_status["last_run"] = datetime.now().isoformat()
    
    try:
        for name, module, func in scrapers:
            try:
                print(f"\n{'='*60}")
                print(f"🚀 [GROUP2] Lancement de {name}...")
                print(f"{'='*60}")
                
                mod = __import__(module, fromlist=[func])
                getattr(mod, func)()
                results.append(f"✅ {name}")
            except Exception as e:
                errors.append(f"❌ {name}: {str(e)[:50]}")
        
        scraper_status["last_result"] = f"GROUP2: ✅ {len(results)} succès, {len(errors)} erreurs"
        
        return {
            "status": "completed",
            "group": "GROUP2 (UK+US)",
            "success": results,
            "errors": errors,
            "total_success": len(results),
            "total_errors": len(errors)
        }
    
    finally:
        scraper_status["running"] = False


@app.post("/scrape/group3", tags=["📦 Groupes"])
def scrape_group3():
    """
    📦 Groupe 3: DE + FR (4 scrapers)

    - 🇩🇪 MyDealz DE
    - 🇩🇪 Sparwelt DE
    - 🇫🇷 iGraal FR
    - 🇫🇷 Ma-Reduc FR

    ⏱️ Durée estimée: 30-50 minutes
    """
    global scraper_status
    
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")
    
    results = []
    errors = []
    
    scrapers = [
        ("DE/MyDealz", "DE.scrap_mydealz_DE", "main"),
        ("DE/Sparwelt", "DE.scrap_sparwelt_DE", "main"),
        ("FR/iGraal", "FR.scrap_igraal_FR", "main"),
        ("FR/Ma-Reduc", "FR.scrap_mareduc_FR", "main"),
    ]
    
    scraper_status["running"] = True
    scraper_status["last_source"] = "GROUP3 (DE+FR)"
    scraper_status["last_run"] = datetime.now().isoformat()
    
    try:
        for name, module, func in scrapers:
            try:
                print(f"\n{'='*60}")
                print(f"🚀 [GROUP3] Lancement de {name}...")
                print(f"{'='*60}")
                
                mod = __import__(module, fromlist=[func])
                getattr(mod, func)()
                results.append(f"✅ {name}")
            except Exception as e:
                errors.append(f"❌ {name}: {str(e)[:50]}")
        
        scraper_status["last_result"] = f"GROUP3: ✅ {len(results)} succès, {len(errors)} erreurs"
        
        return {
            "status": "completed",
            "group": "GROUP3 (DE+FR)",
            "success": results,
            "errors": errors,
            "total_success": len(results),
            "total_errors": len(errors)
        }
    
    finally:
        scraper_status["running"] = False


@app.post("/scrape/group4", tags=["📦 Groupes"])
def scrape_group4():
    """
    📦 Groupe 4: ES (2 scrapers)

    - 🇪🇸 Chollometro ES
    - 🇪🇸 Cuponation ES

    ⏱️ Durée estimée: 30-45 minutes
    """
    global scraper_status

    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")

    results = []
    errors = []

    scrapers = [
        ("ES/Chollometro", "ES.scrap_chollometro_ES", "main"),
        ("ES/Cuponation", "ES.scrap_cuponation_ES", "main"),
    ]

    scraper_status["running"] = True
    scraper_status["last_source"] = "GROUP4 (ES)"
    scraper_status["last_run"] = datetime.now().isoformat()

    try:
        for name, module, func in scrapers:
            try:
                print(f"\n{'='*60}")
                print(f"🚀 [GROUP4] Lancement de {name}...")
                print(f"{'='*60}")

                mod = __import__(module, fromlist=[func])
                getattr(mod, func)()
                results.append(f"✅ {name}")
            except Exception as e:
                errors.append(f"❌ {name}: {str(e)[:50]}")

        scraper_status["last_result"] = f"GROUP4: ✅ {len(results)} succès, {len(errors)} erreurs"

        return {
            "status": "completed",
            "group": "GROUP4 (ES)",
            "success": results,
            "errors": errors,
            "total_success": len(results),
            "total_errors": len(errors)
        }

    finally:
        scraper_status["running"] = False


@app.post("/scrape/group5", tags=["📦 Groupes"])
def scrape_group5():
    """
    📦 Groupe 5: PL (2 scrapers)

    - 🇵🇱 Pepper PL
    - 🇵🇱 Rabatio PL

    ⏱️ Durée estimée: 30-45 minutes
    """
    global scraper_status

    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")

    results = []
    errors = []

    scrapers = [
        ("PL/Pepper", "PL.scrap_pepper_PL", "main"),
        ("PL/Rabatio", "PL.scrap_rabatio_PL", "main"),
    ]

    scraper_status["running"] = True
    scraper_status["last_source"] = "GROUP5 (PL)"
    scraper_status["last_run"] = datetime.now().isoformat()

    try:
        for name, module, func in scrapers:
            try:
                print(f"\n{'='*60}")
                print(f"🚀 [GROUP5] Lancement de {name}...")
                print(f"{'='*60}")

                mod = __import__(module, fromlist=[func])
                getattr(mod, func)()
                results.append(f"✅ {name}")
            except Exception as e:
                errors.append(f"❌ {name}: {str(e)[:50]}")

        scraper_status["last_result"] = f"GROUP5: ✅ {len(results)} succès, {len(errors)} erreurs"

        return {
            "status": "completed",
            "group": "GROUP5 (PL)",
            "success": results,
            "errors": errors,
            "total_success": len(results),
            "total_errors": len(errors)
        }

    finally:
        scraper_status["running"] = False


# ===================================================================
# POLOGNE
# ===================================================================

@app.post("/scrape/pl/pepper", tags=["🇵🇱 Pologne"])
def scrape_pepper_pl():
    """🇵🇱 Lance le scraper Pepper Pologne."""
    global scraper_status

    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")

    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "Pepper PL"
        scraper_status["last_run"] = datetime.now().isoformat()

        from PL.scrap_pepper_PL import main as scrape_pepper
        scrape_pepper()

        scraper_status["last_result"] = "✅ Succès"
        return {"status": "success", "message": "Scraping Pepper PL terminé"}

    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        scraper_status["running"] = False


@app.post("/scrape/pl/rabatio", tags=["🇵🇱 Pologne"])
def scrape_rabatio_pl():
    """🇵🇱 Lance le scraper Rabatio Pologne."""
    global scraper_status

    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")

    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "Rabatio PL"
        scraper_status["last_run"] = datetime.now().isoformat()

        from PL.scrap_rabatio_PL import main as scrape_rabatio
        scrape_rabatio()

        scraper_status["last_result"] = "✅ Succès"
        return {"status": "success", "message": "Scraping Rabatio PL terminé"}

    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        scraper_status["running"] = False


# ===================================================================
# LANCER TOUS LES SCRAPERS
# ===================================================================

@app.post("/scrape/all", tags=["🌍 Tous"])
def scrape_all():
    """
    🌍 Lance TOUS les scrapers (17 au total).

    ⚠️ Attention: Cela peut prendre plusieurs minutes!
    """
    global scraper_status

    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")

    results = []
    errors = []

    scrapers = [
        ("AU/Lifehacker", "AU.scrap_lifehacker_AU", "main"),
        ("AU/Cuponation", "AU.scrap_cuponation_AU", "main"),
        ("US/RetailMeNot", "US.scrap_retailmenot_US", "main"),
        ("US/SimplyCodes", "US.scrap_simplycodes_US", "main"),
        ("US/CouponFollow", "US.scrap_couponfollow_US", "main"),
        ("UK/HotUKDeals", "UK.scrap_hotukdeals_UK", "main"),
        ("UK/VoucherCodes", "UK.scrap_vouchercodes_UK", "main"),
        ("DE/MyDealz", "DE.scrap_mydealz_DE", "main"),
        ("DE/Sparwelt", "DE.scrap_sparwelt_DE", "main"),
        ("FR/iGraal", "FR.scrap_igraal_FR", "main"),
        ("FR/Ma-Reduc", "FR.scrap_mareduc_FR", "main"),
        ("ES/Chollometro", "ES.scrap_chollometro_ES", "main"),
        ("ES/Cuponation", "ES.scrap_cuponation_ES", "main"),
        ("IT/Codicescontonet", "IT.scrap_codicescontonet_IT", "main"),
        ("IT/Cuponation", "IT.scrap_cuponation_IT", "main"),
        ("PL/Pepper", "PL.scrap_pepper_PL", "main"),
        ("PL/Rabatio", "PL.scrap_rabatio_PL", "main"),
    ]
    
    scraper_status["running"] = True
    scraper_status["last_source"] = "ALL"
    scraper_status["last_run"] = datetime.now().isoformat()
    
    try:
        for name, module, func in scrapers:
            try:
                print(f"\n{'='*60}")
                print(f"🚀 Lancement de {name}...")
                print(f"{'='*60}")
                
                mod = __import__(module, fromlist=[func])
                getattr(mod, func)()
                results.append(f"✅ {name}")
            except Exception as e:
                errors.append(f"❌ {name}: {str(e)[:50]}")
        
        scraper_status["last_result"] = f"✅ {len(results)} succès, {len(errors)} erreurs"
        
        return {
            "status": "completed",
            "success": results,
            "errors": errors,
            "total_success": len(results),
            "total_errors": len(errors)
        }
    
    finally:
        scraper_status["running"] = False


# ===================================================================
# MATCHER + ANALYZER (post-scraping)
# ===================================================================

@app.post("/scrape/matcher", tags=["🔧 Post-traitement"])
def run_matcher_and_analyzer(manual_date: str = None):
    """
    🔧 Lance le Code Matcher + Code Analyzer (réécriture des titres).

    1. Code Matcher: compare les codes scrapés avec BigQuery, normalise les dates, crée le spreadsheet
    2. Code Analyzer: réécrit les titres avec GPT-4o-mini dans le spreadsheet créé

    Args:
        manual_date: Date manuelle au format YYYY-MM-DD (optionnel, défaut: aujourd'hui)
    """
    global scraper_status

    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Un scraper est déjà en cours d'exécution")

    try:
        scraper_status["running"] = True
        scraper_status["last_source"] = "Matcher + Analyzer"
        scraper_status["last_run"] = datetime.now().isoformat()

        # Étape 1: Code Matcher
        print(f"\n{'='*60}")
        print(f"🔧 ÉTAPE 1: CODE MATCHER")
        print(f"{'='*60}")

        from code_matcher import main as run_matcher
        spreadsheet_url = run_matcher(manual_date=manual_date)

        if not spreadsheet_url:
            scraper_status["last_result"] = "⚠️ Matcher: aucun nouveau code"
            return {"status": "completed", "matcher": "no new codes", "analyzer": "skipped"}

        # Étape 2: Code Analyzer (réécriture des titres)
        print(f"\n{'='*60}")
        print(f"🤖 ÉTAPE 2: CODE ANALYZER (réécriture des titres)")
        print(f"{'='*60}")

        from code_analyzer import main as run_analyzer
        run_analyzer(batch_size=100)

        scraper_status["last_result"] = f"✅ Matcher + Analyzer terminés"
        return {
            "status": "completed",
            "matcher": "success",
            "analyzer": "success",
            "spreadsheet_url": spreadsheet_url
        }

    except Exception as e:
        scraper_status["last_result"] = f"❌ Erreur: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        scraper_status["running"] = False


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
