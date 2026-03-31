"""
Cliente HTTP para realizar requisições à API.
Responsável por construir headers e executar chamadas HTTP.
"""
import requests
import time
from typing import Dict, Optional


def construir_headers(api_key: str, headers_default: Dict[str, str]) -> Dict[str, str]:
    """
    Constrói os headers necessários para as requisições.
    
    Args:
        api_key: Chave de autenticação da API
        headers_default: Headers padrão configurados
        
    Returns:
        Dict contendo todos os headers necessários
    """
    return {
        **headers_default,
        "Authorization": api_key
    }


def chamar_api(
    base_url: str,
    caminho: str,
    headers: Dict,
    params: Optional[Dict] = None,
    metodo: str = "GET",
    body: Optional[Dict] = None,
    consumes: Optional[list] = None
) -> Dict:
    """
    Realiza chamada à API e retorna resposta com metadados.
    
    Args:
        base_url: URL base da API
        caminho: Caminho do endpoint
        headers: Headers HTTP
        params: Parâmetros de query string (opcional)
        metodo: Método HTTP (GET, POST, PUT, DELETE)
        body: Body da requisição (opcional)
        consumes: Lista de content types aceitos (ex: ["multipart/form-data"])
        
    Returns:
        Dict contendo status_code, data, error e response_time_ms
    """
    url = f"{base_url}{caminho}"
    
    try:
        inicio_tempo = time.time()
        
        if metodo.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
            
        elif metodo.upper() == "POST":
            response = _executar_post(url, headers, params, body, consumes)
            
        elif metodo.upper() == "PUT":
            response = _executar_put(url, headers, params, body, consumes)
            
        elif metodo.upper() == "DELETE":
            response = requests.delete(url, headers=headers, params=params)
            
        else:
            raise ValueError(f"Método HTTP não suportado: {metodo}")
        
        tempo_resposta_ms = int((time.time() - inicio_tempo) * 1000)
        dados = response.json() if response.text else {}
        
        return {
            "status_code": response.status_code,
            "data": dados,
            "error": None,
            "response_time_ms": tempo_resposta_ms
        }
        
    except Exception as e:
        return {
            "status_code": None,
            "data": {},
            "error": str(e),
            "response_time_ms": None
        }


def _executar_post(
    url: str,
    headers: Dict,
    params: Optional[Dict],
    body: Optional[Dict],
    consumes: Optional[list]
) -> requests.Response:
    """
    Executa requisição POST com encoding apropriado.
    
    Args:
        url: URL completa
        headers: Headers HTTP
        params: Parâmetros de query
        body: Body da requisição
        consumes: Content types aceitos
        
    Returns:
        Response object do requests
    """
    if consumes and "multipart/form-data" in consumes:
        # Para multipart/form-data, usa files= (mesmo para campos não-arquivo)
        files = {k: (None, v) for k, v in body.items()} if body else None
        return requests.post(url, headers=headers, params=params, files=files)
    elif not consumes or "application/json" in consumes or len(consumes) == 0:
        # Usa JSON por padrão ou quando explicitamente especificado
        import json
        headers_with_json = {**headers, "Content-Type": "application/json"}
        return requests.post(url, headers=headers_with_json, params=params, json=body)
    else:
        # Usa data= para application/x-www-form-urlencoded
        return requests.post(url, headers=headers, params=params, data=body)


def _executar_put(
    url: str,
    headers: Dict,
    params: Optional[Dict],
    body: Optional[Dict],
    consumes: Optional[list]
) -> requests.Response:
    """
    Executa requisição PUT com encoding apropriado.
    
    Args:
        url: URL completa
        headers: Headers HTTP
        params: Parâmetros de query
        body: Body da requisição
        consumes: Content types aceitos
        
    Returns:
        Response object do requests
    """
    if consumes and "multipart/form-data" in consumes:
        # Para multipart/form-data, usa files= (mesmo para campos não-arquivo)
        files = {k: (None, v) for k, v in body.items()} if body else None
        return requests.put(url, headers=headers, params=params, files=files)
    elif not consumes or "application/json" in consumes or len(consumes) == 0:
        # Usa JSON por padrão ou quando explicitamente especificado
        import json
        headers_with_json = {**headers, "Content-Type": "application/json"}
        return requests.put(url, headers=headers_with_json, params=params, json=body)
    else:
        # Usa data= para application/x-www-form-urlencoded
        return requests.put(url, headers=headers, params=params, data=body)
