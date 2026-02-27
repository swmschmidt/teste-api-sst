"""
Extrator inteligente de valores de respostas da API.
Responsável por extrair valores válidos de respostas para construir parâmetros.
"""
import json
from typing import Dict, Any, List, Tuple


def extrair_valor_valido_da_resposta(
    dados_resposta: Dict,
    nome_param: str,
    tipo_param: str
) -> Any:
    """
    Extrai um valor válido da resposta sem parâmetros.
    Usa múltiplas estratégias de busca para encontrar o melhor match.
    
    Args:
        dados_resposta: Resposta da API
        nome_param: Nome do parâmetro a buscar
        tipo_param: Tipo do parâmetro (string, integer, etc)
        
    Returns:
        Valor extraído ou valor padrão
    """
    if not dados_resposta or "Key_000000" not in dados_resposta:
        return _valor_padrao_por_tipo(tipo_param)
    
    try:
        # Pega o primeiro registro
        dados_primeira_chave = json.loads(dados_resposta["Key_000000"])
        
        # Remove o prefixo P_ do nome do parâmetro
        nome_sem_prefixo = nome_param.replace("P_", "")
        
        # Estratégia 1: Correspondência exata no final da chave
        valor = _buscar_correspondencia_exata(dados_primeira_chave, nome_sem_prefixo)
        if valor is not None:
            return valor
        
        # Estratégia 2: Correspondência parcial usando sufixo
        valor = _buscar_correspondencia_sufixo(dados_primeira_chave, nome_sem_prefixo)
        if valor is not None:
            return valor
        
        # Estratégia 3: Busca por palavras-chave com pontuação
        valor = _buscar_por_palavras_chave(dados_primeira_chave, nome_sem_prefixo)
        if valor is not None:
            return valor
        
        # Fallback: retorna o primeiro valor disponível
        return next(iter(dados_primeira_chave.values()))
        
    except Exception:
        return _valor_padrao_por_tipo(tipo_param)


def _valor_padrao_por_tipo(tipo_param: str) -> Any:
    """Retorna valor padrão baseado no tipo."""
    return 1 if tipo_param == "integer" else "teste"


def _buscar_correspondencia_exata(
    dados: Dict,
    nome_sem_prefixo: str
) -> Any:
    """
    Estratégia 1: Procura correspondência exata no final da chave.
    
    Exemplo:
        nome_sem_prefixo = "DT_START"
        Chaves: ["SCO_RK_EVAL_PERS.DT_START", "STD_HR_PERIOD.STD_DT_START"]
        Retorna: valor de "SCO_RK_EVAL_PERS.DT_START" (nome mais curto)
    """
    correspondencias_exatas = []
    
    for chave, valor in dados.items():
        if chave.endswith(nome_sem_prefixo):
            # Extrai apenas o nome da coluna (parte depois do ponto)
            nome_coluna = chave.split(".")[-1] if "." in chave else chave
            correspondencias_exatas.append((chave, valor, nome_coluna))
    
    if not correspondencias_exatas:
        return None
    
    # Se houver múltiplas, prefere a com nome de coluna mais curto
    if len(correspondencias_exatas) > 1:
        correspondencias_exatas.sort(key=lambda x: len(x[2]))
    
    return correspondencias_exatas[0][1]


def _buscar_correspondencia_sufixo(
    dados: Dict,
    nome_sem_prefixo: str
) -> Any:
    """
    Estratégia 2: Busca por correspondência parcial usando sufixo.
    
    Exemplo:
        nome_sem_prefixo = "SCO_ID_WORK_LOCATION"
        Busca: "ID_WORK_LOCATION" ou "WORK_LOCATION"
    """
    partes_nome = nome_sem_prefixo.split("_")
    
    if len(partes_nome) <= 2:
        return None
    
    # Usa as últimas 2 partes para buscar
    sufixo_busca = "_".join(partes_nome[-2:])
    correspondencias = []
    
    for chave, valor in dados.items():
        if sufixo_busca in chave:
            # Preferência por correspondências mais longas (mais específicas)
            correspondencias.append((chave, valor, len(chave)))
    
    if not correspondencias:
        return None
    
    # Retorna a correspondência com chave mais longa
    correspondencias.sort(key=lambda x: x[2], reverse=True)
    return correspondencias[0][1]


def _buscar_por_palavras_chave(
    dados: Dict,
    nome_sem_prefixo: str
) -> Any:
    """
    Estratégia 3: Busca por palavras-chave individuais com sistema de pontuação.
    
    Exemplo:
        nome_sem_prefixo = "ID_DOCUMENT"
        Busca: chaves contendo "DOCUMENT" ou "DOC"
    """
    partes_nome = nome_sem_prefixo.split("_")
    palavras_chave = [parte for parte in partes_nome if len(parte) > 2]
    
    if not palavras_chave:
        return None
    
    melhores_correspondencias = []
    
    for chave, valor in dados.items():
        pontuacao = _calcular_pontuacao_correspondencia(chave, palavras_chave)
        
        if pontuacao > 0:
            melhores_correspondencias.append((chave, valor, pontuacao))
    
    if not melhores_correspondencias:
        return None
    
    # Retorna a melhor correspondência (maior pontuação)
    melhores_correspondencias.sort(key=lambda x: x[2], reverse=True)
    return melhores_correspondencias[0][1]


def _calcular_pontuacao_correspondencia(
    chave: str,
    palavras_chave: List[str]
) -> int:
    """
    Calcula pontuação de correspondência entre chave e palavras-chave.
    
    Args:
        chave: Chave do campo no registro
        palavras_chave: Lista de palavras para buscar
        
    Returns:
        Pontuação (0 = sem match, maior = melhor match)
    """
    pontuacao = 0
    partes_chave = chave.split(".")[-1].split("_")
    
    for palavra in palavras_chave:
        # Correspondência exata de palavra
        if palavra in partes_chave:
            pontuacao += 10
        # Correspondência parcial
        elif any(
            palavra.startswith(parte) or parte.startswith(palavra)
            for parte in partes_chave
            if len(parte) > 2
        ):
            pontuacao += 5
    
    return pontuacao
