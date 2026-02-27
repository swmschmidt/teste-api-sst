"""
Cliente para interação com especificações Swagger/OpenAPI.
Responsável por obter e processar especificações de API.
"""
import requests
from typing import Dict, List


def obter_especificacao_api(swagger_url: str) -> Dict:
    """
    Obtém a especificação da API do endpoint Swagger.
    
    Args:
        swagger_url: URL do endpoint Swagger
        
    Returns:
        Dict contendo a especificação completa da API
        
    Raises:
        requests.HTTPError: Se a requisição falhar
    """
    response = requests.get(swagger_url)
    response.raise_for_status()
    return response.json()


def resolver_parametros(parametros: List, spec: Dict) -> List[Dict]:
    """
    Resolve referências de parâmetros ($ref) no Swagger spec.
    
    Args:
        parametros: Lista de parâmetros que podem conter referências $ref
        spec: Especificação completa da API
        
    Returns:
        Lista de parâmetros com todas as referências resolvidas
    """
    parametros_resolvidos = []
    
    for param in parametros:
        if isinstance(param, dict):
            if "$ref" in param:
                # Resolve a referência
                ref_path = param["$ref"]
                if ref_path.startswith("#/parameters/"):
                    param_name = ref_path.split("/")[-1]
                    if "parameters" in spec and param_name in spec["parameters"]:
                        parametros_resolvidos.append(spec["parameters"][param_name])
                    else:
                        # Se não conseguir resolver, ignora o parâmetro
                        continue
            else:
                # Parâmetro normal, sem referência
                parametros_resolvidos.append(param)
    
    return parametros_resolvidos


def extrair_endpoints_get(spec: Dict) -> List[Dict]:
    """
    Extrai todos os endpoints GET da especificação.
    
    Args:
        spec: Especificação completa da API
        
    Returns:
        Lista de dicionários contendo informações dos endpoints GET
    """
    endpoints = []
    for caminho, methods in spec["paths"].items():
        if "get" in methods:
            info_endpoint = methods["get"]
            parametros_raw = info_endpoint.get("parameters", [])
            parametros_resolvidos = resolver_parametros(parametros_raw, spec)
            
            endpoints.append({
                "path": caminho,
                "x_objeto_api": info_endpoint.get("x-objeto-api", ""),
                "x_caminho": info_endpoint.get("x-caminho", ""),
                "parameters": parametros_resolvidos,
                "summary": info_endpoint.get("summary", "")
            })
    return endpoints


def extrair_endpoints_todos(spec: Dict) -> List[Dict]:
    """
    Extrai todos os endpoints com todos os métodos HTTP disponíveis.
    
    Args:
        spec: Especificação completa da API
        
    Returns:
        Lista de dicionários contendo informações de todos os endpoints e métodos
    """
    endpoints = []
    for caminho, methods in spec["paths"].items():
        metodos_disponiveis = {}
        for metodo in ["get", "post", "put", "delete"]:
            if metodo in methods:
                parametros_raw = methods[metodo].get("parameters", [])
                parametros_resolvidos = resolver_parametros(parametros_raw, spec)
                
                metodos_disponiveis[metodo] = {
                    "parameters": parametros_resolvidos,
                    "requestBody": methods[metodo].get("requestBody", {}),
                    "consumes": methods[metodo].get("consumes", []),
                    "summary": methods[metodo].get("summary", "")
                }
        
        if "get" in metodos_disponiveis:
            info_get = methods["get"]
            endpoints.append({
                "path": caminho,
                "x_objeto_api": info_get.get("x-objeto-api", ""),
                "x_caminho": info_get.get("x-caminho", ""),
                "methods": metodos_disponiveis,
                "summary": info_get.get("summary", "")
            })
    return endpoints


def obter_nome_endpoint(endpoint: Dict) -> str:
    """
    Retorna o nome formatado do endpoint.
    
    Args:
        endpoint: Dicionário contendo informações do endpoint
        
    Returns:
        Nome formatado no padrão: "x_objeto_api - x_caminho"
    """
    return f"{endpoint['x_objeto_api']} - {endpoint['x_caminho']}"
