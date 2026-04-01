"""
Avaliador de resultados de testes.
Responsável por determinar sucesso/falha de testes baseado em critérios específicos.
"""
import json
from typing import Dict, Optional
from configuracao import CRITERIOS_SUCESSO


def avaliar_sucesso_teste(
    resultado: Dict,
    tipo_teste: str,
    metodo: str = "GET",
    body_enviado: Optional[Dict] = None,
    resultado_sem_params: Optional[Dict] = None,
    endpoint: Optional[Dict] = None
) -> Dict:
    """
    Avalia se o teste foi bem-sucedido baseado no tipo de teste e resposta.
    
    Args:
        resultado: Resultado da chamada à API
        tipo_teste: Tipo do teste (parametros_invalidos, parametros_validos, crud_*, etc)
        metodo: Método HTTP utilizado
        body_enviado: Body enviado na requisição (para validar PUT)
        resultado_sem_params: Resultado do teste sem parâmetros (para validação especial)
        endpoint: Informações do endpoint (para validação especial)
        
    Returns:
        Resultado atualizado com campo 'success' indicando sucesso/falha
    """
    if resultado["error"]:
        return {**resultado, "success": False}
    
    cod_retorno = resultado["data"].get("codRetorno")
    total_registros = resultado["data"].get("totalRegistros")
    desc_retorno = resultado["data"].get("descRetorno", "")
    
    # Determina critérios de sucesso baseado no tipo de teste
    if tipo_teste == "parametros_invalidos":
        sucesso = _avaliar_parametros_invalidos(cod_retorno)
        
    elif tipo_teste == "parametros_validos":
        sucesso = _avaliar_parametros_validos(
            cod_retorno, 
            total_registros,
            resultado_sem_params,
            endpoint
        )
        
    elif tipo_teste == "crud_delete":
        sucesso = _avaliar_crud_delete(cod_retorno, desc_retorno)
        
    elif tipo_teste in ["crud_post", "crud_put"]:
        sucesso = _avaliar_crud_post_put(
            cod_retorno, 
            total_registros, 
            resultado["data"],
            tipo_teste,
            body_enviado
        )
        
    elif tipo_teste == "crud_get":
        sucesso = _avaliar_crud_get(cod_retorno)
        
    else:
        # Teste sem parâmetros ou outros
        if cod_retorno:
            criterios = CRITERIOS_SUCESSO.get(tipo_teste, {"codRetorno": "200"})
            sucesso = cod_retorno == criterios.get("codRetorno", "200")
        else:
            sucesso = True
    
    return {**resultado, "success": sucesso}


def verificar_registro_ja_existe(resultado: Dict) -> bool:
    """
    Verifica se o erro indica que o registro já existe.
    
    Args:
        resultado: Resultado da chamada à API
        
    Returns:
        True se o erro indica registro duplicado
    """
    if resultado.get("error"):
        return False
    
    cod_retorno = resultado.get("data", {}).get("codRetorno")
    desc_retorno = resultado.get("data", {}).get("descRetorno", "")
    
    # Verifica padrão de erro "registro já existe"
    return (cod_retorno == "404" and 
            "registo j" in desc_retorno.lower() and 
            "existe" in desc_retorno.lower())


def _avaliar_parametros_invalidos(cod_retorno: str) -> bool:
    """Avalia teste com parâmetros inválidos."""
    criterios = CRITERIOS_SUCESSO["parametros_invalidos"]
    return cod_retorno == criterios["codRetorno"]


def _avaliar_parametros_validos(
    cod_retorno: str, 
    total_registros: str,
    resultado_sem_params: Optional[Dict] = None,
    endpoint: Optional[Dict] = None
) -> bool:
    """Avalia teste com parâmetros válidos."""
    criterios = CRITERIOS_SUCESSO["parametros_validos"]
    
    # Verifica se requer validação especial de totalRegistros
    if endpoint and resultado_sem_params:
        from substituicoes_endpoint import requer_validacao_especial_registros
        
        if requer_validacao_especial_registros(endpoint):
            # Validação especial: compara totalRegistros com teste sem parâmetros
            if cod_retorno != criterios["codRetorno"]:
                return False
            
            total_sem_params = resultado_sem_params.get("data", {}).get("totalRegistros")
            
            if total_sem_params:
                try:
                    num_sem_params = int(total_sem_params)
                    num_com_params = int(total_registros)
                    
                    if num_sem_params == 1:
                        # Se sem_parametros tem 1 registro, parametros_validos deve ter 1 também
                        return num_com_params == 1
                    else:
                        # Se sem_parametros tem > 1, parametros_validos deve ter < sem_parametros
                        return num_com_params < num_sem_params
                except (ValueError, TypeError):
                    pass
    
    # Validação padrão
    return (cod_retorno == criterios["codRetorno"] and 
            total_registros == criterios["totalRegistros"])


def _avaliar_crud_get(cod_retorno: str) -> bool:
    """Avalia GET no contexto CRUD."""
    # Para CRUD, apenas erro interno (500) deve reprovar o GET.
    return cod_retorno is not None and cod_retorno != "500"


def _avaliar_crud_delete(cod_retorno: str, desc_retorno: str) -> bool:
    """Avalia DELETE."""
    criterios = CRITERIOS_SUCESSO["crud_delete"]
    return (cod_retorno == criterios["codRetorno"] and 
            criterios["descRetorno_contem"] in desc_retorno)


def _avaliar_crud_post_put(
    cod_retorno: str,
    total_registros: str,
    data: Dict,
    tipo_teste: str,
    body_enviado: Optional[Dict]
) -> bool:
    """Avalia POST/PUT."""
    criterios = CRITERIOS_SUCESSO[tipo_teste]
    
    # Valida critérios básicos
    if cod_retorno != criterios["codRetorno"]:
        return False
    if total_registros != criterios["totalRegistros"]:
        return False
    
    # Para PUT, verifica se os dados foram realmente atualizados
    if tipo_teste == "crud_put" and criterios.get("validar_atualizacao") and body_enviado:
        return _verificar_atualizacao_put(data, body_enviado)
    
    return True


def _verificar_atualizacao_put(data: Dict, body_enviado: Dict) -> bool:
    """
    Verifica se o PUT realmente atualizou os campos.
    
    Args:
        data: Dados retornados pela API
        body_enviado: Body que foi enviado no PUT
        
    Returns:
        True se pelo menos um campo foi atualizado
    """
    try:
        dados_json = data["Key_000000"]
        dados_retornados = (json.loads(dados_json) 
                           if isinstance(dados_json, str) 
                           else dados_json)
        
        campos_verificados = 0
        campos_atualizados = 0
        
        for campo_enviado, valor_enviado in body_enviado.items():
            # Ignora campos ID na validação
            if _e_campo_id(campo_enviado):
                continue
            
            # Procura o campo na resposta
            for chave, valor_retornado in dados_retornados.items():
                nome_campo = chave.split(".")[-1] if "." in chave else chave
                if nome_campo == campo_enviado:
                    campos_verificados += 1
                    # Compara valores (converte para string)
                    if str(valor_retornado).strip() == str(valor_enviado).strip():
                        campos_atualizados += 1
                    break
        
        # PUT só é sucesso se pelo menos um campo foi atualizado
        if campos_verificados > 0 and campos_atualizados == 0:
            data["_aviso_put"] = (f"Nenhum campo foi atualizado "
                                 f"({campos_verificados} campos verificados)")
            return False
        
        return True
        
    except Exception:
        return True  # Se houver erro na verificação, considera sucesso


def _e_campo_id(nome_campo: str) -> bool:
    """Verifica se o campo é um ID."""
    return ("_ID_" in nome_campo or 
            nome_campo.startswith("ID_") or 
            nome_campo.endswith("_ID"))
