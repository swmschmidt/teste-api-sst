"""
Construtor de bodies para requisições HTTP.
Responsável por criar e modificar bodies de requisições POST/PUT.
"""
from typing import Dict, List, Optional, Any


def aplicar_definicoes_body(
    body: Dict,
    endpoint: Dict,
    metodo: str
) -> Dict:
    """
    Aplica definicoes configurados ao body da requisição.
    
    Quando há definicoes configurados para o método, SUBSTITUI completamente o body
    pelos valores do definicao (não faz merge).
    
    Args:
        body: Body original construído
        endpoint: Informações do endpoint
        metodo: Método HTTP (POST, PUT, DELETE)
        
    Returns:
        Body com definicoes aplicados (substituição completa se houver definicao)
    """
    from definicoes_endpoints import DEFINICOES_ENDPOINTS
    
    x_objeto_api = endpoint.get("x_objeto_api", "")
    
    # Verifica se há definicoes configurados
    if x_objeto_api not in DEFINICOES_ENDPOINTS:
        return body
    
    config = DEFINICOES_ENDPOINTS[x_objeto_api]
    substituicoes = config.get("substituicoes", {})
    
    # Verifica se há substituições para este método
    if metodo not in substituicoes:
        return body
    
    # SUBSTITUI completamente o body pelos valores do definicao
    body_definicao = {}
    for campo, valor in substituicoes[metodo].items():
        # Remove prefixo P_ se necessário (campos de query que não vão no body)
        if not campo.startswith("P_"):
            body_definicao[campo] = valor
    
    return body_definicao


def construir_body_post(dados_registro: Dict) -> Dict:
    """
    Constrói o body para requisição POST baseado nos dados de um registro.
    Remove prefixos de tabela dos campos.
    
    Args:
        dados_registro: Dados do registro original (ex: de um GET)
        
    Returns:
        Dict com campos sem prefixos de tabela
        
    Exemplo:
        Input: {"DBR_EXAME.DBR_ID_EXAME": "123"}
        Output: {"DBR_ID_EXAME": "123"}
    """
    body = {}
    for chave, valor in dados_registro.items():
        nome_campo = chave.split(".")[-1] if "." in chave else chave
        body[nome_campo] = valor
    return body


def construir_body_de_parametros(
    parametros: List[Dict],
    dados_registro: Dict,
    id_teste: Optional[int] = None
) -> Dict:
    """
    Constrói body baseado em parâmetros formData e dados de um registro.
    
    Args:
        parametros: Lista de parâmetros da especificação Swagger
        dados_registro: Dados do registro de referência
        id_teste: ID de teste para substituir campos ID (opcional)
        
    Returns:
        Dict com body pronto para envio
    """
    body = {}
    
    # Filtra apenas parâmetros formData
    parametros_form = [
        p for p in parametros
        if isinstance(p, dict) and p.get("in") == "formData"
    ]
    
    for param in parametros_form:
        nome_param = param.get("name")
        if not nome_param:
            continue
        
        # Se é um campo ID e temos um ID de teste, usa o ID de teste
        if id_teste is not None and _e_campo_id(nome_param):
            body[nome_param] = id_teste
            continue
        
        # Tenta encontrar o valor correspondente no registro
        valor = _encontrar_valor_no_registro(nome_param, dados_registro)
        
        # Se não encontrou, usa valor padrão baseado no tipo
        if valor is None:
            tipo_param = param.get("type", "string")
            valor = 0 if tipo_param in ["integer", "number"] else ""
        
        body[nome_param] = valor
    
    return body


def modificar_body_put(body: Dict) -> Dict:
    """
    Modifica valores do body para teste de PUT.
    Altera campos de texto para "MODIFICADO" exceto IDs e datas.
    
    Args:
        body: Body original
        
    Returns:
        Body modificado para teste
    """
    body_modificado = body.copy()
    
    for chave, valor in body_modificado.items():
        if _deve_modificar_campo(chave, valor):
            body_modificado[chave] = "MODIFICADO"
    
    return body_modificado


def _e_campo_id(nome_campo: str) -> bool:
    """
    Verifica se o campo é um campo ID.
    
    Args:
        nome_campo: Nome do campo
        
    Returns:
        True se for campo ID
    """
    return ("_ID_" in nome_campo or 
            nome_campo.startswith("ID_") or 
            nome_campo.endswith("_ID"))


def _encontrar_valor_no_registro(nome_param: str, dados_registro: Dict) -> Optional[Any]:
    """
    Encontra o valor correspondente ao parâmetro no registro.
    
    Args:
        nome_param: Nome do parâmetro a buscar
        dados_registro: Dados do registro
        
    Returns:
        Valor encontrado ou None
    """
    for chave, val in dados_registro.items():
        nome_campo = chave.split(".")[-1] if "." in chave else chave
        if nome_campo == nome_param:
            return val
    return None


def _deve_modificar_campo(chave: str, valor: Any) -> bool:
    """
    Verifica se um campo deve ser modificado no teste PUT.
    
    Args:
        chave: Nome do campo
        valor: Valor do campo
        
    Returns:
        True se deve ser modificado
    """
    # Não modifica IDs
    if chave.endswith("_ID"):
        return False
    
    # Não modifica datas
    if chave.startswith("DT_"):
        return False
    
    # Só modifica strings não vazias e não numéricas
    if not isinstance(valor, str):
        return False
    
    if len(valor) == 0 or valor.isdigit():
        return False
    
    return True


