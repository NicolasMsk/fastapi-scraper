from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
import uvicorn
import time
import requests

from scraper_hotukdeals import scrape_hotukdeals_all
from scraper_vouchercodes import scrape_vouchercodes_single, scrape_vouchercodes_all
from scraper_retailmenot import scrape_retailmenot_all
from scraper_simplycodes import scrape_simplycodes_all
from scraper_cuponation import scrape_cuponation_all
from scraper_lifehacker import scrape_lifehacker_all
from scraper_cuponation_es import scrape_cuponation_es_all
from scraper_chollometro import scrape_chollometro_all
from scraper_codicescontonet import scrape_codicescontonet_all
from scraper_cuponation_it import scrape_cuponation_it_all

app = FastAPI(
    title="Scraper API",
    description="API pour scraper des codes promo depuis HotUKDeals et VoucherCodes",
    version="1.0.0"
)


class ScrapeRequestHotUKDeals(BaseModel):
    """Modèle de requête pour le scraping HotUKDeals - TOUS les codes"""
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.hotukdeals.com/vouchers/asos.com"
            }
        }


class ScrapeRequestVoucherCodes(BaseModel):
    """Modèle de requête pour le scraping VoucherCodes - TOUS les codes"""
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.vouchercodes.co.uk/tui.co.uk"
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


class ScrapeRequestCuponation(BaseModel):
    """Modèle de requête pour le scraping Cuponation - TOUS les codes"""
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.cuponation.com.au/qatar-airways-promo-code"
            }
        }


class ScrapeRequestLifehacker(BaseModel):
    """Modèle de requête pour le scraping Lifehacker AU - TOUS les codes"""
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://au.lifehacker.com/coupons/emirates.com/"
            }
        }


class ScrapeRequestCuponationES(BaseModel):
    """Modèle de requête pour le scraping Cuponation Espagne - TOUS les codes"""
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.cuponation.es/cupon-descuento-ali-express"
            }
        }


class ScrapeRequestChollometro(BaseModel):
    """Modèle de requête pour le scraping Chollometro (HotUKDeals Espagne) - TOUS les codes"""
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.chollometro.com/cupones/atida.com"
            }
        }


class ScrapeRequestCodiceSconto(BaseModel):
    """Modèle de requête pour le scraping Codice-Sconto.net (Italie) - TOUS les codes"""
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://ubereats.codice-sconto.net/"
            }
        }


class ScrapeRequestCuponationIT(BaseModel):
    """Modèle de requête pour le scraping Cuponation Italie - TOUS les codes"""
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.cuponation.it/codice-sconto-groupon"
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
    message: str
    execution_time_seconds: float


@app.get("/")
async def root():
    """Page d'accueil de l'API"""
    return {
        "message": "Bienvenue sur l'API de scraping de codes promo",
        "endpoints": {
            "hotukdeals": "/scrape/hotukdeals (récupère TOUS les codes)",
            "vouchercodes": "/scrape/vouchercodes (récupère TOUS les codes)",
            "retailmenot": "/scrape/retailmenot (récupère TOUS les codes)",
            "simplycodes": "/scrape/simplycodes (récupère TOUS les codes)",
            "cuponation": "/scrape/cuponation (récupère TOUS les codes - Australie)",
            "lifehacker": "/scrape/lifehacker (récupère TOUS les codes - Australie)",
            "cuponation_es": "/scrape/cuponation_es (récupère TOUS les codes - Espagne)",
            "chollometro": "/scrape/chollometro (récupère TOUS les codes - Espagne, HotUKDeals)",
            "codicescontonet": "/scrape/codicescontonet (récupère TOUS les codes - Italie)",
            "cuponation_it": "/scrape/cuponation_it (récupère TOUS les codes - Italie)"
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


@app.post("/scrape/hotukdeals", response_model=ScrapeAllResponse)
async def scrape_hotukdeals_endpoint(request: ScrapeRequestHotUKDeals):
    """
    Scrape TOUS les codes promo d'une page HotUKDeals
    
    Args:
        request: Objet contenant l'URL de la page HotUKDeals
    
    Returns:
        Liste de tous les codes trouvés sur la page
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
        
        # Effectuer le scraping de TOUS les codes
        results = scrape_hotukdeals_all(url_str)
        
        # Calculer le temps d'exécution
        execution_time = round(time.time() - start_time, 2)
        
        # Message selon le résultat
        if len(results) > 0:
            message = f"{len(results)} code(s) found on the page"
        else:
            message = "No code found on this page"
        
        return ScrapeAllResponse(
            success=len(results) > 0,
            total_codes=len(results),
            codes=results,
            message=message,
            execution_time_seconds=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors du scraping: {str(e)}"
        )


@app.post("/scrape/vouchercodes", response_model=ScrapeAllResponse)
async def scrape_vouchercodes_endpoint(request: ScrapeRequestVoucherCodes):
    """
    Scrape TOUS les codes promo d'une page VoucherCodes
    
    Args:
        request: Objet contenant l'URL de la page VoucherCodes
    
    Returns:
        Liste de tous les codes trouvés sur la page
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
        
        # Effectuer le scraping de TOUS les codes
        results = scrape_vouchercodes_all(url_str)
        
        # Calculer le temps d'exécution
        execution_time = round(time.time() - start_time, 2)
        
        # Message selon le résultat
        if len(results) > 0:
            message = f"{len(results)} code(s) found on the page"
        else:
            message = "No code found on this page"
        
        return ScrapeAllResponse(
            success=len(results) > 0,
            total_codes=len(results),
            codes=results,
            message=message,
            execution_time_seconds=execution_time
        )
        
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
        
        # Message selon le résultat
        if len(results) > 0:
            message = f"{len(results)} code(s) found on the page"
        else:
            message = "No code found on this page"
        
        return ScrapeAllResponse(
            success=len(results) > 0,
            total_codes=len(results),
            codes=results,
            message=message,
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
        
        # Message selon le résultat
        if len(results) > 0:
            message = f"{len(results)} code(s) found on the page"
        else:
            message = "No code found on this page"
        
        return ScrapeAllResponse(
            success=len(results) > 0,
            total_codes=len(results),
            codes=results,
            message=message,
            execution_time_seconds=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors du scraping: {str(e)}"
        )


@app.post("/scrape/cuponation", response_model=ScrapeAllResponse)
async def scrape_cuponation(request: ScrapeRequestCuponation):
    """
    Scrape TOUS les codes promo depuis une page Cuponation (Australie)
    
    Args:
        request: Objet contenant l'URL de la page Cuponation
    
    Returns:
        Liste de tous les codes promo trouvés sur la page
    
    Example:
        POST /scrape/cuponation
        {"url": "https://www.cuponation.com.au/qatar-airways-promo-code"}
    """
    start_time = time.time()
    try:
        url_str = str(request.url)
        
        # Vérifier que c'est bien une URL Cuponation
        if "cuponation.com" not in url_str:
            raise HTTPException(
                status_code=400,
                detail="L'URL doit être une page Cuponation (cuponation.com)"
            )
        
        # Effectuer le scraping de TOUS les codes
        results = scrape_cuponation_all(url_str)
        
        # Calculer le temps d'exécution
        execution_time = round(time.time() - start_time, 2)
        
        # Message selon le résultat
        if len(results) > 0:
            message = f"{len(results)} code(s) found on the page"
        else:
            message = "No code found on this page"
        
        return ScrapeAllResponse(
            success=len(results) > 0,
            total_codes=len(results),
            codes=results,
            message=message,
            execution_time_seconds=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors du scraping: {str(e)}"
        )


@app.post("/scrape/lifehacker", response_model=ScrapeAllResponse)
async def scrape_lifehacker(request: ScrapeRequestLifehacker):
    """
    Scrape TOUS les codes promo depuis une page Lifehacker AU
    
    Args:
        request: Objet contenant l'URL de la page Lifehacker
    
    Returns:
        Liste de tous les codes promo trouvés sur la page
    
    Example:
        POST /scrape/lifehacker
        {"url": "https://au.lifehacker.com/coupons/emirates.com/"}
    """
    start_time = time.time()
    try:
        url_str = str(request.url)
        
        # Vérifier que c'est bien une URL Lifehacker
        if "lifehacker.com" not in url_str:
            raise HTTPException(
                status_code=400,
                detail="L'URL doit être une page Lifehacker (lifehacker.com)"
            )
        
        # Effectuer le scraping de TOUS les codes
        results = scrape_lifehacker_all(url_str)
        
        # Calculer le temps d'exécution
        execution_time = round(time.time() - start_time, 2)
        
        # Message selon le résultat
        if len(results) > 0:
            message = f"{len(results)} code(s) found on the page"
        else:
            message = "No code found on this page"
        
        return ScrapeAllResponse(
            success=len(results) > 0,
            total_codes=len(results),
            codes=results,
            message=message,
            execution_time_seconds=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors du scraping: {str(e)}"
        )


@app.post("/scrape/cuponation_es", response_model=ScrapeAllResponse)
async def scrape_cuponation_es(request: ScrapeRequestCuponationES):
    """
    Scrape TOUS les codes promo depuis une page Cuponation Espagne
    
    Args:
        request: Objet contenant l'URL de la page Cuponation ES
    
    Returns:
        Liste de tous les codes promo trouvés sur la page
    
    Example:
        POST /scrape/cuponation_es
        {"url": "https://www.cuponation.es/cupon-descuento-ali-express"}
    """
    start_time = time.time()
    try:
        url_str = str(request.url)
        
        # Vérifier que c'est bien une URL Cuponation ES
        if "cuponation.es" not in url_str:
            raise HTTPException(
                status_code=400,
                detail="L'URL doit être une page Cuponation Espagne (cuponation.es)"
            )
        
        # Effectuer le scraping de TOUS les codes
        results = scrape_cuponation_es_all(url_str)
        
        # Calculer le temps d'exécution
        execution_time = round(time.time() - start_time, 2)
        
        # Message selon le résultat
        if len(results) > 0:
            message = f"{len(results)} code(s) found on the page"
        else:
            message = "No code found on this page"
        
        return ScrapeAllResponse(
            success=len(results) > 0,
            total_codes=len(results),
            codes=results,
            message=message,
            execution_time_seconds=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors du scraping: {str(e)}"
        )


@app.post("/scrape/chollometro", response_model=ScrapeAllResponse)
async def scrape_chollometro(request: ScrapeRequestChollometro):
    """
    Scrape TOUS les codes promo depuis une page Chollometro (HotUKDeals Espagne)
    
    Args:
        request: Objet contenant l'URL de la page Chollometro
    
    Returns:
        Liste de tous les codes promo trouvés sur la page
    
    Example:
        POST /scrape/chollometro
        {"url": "https://www.chollometro.com/cupones/visiondirect.es"}
    """
    start_time = time.time()
    try:
        url_str = str(request.url)
        
        # Vérifier que c'est bien une URL Chollometro
        if "chollometro.com" not in url_str:
            raise HTTPException(
                status_code=400,
                detail="L'URL doit être une page Chollometro (chollometro.com)"
            )
        
        # Effectuer le scraping de TOUS les codes
        results = scrape_chollometro_all(url_str)
        
        # Calculer le temps d'exécution
        execution_time = round(time.time() - start_time, 2)
        
        # Message selon le résultat
        if len(results) > 0:
            message = f"{len(results)} code(s) found on the page"
        else:
            message = "No code found on this page"
        
        return ScrapeAllResponse(
            success=len(results) > 0,
            total_codes=len(results),
            codes=results,
            message=message,
            execution_time_seconds=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors du scraping: {str(e)}"
        )


@app.post("/scrape/codicescontonet", response_model=ScrapeAllResponse)
async def scrape_codicescontonet(request: ScrapeRequestCodiceSconto):
    """
    Scrape TOUS les codes promo depuis une page Codice-Sconto.net (Italie)
    
    Args:
        request: Objet contenant l'URL de la page codice-sconto.net
    
    Returns:
        Liste de tous les codes promo trouvés sur la page
    
    Example:
        POST /scrape/codicescontonet
        {"url": "https://ubereats.codice-sconto.net/"}
    """
    start_time = time.time()
    try:
        url_str = str(request.url)
        
        # Vérifier que c'est bien une URL codice-sconto.net
        if "codice-sconto.net" not in url_str:
            raise HTTPException(
                status_code=400,
                detail="L'URL doit être une page codice-sconto.net"
            )
        
        # Effectuer le scraping de TOUS les codes
        results = scrape_codicescontonet_all(url_str)
        
        # Calculer le temps d'exécution
        execution_time = round(time.time() - start_time, 2)
        
        # Message selon le résultat
        if len(results) > 0:
            message = f"{len(results)} code(s) found on the page"
        else:
            message = "No code found on this page"
        
        return ScrapeAllResponse(
            success=len(results) > 0,
            total_codes=len(results),
            codes=results,
            message=message,
            execution_time_seconds=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors du scraping: {str(e)}"
        )


@app.post("/scrape/cuponation_it", response_model=ScrapeAllResponse)
async def scrape_cuponation_it(request: ScrapeRequestCuponationIT):
    """
    Scrape TOUS les codes promo depuis une page Cuponation Italie
    
    Args:
        request: Objet contenant l'URL de la page Cuponation IT
    
    Returns:
        Liste de tous les codes promo trouvés sur la page
    
    Example:
        POST /scrape/cuponation_it
        {"url": "https://www.cuponation.it/codice-sconto-groupon"}
    """
    start_time = time.time()
    try:
        url_str = str(request.url)
        
        # Vérifier que c'est bien une URL Cuponation IT
        if "cuponation.it" not in url_str:
            raise HTTPException(
                status_code=400,
                detail="L'URL doit être une page Cuponation Italie (cuponation.it)"
            )
        
        # Effectuer le scraping de TOUS les codes
        results = scrape_cuponation_it_all(url_str)
        
        # Calculer le temps d'exécution
        execution_time = round(time.time() - start_time, 2)
        
        # Message selon le résultat
        if len(results) > 0:
            message = f"{len(results)} code(s) found on the page"
        else:
            message = "No code found on this page"
        
        return ScrapeAllResponse(
            success=len(results) > 0,
            total_codes=len(results),
            codes=results,
            message=message,
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
