import requests
import time
from typing import Dict, List
from configuracao import API_KEY, SWAGGER_URL, HEADERS_DEFAULT, BASE_URL


def obter_especificacao_api() -> Dict:
    """Obtém a especificação da API do endpoint Swagger"""
    response = requests.get(SWAGGER_URL)
    response.raise_for_status()
    return response.json()


def construir_headers() -> Dict[str, str]:
    """Constrói os headers necessários para as requisições"""
    return {
        **HEADERS_DEFAULT,
        "Authorization": API_KEY
    }





def extrair_endpoints_get(spec: Dict) -> List[Dict]:
    """Extrai todos os endpoints GET da especificação"""
    endpoints = []
    for caminho, methods in spec["paths"].items():
        if "get" in methods:
            info_endpoint = methods["get"]
            endpoints.append({
                "path": caminho,
                "x_objeto_api": info_endpoint.get("x-objeto-api", ""),
                "x_caminho": info_endpoint.get("x-caminho", ""),
                "parameters": info_endpoint.get("parameters", []),
                "summary": info_endpoint.get("summary", "")
            })
    return endpoints


def obter_nome_endpoint(endpoint: Dict) -> str:
    """Retorna o nome do endpoint no formato especificado"""
    return f"{endpoint['x_objeto_api']} - {endpoint['x_caminho']}"


def chamar_api(base_url: str, caminho: str, headers: Dict, params: Dict = None) -> Dict:
    """Realiza chamada à API e retorna resposta com metadados"""
    url = f"{base_url}{caminho}"
    try:
        inicio_tempo = time.time()
        response = requests.get(url, headers=headers, params=params)
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


def avaliar_sucesso_teste(resultado: Dict, tipo_teste: str) -> Dict:
    """Avalia se o teste foi bem-sucedido baseado no tipo de teste e resposta"""
    if resultado["error"]:
        return {**resultado, "success": False}
    
    cod_retorno = resultado["data"].get("codRetorno")
    total_registros = resultado["data"].get("totalRegistros")
    
    if tipo_teste == "parametros_invalidos":
        # Para parâmetros inválidos, esperamos codRetorno 404
        sucesso = cod_retorno == "404"
    elif tipo_teste == "parametros_validos":
        # Para parâmetros válidos, esperamos codRetorno 200 e totalRegistros 1
        sucesso = cod_retorno == "200" and total_registros == "1"
    else:
        # Para sem parâmetros, esperamos codRetorno 200
        sucesso = cod_retorno == "200" if cod_retorno else True
    
    return {**resultado, "success": sucesso}
