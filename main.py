from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional
import uvicorn
import time

from scraper_hotukdeals import scrape_hotukdeals_single
from scraper_vouchercodes import scrape_vouchercodes_single
from scraper_retailmenot import scrape_retailmenot_single

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
                "title": "Get 15% off your parking reservation using this Birmingham Airport Parking promo code",
                "url": "https://www.hotukdeals.com/vouchers/birminghamairport.co.uk"
            }
        }


class ScrapeRequestVoucherCodes(BaseModel):
    """Modèle de requête pour le scraping VoucherCodes"""
    title: str
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Get 20% off full price items on the app",
                "url": "https://www.vouchercodes.co.uk/asos.com"
            }
        }


class ScrapeRequestRetailMeNot(BaseModel):
    """Modèle de requête pour le scraping RetailMeNot"""
    title: str
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "10% Off Stays",
                "url": "https://www.retailmenot.com/view/dusit.com"
            }
        }


class ScrapeResponse(BaseModel):
    """Modèle de réponse pour le scraping"""
    success: bool
    code: Optional[str]
    title: str
    message: str
    execution_time_seconds: Optional[float] = None


@app.get("/")
async def root():
    """Page d'accueil de l'API"""
    return {
        "message": "Bienvenue sur l'API de scraping de codes promo",
        "endpoints": {
            "hotukdeals": "/scrape/hotukdeals",
            "vouchercodes": "/scrape/vouchercodes",
            "retailmenot": "/scrape/retailmenot"
        },
        "documentation": "/docs"
    }


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


@app.post("/scrape/retailmenot", response_model=ScrapeResponse)
async def scrape_retailmenot(request: ScrapeRequestRetailMeNot):
    """
    Scrape un code promo depuis RetailMeNot
    
    Args:
        request: Objet contenant le titre et l'URL de l'offre
    
    Returns:
        Résultat du scraping avec le code trouvé (ou erreur)
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
        
        # Effectuer le scraping
        result = scrape_retailmenot_single(url_str, request.title)
        
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
