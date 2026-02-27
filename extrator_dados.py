"""
Extrator de dados de respostas da API.
Responsável por extrair e processar informações específicas das respostas.
"""
import json
from typing import Dict, Optional, Tuple, Any


def extrair_dados_primeiro_registro(resultado_get: Dict) -> Dict:
    """
    Extrai os dados do primeiro registro de uma resposta GET.
    
    Args:
        resultado_get: Resultado da chamada GET
        
    Returns:
        Dict com os dados do primeiro registro ou dict vazio se não encontrado
    """
    if not resultado_get.get("data") or "Key_000000" not in resultado_get["data"]:
        return {}
    
    try:
        dados_json = resultado_get["data"]["Key_000000"]
        return json.loads(dados_json) if isinstance(dados_json, str) else dados_json
    except Exception:
        return {}


def extrair_id_de_resposta(resultado: Dict, nome_campo_id: str) -> Optional[Any]:
    """
    Extrai o valor do campo ID da resposta de POST/PUT.
    
    Args:
        resultado: Resultado da chamada à API
        nome_campo_id: Nome do campo ID a ser extraído (pode ter prefixo P_)
        
    Returns:
        Valor do ID salvo ou None se não encontrado
    """
    if not resultado.get("data") or "Key_000000" not in resultado["data"]:
        return None
    
    try:
        dados_json = resultado["data"]["Key_000000"]
        dados = json.loads(dados_json) if isinstance(dados_json, str) else dados_json
        
        # Remove prefixos comuns (P_, SCO_) para comparação
        def normalizar_campo(nome: str) -> str:
            """Remove prefixos comuns para permitir comparação flexível."""
            if not nome:
                return ""
            # Remove P_ e SCO_ se presentes
            nome = nome.replace("P_", "").replace("SCO_", "")
            return nome
        
        nome_campo_busca = normalizar_campo(nome_campo_id)
        
        # Procura pelo campo ID no registro retornado
        for chave, valor in dados.items():
            nome_campo = chave.split(".")[-1] if "." in chave else chave
            nome_campo_normalizado = normalizar_campo(nome_campo)
            
            if nome_campo_normalizado == nome_campo_busca:
                return valor
        
        return None
        
    except Exception:
        return None


def extrair_id_de_parametros(parametros: Dict) -> Tuple[Optional[str], Optional[Any]]:
    """
    Extrai o nome e valor do campo ID dos parâmetros.
    
    Args:
        parametros: Dicionário de parâmetros
        
    Returns:
        Tupla (nome_campo_id, valor_id) ou (None, None) se não encontrado
    """
    for nome, valor in parametros.items():
        if "_ID_" in nome or nome.startswith("ID_") or nome.endswith("_ID"):
            return (nome, valor)
    return (None, None)


def atualizar_parametros_com_id(
    parametros: Dict,
    nome_campo_id: Optional[str],
    novo_id: Any
) -> Dict:
    """
    Cria uma cópia dos parâmetros substituindo o valor do campo ID.
    
    Args:
        parametros: Parâmetros originais
        nome_campo_id: Nome do campo ID a ser substituído
        novo_id: Novo valor do ID
        
    Returns:
        Nova cópia dos parâmetros com ID atualizado
    """
    parametros_novos = parametros.copy()
    if nome_campo_id:
        parametros_novos[nome_campo_id] = novo_id
    return parametros_novos
