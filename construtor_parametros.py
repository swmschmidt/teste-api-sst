import json
from typing import Dict, List, Any
from configuracao import (
    P_SCO_ID_HR_R082H,
    P_SCO_ID_DISABILITY_R082H,
    P_SCO_DT_START_R082H
)


def extrair_valor_valido_da_resposta(dados_resposta: Dict, nome_param: str, tipo_param: str) -> Any:
    """Extrai um valor válido da resposta sem parâmetros"""
    if not dados_resposta or "Key_000000" not in dados_resposta:
        return 1 if tipo_param == "integer" else "teste"
    
    try:
        # Pega o primeiro registro
        dados_primeira_chave = json.loads(dados_resposta["Key_000000"])
        
        # Remove o prefixo P_ do nome do parâmetro
        nome_sem_prefixo = nome_param.replace("P_", "")
        
        # Estratégia 1: Procura correspondência exata no final da chave
        correspondencias_exatas = []
        for chave, valor in dados_primeira_chave.items():
            if chave.endswith(nome_sem_prefixo):
                # Extrai apenas o nome da coluna (parte depois do ponto)
                nome_coluna = chave.split(".")[-1] if "." in chave else chave
                correspondencias_exatas.append((chave, valor, nome_coluna))
        
        if correspondencias_exatas:
            # Se houver múltiplas correspondências, prefere a que tem o nome de coluna mais curto
            # Isso resolve casos como DT_START vs STD_DT_START
            if len(correspondencias_exatas) > 1:
                correspondencias_exatas.sort(key=lambda x: len(x[2]))
            return correspondencias_exatas[0][1]
        
        # Caso especial para endpoint R056: se não encontrou DT_START exato, tenta sem prefixo STD_
        # Exemplo: P_DT_START deve usar SCO_RK_EVAL_PERS.DT_START (valor: "2024-12-12")
        # e não STD_HR_PERIOD.STD_DT_START (valor: "2006-01-30")
        # O endswith("DT_START") captura ambos, então buscamos exatamente "DT_START" como nome de coluna
        if nome_sem_prefixo == "DT_START":
            for chave, valor in dados_primeira_chave.items():
                nome_coluna = chave.split(".")[-1] if "." in chave else chave
                if nome_coluna == "DT_START":
                    return valor
        
        # Estratégia 2: Se não encontrou, procura por correspondência parcial usando sufixo
        # Busca pela parte mais significativa do nome (após o último underscore)
        # Ex: P_SCO_ID_WORK_LOCATION -> busca WORK_LOCATION
        partes_nome = nome_sem_prefixo.split("_")
        if len(partes_nome) > 2:
            # Usa as últimas 2-3 partes para buscar (ex: ID_WORK_LOCATION ou WORK_LOCATION)
            sufixo_busca = "_".join(partes_nome[-2:])
            correspondencias = []
            for chave, valor in dados_primeira_chave.items():
                if sufixo_busca in chave:
                    # Calcula quão próxima é a correspondência (preferência por correspondências mais longas)
                    correspondencias.append((chave, valor, len(chave)))
            
            # Retorna a correspondência com chave mais longa (mais específica)
            if correspondencias:
                correspondencias.sort(key=lambda x: x[2], reverse=True)
                return correspondencias[0][1]
        
        # Estratégia 3: Busca por palavras-chave individuais e pontuação
        # Ex: P_ID_DOCUMENT -> procura por chaves contendo "DOCUMENT" ou "DOC"
        palavras_chave = [parte for parte in partes_nome if len(parte) > 2]
        melhores_correspondencias = []
        
        for chave, valor in dados_primeira_chave.items():
            pontuacao = 0
            partes_chave = chave.split(".")[-1].split("_")  # Pega apenas a parte depois do ponto
            
            for palavra in palavras_chave:
                # Correspondência exata de palavra
                if palavra in partes_chave:
                    pontuacao += 10
                # Correspondência parcial (ex: DOCUMENT encontra DOC)
                elif any(palavra.startswith(parte) or parte.startswith(palavra) for parte in partes_chave if len(parte) > 2):
                    pontuacao += 5
            
            if pontuacao > 0:
                melhores_correspondencias.append((chave, valor, pontuacao))
        
        # Retorna a melhor correspondência (maior pontuação)
        if melhores_correspondencias:
            melhores_correspondencias.sort(key=lambda x: x[2], reverse=True)
            return melhores_correspondencias[0][1]
        
        # Se ainda não encontrou, retorna o primeiro valor disponível
        primeiro_valor = next(iter(dados_primeira_chave.values()))
        return primeiro_valor
    except:
        return 1 if tipo_param == "integer" else "teste"


def construir_parametros_validos(parameters: List[Dict], resultado_sem_params: Dict = None, endpoint: Dict = None) -> Dict:
    """Constrói um conjunto válido de parâmetros baseado na resposta sem parâmetros"""
    if not parameters:
        return {}
    
    parametros_validos = {}
    
    if resultado_sem_params and resultado_sem_params.get("success"):
        # Extrai valores para TODOS os parâmetros do primeiro registro
        for param in parameters:
            nome_param = param["name"]
            tipo_param = param["type"]
            valor = extrair_valor_valido_da_resposta(resultado_sem_params["data"], nome_param, tipo_param)
            parametros_validos[nome_param] = valor
    else:
        # Fallback: usa valores padrão apenas para o primeiro parâmetro
        primeiro_param = parameters[0]
        nome_param = primeiro_param["name"]
        tipo_param = primeiro_param["type"]
        parametros_validos[nome_param] = 1 if tipo_param == "integer" else "teste"
    
    # Caso especial para endpoints R057B e R057D: hardcode P_SCO_ID_RISK_FACTOR = "AG1"
    # Este valor não é retornado no GET sem parâmetros, então precisa ser fixado manualmente
    if endpoint and endpoint.get("x_objeto_api") in ["CBR_API_REST_SST_R057B", "CBR_API_REST_SST_R057D"]:
        if "P_SCO_ID_RISK_FACTOR" in parametros_validos:
            parametros_validos["P_SCO_ID_RISK_FACTOR"] = "AG1"
    
    # Caso especial para endpoint R082H: hardcode múltiplos parâmetros obrigatórios
    # Este endpoint não retorna dados sem estes parâmetros
    if endpoint and endpoint.get("x_objeto_api") == "CBR_API_REST_SST_R082H":
        if "P_SCO_ID_HR" in parametros_validos:
            parametros_validos["P_SCO_ID_HR"] = P_SCO_ID_HR_R082H
        if "P_SCO_ID_DISABILITY" in parametros_validos:
            parametros_validos["P_SCO_ID_DISABILITY"] = P_SCO_ID_DISABILITY_R082H
        if "P_SCO_DT_START" in parametros_validos:
            parametros_validos["P_SCO_DT_START"] = P_SCO_DT_START_R082H
    
    return parametros_validos


def construir_parametros_invalidos(parameters: List[Dict]) -> Dict:
    """Constrói um conjunto inválido de parâmetros"""
    if not parameters:
        return {"invalid_param": "999999"}
    
    parametros_invalidos = {}
    
    # Cria valores inválidos para TODOS os parâmetros
    for param in parameters:
        nome_param = param["name"]
        tipo_param = param["type"]
        
        # Usa número inválido para tipos numéricos, string para outros
        if tipo_param in ["integer", "number"]:
            valor_invalido = 999999999
        else:
            valor_invalido = "valor_inexistente_999999"
        
        parametros_invalidos[nome_param] = valor_invalido
    
    return parametros_invalidos
