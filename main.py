from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
import uvicorn
import time
import requests

from scraper_hotukdeals import scrape_hotukdeals_single
from scraper_vouchercodes import scrape_vouchercodes_single
from scraper_retailmenot import scrape_retailmenot_all
from scraper_simplycodes import scrape_simplycodes_all

app = FastAPI(
    title="Scraper API",
    description="API pour scraper des codes promo depuis HotUKDeals et VoucherCodes",
    version="1.0.0"
)


class ScrapeRequestHotUKDeals(BaseModel):
    """Modèle de requête pour le scraping HotUKDeals"""
    title: str
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
                "example": {
                    "title": "Get 20% off full price items on the app",
                    "url": "https://www.hotukdeals.com/vouchers/asos.com"
                }
        }


class ScrapeRequestVoucherCodes(BaseModel):
    """Modèle de requête pour le scraping VoucherCodes"""
    title: str
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "5% off First Orders at Acer",
                "url": "https://www.vouchercodes.co.uk/uk-store.acer.com?oi=8792020"
            }
        }


class ScrapeRequestRetailMeNot(BaseModel):
    """Modèle de requête pour le scraping RetailMeNot - TOUS les codes"""
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.retailmenot.com/view/asos.com"
            }
        }


class ScrapeRequestSimplyCodes(BaseModel):
    """Modèle de requête pour le scraping SimplyCodes - TOUS les codes"""
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://simplycodes.com/store/autodesk.com"
            }
        }


class ScrapeResponse(BaseModel):
    """Modèle de réponse pour le scraping"""
    success: bool
    code: Optional[str]
    title: str
    message: str
    execution_time_seconds: Optional[float] = None


class ScrapeResponseItem(BaseModel):
    """Un code promo individuel"""
    success: bool
    code: str
    title: str
    message: str


class ScrapeAllResponse(BaseModel):
    """Modèle de réponse pour le scraping de tous les codes"""
    success: bool
    total_codes: int
    codes: List[ScrapeResponseItem]
    execution_time_seconds: float


@app.get("/")
async def root():
    """Page d'accueil de l'API"""
    return {
        "message": "Bienvenue sur l'API de scraping de codes promo",
        "endpoints": {
            "hotukdeals": "/scrape/hotukdeals",
            "vouchercodes": "/scrape/vouchercodes",
            "retailmenot": "/scrape/retailmenot (récupère TOUS les codes)",
            "simplycodes": "/scrape/simplycodes (récupère TOUS les codes)"
        },
        "documentation": "/docs"
    }


@app.post("/check-url")
def check_url(url: str, timeout: int = 15):
    """
    Vérifie l'accessibilité d'une URL
    
    Args:
        url: L'URL à vérifier
        timeout: Timeout en secondes (défaut: 15)
    
    Returns:
        Le code de statut HTTP de la réponse
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        # Essayer d'abord avec HEAD (plus rapide)
        response = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)
        return {"status_code": response.status_code}
    except requests.exceptions.Timeout:
        # Si timeout avec HEAD, essayer avec GET
        try:
            response = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True, stream=True)
            return {"status_code": response.status_code}
        except requests.exceptions.Timeout:
            return {"status_code": 0, "error": "Timeout - URL took too long to respond (tried HEAD and GET)"}
        except Exception as e:
            return {"status_code": 0, "error": str(e)}
    except requests.exceptions.ConnectionError:
        return {"status_code": 0, "error": "Connection error - Could not connect to URL"}
    except Exception as e:
        return {"status_code": 0, "error": str(e)}


@app.post("/scrape/hotukdeals", response_model=ScrapeResponse)
async def scrape_hotukdeals(request: ScrapeRequestHotUKDeals):
    """
    Scrape un code promo depuis HotUKDeals
    
    Args:
        request: Objet contenant le titre et l'URL de l'offre
    
    Returns:
        Résultat du scraping avec le code trouvé (ou erreur)
    """
    start_time = time.time()
    try:
        url_str = str(request.url)
        
        # Vérifier que c'est bien une URL HotUKDeals
        if "hotukdeals.com" not in url_str:
            raise HTTPException(
                status_code=400,
                detail="L'URL doit être une page HotUKDeals (hotukdeals.com)"
            )
        
        # Effectuer le scraping
        result = scrape_hotukdeals_single(url_str, request.title)
        
        # Ajouter le temps d'exécution
        execution_time = round(time.time() - start_time, 2)
        result["execution_time_seconds"] = execution_time
        
        if not result["success"]:
            raise HTTPException(
                status_code=404,
                detail=result["message"]
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors du scraping: {str(e)}"
        )


@app.post("/scrape/vouchercodes", response_model=ScrapeResponse)
async def scrape_vouchercodes(request: ScrapeRequestVoucherCodes):
    """
    Scrape un code promo depuis VoucherCodes
    
    Args:
        request: Objet contenant le titre et l'URL de l'offre
    
    Returns:
        Résultat du scraping avec le code trouvé (ou erreur)
    """
    start_time = time.time()
    try:
        url_str = str(request.url)
        
        # Vérifier que c'est bien une URL VoucherCodes
        if "vouchercodes.co.uk" not in url_str:
            raise HTTPException(
                status_code=400,
                detail="L'URL doit être une page VoucherCodes (vouchercodes.co.uk)"
            )
        
        # Effectuer le scraping
        result = scrape_vouchercodes_single(url_str, request.title)
        
        # Ajouter le temps d'exécution
        execution_time = round(time.time() - start_time, 2)
        result["execution_time_seconds"] = execution_time
        
        if not result["success"]:
            raise HTTPException(
                status_code=404,
                detail=result["message"]
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors du scraping: {str(e)}"
        )


@app.post("/scrape/retailmenot", response_model=ScrapeAllResponse)
async def scrape_retailmenot(request: ScrapeRequestRetailMeNot):
    """
    Scrape TOUS les codes promo depuis une page RetailMeNot
    
    Args:
        request: Objet contenant l'URL de la page RetailMeNot
    
    Returns:
        Liste de tous les codes promo trouvés sur la page
    
    Example:
        POST /scrape/retailmenot
        {"url": "https://www.retailmenot.com/view/asos.com"}
    """
    start_time = time.time()
    try:
        url_str = str(request.url)
        
        # Vérifier que c'est bien une URL RetailMeNot
        if "retailmenot.com" not in url_str:
            raise HTTPException(
                status_code=400,
                detail="L'URL doit être une page RetailMeNot (retailmenot.com)"
            )
        
        # Effectuer le scraping de TOUS les codes
        results = scrape_retailmenot_all(url_str)
        
        # Calculer le temps d'exécution
        execution_time = round(time.time() - start_time, 2)
        
        return ScrapeAllResponse(
            success=len(results) > 0,
            total_codes=len(results),
            codes=results,
            execution_time_seconds=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors du scraping: {str(e)}"
        )


@app.post("/scrape/simplycodes", response_model=ScrapeAllResponse)
async def scrape_simplycodes(request: ScrapeRequestSimplyCodes):
    """
    Scrape TOUS les codes promo depuis une page SimplyCodes
    
    Args:
        request: Objet contenant l'URL de la page SimplyCodes
    
    Returns:
        Liste de tous les codes promo trouvés sur la page
    
    Example:
        POST /scrape/simplycodes
        {"url": "https://simplycodes.com/store/autodesk.com"}
    """
    start_time = time.time()
    try:
        url_str = str(request.url)
        
        # Vérifier que c'est bien une URL SimplyCodes
        if "simplycodes.com" not in url_str:
            raise HTTPException(
                status_code=400,
                detail="L'URL doit être une page SimplyCodes (simplycodes.com)"
            )
        
        # Effectuer le scraping de TOUS les codes
        results = scrape_simplycodes_all(url_str)
        
        # Calculer le temps d'exécution
        execution_time = round(time.time() - start_time, 2)
        
        return ScrapeAllResponse(
            success=len(results) > 0,
            total_codes=len(results),
            codes=results,
            execution_time_seconds=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors du scraping: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
