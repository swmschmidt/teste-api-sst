"""
Configurações de definicoes para endpoints específicos.
Centraliza tratamentos especiais e hardcoded values para endpoints problemáticos.
"""
from typing import Dict, Optional
from definicoes_endpoints import DEFINICOES_ENDPOINTS


def aplicar_definicoes_especificas(
    parametros_validos: Dict,
    endpoint: Dict,
    metodo: str = "GET"
) -> Dict:
    """
    Aplica definicoes específicos para endpoints que requerem valores hardcoded.
    
    Args:
        parametros_validos: Parâmetros construídos normalmente
        endpoint: Informações do endpoint
        metodo: Método HTTP (GET, POST, PUT, DELETE)
        
    Returns:
        Parâmetros com definicoes aplicados
    """
    x_objeto_api = endpoint.get("x_objeto_api", "")
    
    # Verifica se há definicoes configurados para este endpoint
    if x_objeto_api not in DEFINICOES_ENDPOINTS:
        return parametros_validos
    
    config_endpoint = DEFINICOES_ENDPOINTS[x_objeto_api]
    substituicoes = config_endpoint.get("substituicoes", {})
    
    # Verifica se há substituições para este método específico
    if metodo not in substituicoes:
        return parametros_validos
    
    # Aplica as substituições configuradas
    parametros_atualizados = parametros_validos.copy()
    
    # Coleta todos os parâmetros P_ do definicao para este método
    definicao_p_params = {k: v for k, v in substituicoes[metodo].items() if k.startswith("P_")}
    
    if definicao_p_params:
        # Se há definicoes com P_, remove TODOS os P_ existentes e usa APENAS os do definicao
        # Isso garante que definicoes substituam completamente os parâmetros de query, não fazem merge
        parametros_atualizados = {k: v for k, v in parametros_atualizados.items() if not k.startswith("P_")}
        parametros_atualizados.update(definicao_p_params)
    
    # Atualiza parâmetros não-P_ que estão no definicao (raro, mas permite flexibilidade)
    for param_nome, param_valor in substituicoes[metodo].items():
        if not param_nome.startswith("P_") and param_nome in parametros_atualizados:
            parametros_atualizados[param_nome] = param_valor
    
    return parametros_atualizados


def deve_pular_teste_sem_parametros(endpoint: Dict) -> bool:
    """
    Verifica se o endpoint deve pular o teste sem parâmetros.
    
    Args:
        endpoint: Informações do endpoint
        
    Returns:
        True se deve pular o teste
    """
    x_objeto_api = endpoint.get("x_objeto_api", "")
    
    if x_objeto_api not in DEFINICOES_ENDPOINTS:
        return False
    
    return DEFINICOES_ENDPOINTS[x_objeto_api].get("pular_sem_parametros", False)


def obter_mensagem_skip(endpoint: Dict) -> Optional[str]:
    """
    Retorna mensagem explicativa para quando um teste é pulado.
    
    Args:
        endpoint: Informações do endpoint
        
    Returns:
        Mensagem ou None
    """
    x_objeto_api = endpoint.get("x_objeto_api", "")
    
    if x_objeto_api not in DEFINICOES_ENDPOINTS:
        return None
    
    return DEFINICOES_ENDPOINTS[x_objeto_api].get("mensagem_pular")


def requer_validacao_especial_registros(endpoint: Dict) -> bool:
    """
    Verifica se o endpoint requer validação comparativa de totalRegistros.
    
    Validação normal: espera totalRegistros=1 para parâmetros válidos.
    
    Validação comparativa: compara totalRegistros com vs sem parâmetros:
    - Se sem_parametros retorna 1 registro: com_parametros deve retornar 1
    - Se sem_parametros retorna 5 registros: com_parametros deve retornar <5
    
    Use quando o endpoint filtra dentro de um conjunto maior de registros.
    
    Args:
        endpoint: Informações do endpoint
        
    Returns:
        True se requer validação comparativa
    """
    x_objeto_api = endpoint.get("x_objeto_api", "")
    
    if x_objeto_api not in DEFINICOES_ENDPOINTS:
        return False
    
    return DEFINICOES_ENDPOINTS[x_objeto_api].get("validacao_comparativa", False)


