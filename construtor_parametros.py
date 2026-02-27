"""
Construtor de parâmetros para requisições à API.
Orquestra a construção de parâmetros válidos e inválidos.
"""
from typing import Dict, List, Optional
from extrator_valores import extrair_valor_valido_da_resposta
from substituicoes_endpoint import aplicar_overrides_especificos


def construir_parametros_validos(
    parameters: List[Dict],
    resultado_sem_params: Optional[Dict] = None,
    endpoint: Optional[Dict] = None,
    metodo: str = "GET"
) -> Dict:
    """
    Constrói um conjunto válido de parâmetros baseado na resposta sem parâmetros.
    Retorna apenas parâmetros de query (in='query'), não formData.
    
    Args:
        parameters: Lista de parâmetros da especificação
        resultado_sem_params: Resultado da chamada sem parâmetros (opcional)
        endpoint: Informações do endpoint (opcional, para overrides)
        metodo: Método HTTP (GET, POST, PUT, DELETE) para aplicar overrides específicos
        
    Returns:
        Dict com parâmetros válidos construídos
    """
    if not parameters:
        return {}
    
    # Filtra apenas parâmetros de query (não formData)
    parametros_query = [
        p for p in parameters
        if isinstance(p, dict) and p.get("in") == "query"
    ]
    
    if not parametros_query:
        return {}
    
    # Constrói parâmetros baseado na resposta
    if resultado_sem_params and resultado_sem_params.get("success"):
        parametros_validos = _construir_de_resposta(
            parametros_query,
            resultado_sem_params
        )
    else:
        parametros_validos = _construir_fallback(parametros_query)
    
    # Aplica overrides específicos de endpoints se necessário
    if endpoint:
        parametros_validos = aplicar_overrides_especificos(
            parametros_validos,
            endpoint,
            metodo
        )
    
    return parametros_validos


def construir_parametros_invalidos(parameters: List[Dict]) -> Dict:
    """
    Constrói um conjunto inválido de parâmetros.
    Retorna apenas parâmetros de query (in='query'), não formData.
    
    Args:
        parameters: Lista de parâmetros da especificação
        
    Returns:
        Dict com parâmetros inválidos
    """
    if not parameters:
        return {"invalid_param": "999999"}
    
    # Filtra apenas parâmetros de query
    parametros_query = [
        p for p in parameters
        if isinstance(p, dict) and p.get("in") == "query"
    ]
    
    if not parametros_query:
        return {"invalid_param": "999999"}
    
    parametros_invalidos = {}
    
    # Cria valores inválidos para TODOS os parâmetros de query
    for param in parametros_query:
        nome_param = param.get("name")
        if not nome_param:
            continue
        
        tipo_param = param.get("type", "string")
        
        # Usa número inválido para tipos numéricos, string para outros
        if tipo_param in ["integer", "number"]:
            valor_invalido = 999999999
        else:
            valor_invalido = "valor_inexistente_999999"
        
        parametros_invalidos[nome_param] = valor_invalido
    
    return parametros_invalidos


def _construir_de_resposta(
    parametros_query: List[Dict],
    resultado_sem_params: Dict
) -> Dict:
    """
    Constrói parâmetros extraindo valores da resposta.
    
    Args:
        parametros_query: Lista de parâmetros de query
        resultado_sem_params: Resultado da chamada sem parâmetros
        
    Returns:
        Dict com parâmetros extraídos
    """
    parametros_validos = {}
    
    for param in parametros_query:
        nome_param = param.get("name")
        if not nome_param:
            continue
        
        tipo_param = param.get("type", "string")
        valor = extrair_valor_valido_da_resposta(
            resultado_sem_params["data"],
            nome_param,
            tipo_param
        )
        parametros_validos[nome_param] = valor
    
    return parametros_validos


def _construir_fallback(parametros_query: List[Dict]) -> Dict:
    """
    Constrói parâmetros usando valores padrão (fallback).
    Usa apenas o primeiro parâmetro.
    
    Args:
        parametros_query: Lista de parâmetros de query
        
    Returns:
        Dict com parâmetros padrão
    """
    parametros_validos = {}
    
    if parametros_query and isinstance(parametros_query[0], dict):
        primeiro_param = parametros_query[0]
        nome_param = primeiro_param.get("name")
        tipo_param = primeiro_param.get("type", "string")
        
        if nome_param:
            parametros_validos[nome_param] = (
                1 if tipo_param == "integer" else "teste"
            )
    
    return parametros_validos
