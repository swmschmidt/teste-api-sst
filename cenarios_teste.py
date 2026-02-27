"""
Cenários de teste para endpoints da API.
Responsável por executar diferentes tipos de testes (GET, CRUD).
"""
import time
from typing import Dict, List

from cliente_http import chamar_api
from cliente_swagger import obter_nome_endpoint
from construtor_parametros import (
    construir_parametros_validos,
    construir_parametros_invalidos
)
from avaliador_testes import avaliar_sucesso_teste, verificar_registro_ja_existe
from extrator_dados import (
    extrair_dados_primeiro_registro,
    extrair_id_de_resposta,
    extrair_id_de_parametros,
    atualizar_parametros_com_id
)
from construtor_body import (
    construir_body_de_parametros,
    modificar_body_put,
    aplicar_overrides_body
)
from substituicoes_endpoint import (
    deve_pular_teste_sem_parametros,
    obter_mensagem_skip
)


def testar_endpoint(
    base_url: str,
    endpoint: Dict,
    headers: Dict,
    request_delay: float
) -> List[Dict]:
    """
    Testa um endpoint GET com diferentes cenários.
    
    Args:
        base_url: URL base da API
        endpoint: Informações do endpoint
        headers: Headers HTTP
        request_delay: Delay entre requisições em segundos
        
    Returns:
        Lista de resultados dos testes
    """
    resultados = []
    nome_endpoint = obter_nome_endpoint(endpoint)
    caminho = endpoint["path"]
    
    # Teste sem parâmetros
    if deve_pular_teste_sem_parametros(endpoint):
        print(f"Testando {nome_endpoint} sem parâmetros (pulado - parâmetro obrigatório)...")
        resultado_sem_params = {
            "status_code": None,
            "data": {},
            "error": None,
            "response_time_ms": None,
            "success": True,
            "skipped": True,
            "skip_message": obter_mensagem_skip(endpoint)
        }
        resultados.append({
            "endpoint": nome_endpoint,
            "test_type": "sem_parametros",
            "result": resultado_sem_params
        })
    else:
        print(f"Testando {nome_endpoint} sem parâmetros...")
        resultado_sem_params = chamar_api(base_url, caminho, headers)
        resultado_sem_params = avaliar_sucesso_teste(resultado_sem_params, "sem_parametros")
        resultados.append({
            "endpoint": nome_endpoint,
            "test_type": "sem_parametros",
            "result": resultado_sem_params
        })
        time.sleep(request_delay)
    
    # Teste com parâmetros válidos
    if endpoint["parameters"]:
        print(f"Testando {nome_endpoint} com parâmetros válidos...")
        parametros_validos = construir_parametros_validos(
            endpoint["parameters"],
            resultado_sem_params,
            endpoint,
            metodo="GET"
        )
        resultado = chamar_api(base_url, caminho, headers, parametros_validos)
        resultado = avaliar_sucesso_teste(
            resultado, 
            "parametros_validos",
            resultado_sem_params=resultado_sem_params,
            endpoint=endpoint
        )
        resultados.append({
            "endpoint": nome_endpoint,
            "test_type": "parametros_validos",
            "params": parametros_validos,
            "result": resultado
        })
        time.sleep(request_delay)
        
        # Teste com parâmetros inválidos
        print(f"Testando {nome_endpoint} com parâmetros inválidos...")
        parametros_invalidos = construir_parametros_invalidos(endpoint["parameters"])
        resultado = chamar_api(base_url, caminho, headers, parametros_invalidos)
        resultado = avaliar_sucesso_teste(resultado, "parametros_invalidos")
        resultados.append({
            "endpoint": nome_endpoint,
            "test_type": "parametros_invalidos",
            "params": parametros_invalidos,
            "result": resultado
        })
        time.sleep(request_delay)
    
    return resultados


def testar_endpoint_crud(
    base_url: str,
    endpoint: Dict,
    headers: Dict,
    request_delay: float
) -> List[Dict]:
    """
    Testa um endpoint com sequência completa CRUD.
    Sequência: GET -> POST (novo ID) -> PUT -> DELETE
    
    Args:
        base_url: URL base da API
        endpoint: Informações do endpoint
        headers: Headers HTTP
        request_delay: Delay entre requisições em segundos
        
    Returns:
        Lista de resultados dos testes CRUD
    """
    resultados = []
    nome_endpoint = obter_nome_endpoint(endpoint)
    caminho = endpoint["path"]
    metodos = endpoint.get("methods", {})
    
    print(f"\n{'='*80}")
    print(f"Testando CRUD completo: {nome_endpoint}")
    print(f"Métodos disponíveis: {', '.join(metodos.keys()).upper()}")
    print(f"{'='*80}")
    
    # Passo 1: GET
    resultado_get = _executar_crud_get(
        base_url, caminho, headers, nome_endpoint, resultados
    )
    if not resultado_get or not resultado_get["success"]:
        return resultados
    
    time.sleep(request_delay)
    
    # Extrai dados do primeiro registro
    dados_registro = extrair_dados_primeiro_registro(resultado_get)
    if not dados_registro:
        print("ERRO: Não foi possível extrair dados do registro - PARANDO")
        return resultados
    
    # Extrai parâmetros
    parametros = {}
    if metodos["get"].get("parameters"):
        parametros = construir_parametros_validos(
            metodos["get"]["parameters"],
            resultado_get,
            {"x_objeto_api": endpoint["x_objeto_api"]},
            metodo="GET"
        )
    
    nome_campo_id, _ = extrair_id_de_parametros(parametros)
    
    # Passo 2: POST
    if "post" not in metodos:
        print("\n[2/4] POST não disponível - pulando restante dos testes")
        return resultados
    
    resultado_post_info = _executar_crud_post(
        base_url, caminho, headers, nome_endpoint, metodos,
        dados_registro, parametros, nome_campo_id, request_delay, resultados,
        resultado_get,  # Passa resultado GET para extrair valores dos parâmetros POST
        endpoint  # Passa endpoint para aplicar overrides
    )
    
    if not resultado_post_info or not resultado_post_info["sucesso"]:
        return resultados
    
    id_usado = resultado_post_info["id_usado"]
    parametros_novo_registro = resultado_post_info["parametros"]
    skip_final_delete = resultado_post_info.get("skip_final_delete", False)
    skip_put_delete = resultado_post_info.get("skip_put_delete", False)
    original_record_data = resultado_post_info.get("original_record_data", None)
    
    # Passo 3: PUT
    if "put" in metodos:
        if skip_put_delete:
            print("\n[3/4] PUT - Pulando (já testado na estratégia especial)")
        else:
            _executar_crud_put(
                base_url, caminho, headers, nome_endpoint, metodos,
                dados_registro, parametros_novo_registro, nome_campo_id,
                id_usado, request_delay, resultados, endpoint, original_record_data
            )
    else:
        print("\n[3/4] PUT não disponível - pulando para DELETE")
    
    # Passo 4: DELETE
    if "delete" in metodos:
        # Verifica se deve pular DELETE (caso de recuperação de registro existente ou já testado)
        if skip_put_delete:
            print("\n[4/4] DELETE - Pulando (já testado na estratégia especial)")
        elif skip_final_delete:
            print("\n[4/4] DELETE - Pulando (registro existente foi usado para teste)")
            print(f"   Registro com ID={id_usado} permanece no sistema (era um registro válido)")
        else:
            _executar_crud_delete(
                base_url, caminho, headers, nome_endpoint,
                parametros_novo_registro, id_usado, request_delay, resultados
            )
    else:
        print("\n[4/4] DELETE não disponível - ATENÇÃO: Registro de teste não foi deletado!")
        print(f"   Registro criado com ID={id_usado} permanece no sistema")
    
    print(f"\nSUCESSO: CRUD completo executado para {nome_endpoint}")
    return resultados


def _executar_crud_get(
    base_url: str,
    caminho: str,
    headers: Dict,
    nome_endpoint: str,
    resultados: List[Dict]
) -> Dict:
    """Executa passo GET do CRUD."""
    print("\n[1/4] GET - Obtendo dados válidos...")
    resultado_get = chamar_api(base_url, caminho, headers, metodo="GET")
    resultado_get = avaliar_sucesso_teste(resultado_get, "crud_get")
    
    resultados.append({
        "endpoint": nome_endpoint,
        "test_type": "crud_get",
        "method": "GET",
        "result": resultado_get
    })
    
    if not resultado_get["success"]:
        print(f"ERRO: GET falhou - PARANDO testes para este endpoint")
        print(f"   Erro: {resultado_get.get('error') or 'Resposta inválida'}")
        return None
    
    print(f"✓ GET bem-sucedido (codRetorno: {resultado_get['data'].get('codRetorno')})")
    return resultado_get


def _verificar_registro_existe_com_erro_404(resultado: Dict) -> bool:
    """
    Verifica se o retorno indica que registro já existe mas retorna 404 ou 200.
    Casos possíveis:
    - codRetorno: "404", descRetorno: "Erro = O registo já existe."
    - codRetorno: "200", descRetorno: "O registro já existe."
    (Com ou sem problemas de encoding)
    
    Args:
        resultado: Resultado da chamada à API
        
    Returns:
        True se o erro indica registro existe com código 404/200
    """
    if resultado.get("error"):
        return False
    
    cod_retorno = resultado.get("data", {}).get("codRetorno")
    desc_retorno = resultado.get("data", {}).get("descRetorno", "")
    
    # Normaliza para lowercase para comparação
    desc_lower = desc_retorno.lower()
    
    # Verifica padrões de "registro já existe" ou "registo já existe"
    # Aceita variações: "registo", "registro", "jÃ¡", "já"
    existe_pattern = (
        ("regist" in desc_lower or "registro" in desc_lower) and
        ("existe" in desc_lower) and
        ("j" in desc_lower)  # "já" ou "jÃ¡"
    )
    
    # Retorna True se é 404 ou 200 com mensagem de "já existe"
    return cod_retorno in ["404", "200"] and existe_pattern


def _executar_estrategia_put_delete_post(
    base_url: str,
    caminho: str,
    headers: Dict,
    nome_endpoint: str,
    metodos: Dict,
    resultado_get: Dict,
    resultado_post_original: Dict,
    body_post: Dict,
    parametros_post: Dict,
    nome_campo_id: str,
    request_delay: float,
    endpoint: Dict,
    resultados: List[Dict]
) -> Dict:
    """
    Executa estratégia PUT -> DELETE -> POST quando POST retorna 404/200 com "já existe".
    
    Fluxo:
    1. PUT - atualiza o registro existente com dados de teste
    2. DELETE - tenta deletar o registro
    3. POST - recria o registro (restaura estado original)
    4. Se DELETE falha, restaura valores originais via PUT
    
    Args:
        Parâmetros da API e contexto do teste
        
    Returns:
        Dict com resultado da estratégia ou None se falhou
    """
    print(f"\n   ATENÇÃO: POST retornou erro 404/200 com 'registro já existe'")
    print(f"   Iniciando estratégia especial: PUT -> DELETE -> POST")
    
    # Extrai o ID que foi usado no POST (de body_post ou parametros_post)
    # Este é o ID do override que causou o conflito "já existe"
    id_do_post = None
    
    # Normaliza o nome_campo_id removendo P_ se existir
    nome_campo_id_sem_p = nome_campo_id.replace("P_", "", 1) if nome_campo_id and nome_campo_id.startswith("P_") else nome_campo_id
    
    # Verifica se temos um nome de campo válido
    if not nome_campo_id_sem_p:
        print(f"   AVISO: nome_campo_id não definido, tentando extrair ID de qualquer campo com 'ID' no nome")
        # Tenta encontrar qualquer campo que pareça ser um ID
        for campo, valor in body_post.items():
            if "_ID_" in campo or campo.endswith("_ID") or campo.startswith("ID_"):
                id_do_post = valor
                print(f"   ID encontrado no campo {campo}: {id_do_post}")
                break
    else:
        # Primeiro tenta extrair do body do POST
        for campo, valor in body_post.items():
            nome_campo = campo.split(".")[-1] if "." in campo else campo
            
            # Verifica correspondência direta
            if nome_campo == nome_campo_id or nome_campo == nome_campo_id_sem_p:
                id_do_post = valor
                break
            
            # Remove prefixos como SCO_, DBR_, etc e verifica novamente
            nome_limpo = nome_campo
            for prefixo in ["SCO_", "DBR_", "STD_", "SBR_"]:
                if nome_limpo.startswith(prefixo):
                    nome_limpo = nome_limpo[len(prefixo):]
                    break
            
            # Verifica se o nome limpo corresponde ao campo ID (com ou sem P_)
            nome_campo_id_limpo = nome_campo_id_sem_p
            for prefixo in ["SCO_", "DBR_", "STD_", "SBR_"]:
                if nome_campo_id_limpo and nome_campo_id_limpo.startswith(prefixo):
                    nome_campo_id_limpo = nome_campo_id_limpo[len(prefixo):]
                    break
            
            if nome_limpo == nome_campo_id_limpo:
                id_do_post = valor
                break
        
        # Se não encontrou no body, tenta nos parâmetros
        if not id_do_post and parametros_post:
            id_do_post = parametros_post.get(nome_campo_id) or parametros_post.get(nome_campo_id_sem_p)
    
    if not id_do_post:
        print(f"   ERRO: Não foi possível extrair ID do POST que causou o conflito")
        return None
    
    print(f"   ID do conflito identificado: {id_do_post}")
    
    # Extrai dados do registro existente do GET (para valores de restauração)
    registro_existente = extrair_dados_primeiro_registro(resultado_get)
    if not registro_existente:
        print(f"   ERRO: Não foi possível extrair dados do registro existente")
        return None
    
    # Guarda valores originais para possível restauração
    valores_originais = registro_existente.copy()
    
    # ============================================================
    # PASSO 1: PUT - Atualiza registro existente com dados de teste
    # ============================================================
    print(f"\n   [1/3] PUT - Atualizando registro existente com ID={id_do_post}...")
    
    # Constrói parâmetros PUT
    parametros_put = construir_parametros_validos(
        metodos.get("put", {}).get("parameters", []),
        resultado_get,
        {"x_objeto_api": endpoint.get("x_objeto_api", "")},
        metodo="PUT"
    )
    parametros_put = atualizar_parametros_com_id(parametros_put, nome_campo_id, id_do_post)
    
    # Constrói body PUT modificando os valores do registro existente
    body_put = construir_body_de_parametros(
        metodos["put"]["parameters"],
        registro_existente,
        None  # Não usa ID de teste, mantém ID existente
    )
    body_put = modificar_body_put(body_put)  # Aplica modificações (muda textos para "MODIFICADO")
    body_put = aplicar_overrides_body(body_put, endpoint, "PUT")
    
    resultado_put = chamar_api(
        base_url, caminho, headers,
        params=parametros_put,
        body=body_put,
        metodo="PUT",
        consumes=metodos["put"].get("consumes")
    )
    
    resultado_put = avaliar_sucesso_teste(resultado_put, "crud_put")
    
    if not resultado_put.get("success", False):
        print(f"   ⚠ PUT falhou - continuando com DELETE e POST")
        print(f"   PUT Error: codRetorno={resultado_put.get('data', {}).get('codRetorno')}")
        print(f"   PUT Error: {resultado_put.get('data', {}).get('descRetorno', '')[:100]}...")
    else:
        print(f"   ✓ PUT bem-sucedido")
    
    # Adiciona resultado PUT ao relatório
    resultados.append({
        "endpoint": nome_endpoint,
        "test_type": "crud_put_strategy",
        "method": "PUT",
        "params": parametros_put,
        "body": body_put,
        "result": resultado_put
    })
    
    time.sleep(request_delay)
    
    # ============================================================
    # PASSO 2: DELETE - Tenta deletar o registro
    # ============================================================
    print(f"\n   [2/3] DELETE - Tentando deletar registro...")
    
    parametros_delete = construir_parametros_validos(
        metodos.get("delete", {}).get("parameters", []),
        resultado_get,
        {"x_objeto_api": endpoint.get("x_objeto_api", "")},
        metodo="DELETE"
    )
    parametros_delete = atualizar_parametros_com_id(parametros_delete, nome_campo_id, id_do_post)
    
    resultado_delete = chamar_api(
        base_url, caminho, headers,
        params=parametros_delete,
        metodo="DELETE"
    )
    
    resultado_delete = avaliar_sucesso_teste(resultado_delete, "crud_delete")
    delete_sucesso = resultado_delete.get("success", False)
    
    if not delete_sucesso:
        print(f"   ⚠ DELETE falhou - continuando com POST")
        print(f"   DELETE Error: codRetorno={resultado_delete.get('data', {}).get('codRetorno')}")
        print(f"   DELETE Error: {resultado_delete.get('data', {}).get('descRetorno', '')[:100]}...")
    else:
        print(f"   ✓ DELETE bem-sucedido")
    
    # Adiciona resultado DELETE ao relatório
    resultados.append({
        "endpoint": nome_endpoint,
        "test_type": "crud_delete_strategy",
        "method": "DELETE",
        "params": parametros_delete,
        "result": resultado_delete
    })
    
    time.sleep(request_delay)
    
    # ============================================================
    # PASSO 3: POST - Recria o registro (restaura estado)
    # ============================================================
    print(f"\n   [3/3] POST - Recriando registro (restauração)...")
    
    # Usa os dados originais do registro para restaurar
    body_post_restauracao = construir_body_de_parametros(
        metodos["post"]["parameters"],
        valores_originais,
        None  # Mantém ID original
    )
    body_post_restauracao = aplicar_overrides_body(body_post_restauracao, endpoint, "POST")
    
    resultado_post_final = chamar_api(
        base_url, caminho, headers,
        params=parametros_post,
        body=body_post_restauracao,
        metodo="POST",
        consumes=metodos["post"].get("consumes")
    )
    
    resultado_post_final = avaliar_sucesso_teste(resultado_post_final, "crud_post")
    
    if not resultado_post_final.get("success", False):
        print(f"   ⚠ POST falhou")
        print(f"   POST Error: codRetorno={resultado_post_final.get('data', {}).get('codRetorno')}")
        print(f"   POST Error: {resultado_post_final.get('data', {}).get('descRetorno', '')[:100]}...")
        
        # Adiciona metadados de erro
        if "metadata" not in resultado_post_final:
            resultado_post_final["metadata"] = {}
        resultado_post_final["metadata"]["strategy_completed"] = True
        resultado_post_final["metadata"]["strategy_type"] = "PUT->DELETE->POST"
        resultado_post_final["metadata"]["put_success"] = resultado_put.get("success", False)
        resultado_post_final["metadata"]["delete_success"] = delete_sucesso
        resultado_post_final["metadata"]["post_success"] = False
        
        # Se DELETE falhou mas POST também, indica que não houve mudança
        if not delete_sucesso:
            print(f"   Conclusão: DELETE não funcionou, registro permanece inalterado")
            resultado_post_final["metadata"]["no_data_loss"] = True
        else:
            print(f"   ERRO CRÍTICO: DELETE bem-sucedido mas POST falhou!")
            print(f"   Registro foi deletado mas não pôde ser recriado!")
            resultado_post_final["metadata"]["critical_error"] = True
            resultado_post_final["metadata"]["deleted_record"] = valores_originais
        
        return None
    
    print(f"   ✓ POST bem-sucedido - estado original restaurado")
    print(f"   ✓ Estratégia PUT->DELETE->POST concluída!")
    
    # Adiciona resultado POST ao relatório
    resultados.append({
        "endpoint": nome_endpoint,
        "test_type": "crud_post_strategy",
        "method": "POST",
        "params": parametros_post,
        "body": body_post_restauracao,
        "result": resultado_post_final
    })
    
    # Adiciona metadados de sucesso
    if "metadata" not in resultado_post_final:
        resultado_post_final["metadata"] = {}
    resultado_post_final["metadata"]["special_strategy_used"] = True
    resultado_post_final["metadata"]["strategy_type"] = "PUT->DELETE->POST"
    resultado_post_final["metadata"]["strategy_reason"] = "POST retornou 404/200 com 'registro já existe'"
    resultado_post_final["metadata"]["put_tested"] = True
    resultado_post_final["metadata"]["put_success"] = resultado_put.get("success", False)
    resultado_post_final["metadata"]["delete_tested"] = True
    resultado_post_final["metadata"]["delete_success"] = delete_sucesso
    resultado_post_final["metadata"]["post_success"] = True
    resultado_post_final["metadata"]["all_operations_tested"] = True
    
    return {
        "sucesso": True,
        "id_usado": id_do_post,
        "parametros": parametros_put,
        "body_post": body_post_restauracao,
        "resultado_post": resultado_post_final,
        "skip_put_delete": True,  # PUT e DELETE já foram testados
        "original_record_data": valores_originais
    }


def _executar_crud_post(
    base_url: str,
    caminho: str,
    headers: Dict,
    nome_endpoint: str,
    metodos: Dict,
    dados_registro: Dict,
    parametros: Dict,
    nome_campo_id: str,
    request_delay: float,
    resultados: List[Dict],
    resultado_get: Dict = None,
    endpoint: Dict = None
) -> Dict:
    """Executa passo POST do CRUD."""
    print(f"\n[2/4] POST - Criando novo registro com ID de teste...")
    
    # Verifica se há override configurado para este endpoint
    from overrides_endpoints import OVERRIDES_ENDPOINTS
    x_objeto_api = endpoint.get("x_objeto_api", "")
    tem_override_post = (x_objeto_api in OVERRIDES_ENDPOINTS and 
                         "POST" in OVERRIDES_ENDPOINTS[x_objeto_api].get("substituicoes", {}))
    
    # Se há override, usa apenas 1 tentativa. Caso contrário, tenta múltiplos IDs
    ids_teste = [None] if tem_override_post else [987154874, 23942835, 456789123]
    resultado_post = None
    body_post = None
    id_usado = None
    parametros_post = {}
    parametros_novo_registro = None
    skip_put_delete_no_final = False
    original_record_data = None
    
    for id_teste in ids_teste:
        if id_teste is not None:
            print(f"   Tentando POST com ID={id_teste}...")
        else:
            print(f"   Executando POST com valores do override...")
            
        tamanho_maximo_funcionou = None  # Rastreia tamanho máximo de ID que funcionou
        body_post = construir_body_de_parametros(
            metodos["post"]["parameters"],
            dados_registro,
            id_teste
        )
        # Aplica overrides configurados ao body
        body_post = aplicar_overrides_body(body_post, endpoint, "POST")
        
        # Constrói parâmetros de query específicos do POST usando dados do GET
        parametros_post = construir_parametros_validos(
            metodos["post"].get("parameters", []),
            resultado_get,  # Usa resultado GET para extrair valores
            {"x_objeto_api": endpoint.get("x_objeto_api", "")},
            metodo="POST"
        )
        # Se POST tem um campo ID em query, atualiza com o ID de teste (exceto se id_teste é None)
        post_query_params = [p.get("name") for p in metodos["post"].get("parameters", []) if p.get("in") == "query"]
        if nome_campo_id in post_query_params and id_teste is not None:
            parametros_post = atualizar_parametros_com_id(parametros_post, nome_campo_id, id_teste)
        
        resultado_post = chamar_api(
            base_url, caminho, headers,
            params=parametros_post,  # Agora só contém parâmetros definidos no POST
            body=body_post,
            metodo="POST",
            consumes=metodos["post"].get("consumes")
        )
        
        # Se há override, não tenta múltiplos IDs - aceita o resultado direto
        if tem_override_post:
            # ANTES de avaliar como sucesso/falha, verifica se é o caso especial 404/200 com "já existe"
            if _verificar_registro_existe_com_erro_404(resultado_post):
                print(f"   Detectado caso especial: erro 404/200 com 'registro já existe'")
                
                # Verifica se temos PUT e DELETE disponíveis
                if "put" not in metodos or "delete" not in metodos:
                    print(f"   AVISO: Não há PUT ou DELETE disponível para estratégia especial")
                    # Avalia como falha e sai do loop
                    resultado_post = avaliar_sucesso_teste(resultado_post, "crud_post")
                    break
                
                # Executa estratégia PUT -> DELETE -> POST
                resultado_estrategia = _executar_estrategia_put_delete_post(
                    base_url, caminho, headers, nome_endpoint, metodos,
                    resultado_get, resultado_post, body_post, parametros_post,
                    nome_campo_id, request_delay, endpoint, resultados
                )
                
                if resultado_estrategia:
                    # Estratégia bem-sucedida!
                    print(f"   ✓ Estratégia especial concluída com sucesso")
                    resultado_post = resultado_estrategia["resultado_post"]
                    id_usado = resultado_estrategia["id_usado"]
                    parametros_novo_registro = resultado_estrategia["parametros"]
                    body_post = resultado_estrategia["body_post"]
                    
                    # Marca que PUT e DELETE já foram testados
                    skip_put_delete_no_final = resultado_estrategia.get("skip_put_delete", False)
                    original_record_data = resultado_estrategia.get("original_record_data")
                    
                    # Sai do loop
                    break
                else:
                    # Estratégia falhou, avalia como falha
                    print(f"   Estratégia especial falhou")
                    resultado_post = avaliar_sucesso_teste(resultado_post, "crud_post")
                    break
            
            # Se não é o caso especial, avalia o resultado normalmente
            resultado_post = avaliar_sucesso_teste(resultado_post, "crud_post")
            
            # Extrai o ID usado do body ou resposta
            id_usado = extrair_id_de_resposta(resultado_post, nome_campo_id)
            if not id_usado:
                # Se não conseguiu extrair da resposta, tenta pegar do body
                # (para casos com múltiplos IDs como R029)
                for campo in body_post:
                    if "_ID_" in campo or campo.endswith("_ID"):
                        id_usado = body_post[campo]
                        break
                if not id_usado:
                    id_usado = "override"  # Fallback genérico
            break
        
        # Lógica normal para quando NÃO há override:
        # Verifica se deu erro de registro já existe
        if verificar_registro_ja_existe(resultado_post):
            print(f"   Registro com ID={id_teste} já existe, tentando próximo ID...")
            continue
        
        # NOVO: Verifica se é erro especial 404/200 com "registro já existe"
        # Neste caso, executa estratégia PUT -> DELETE -> POST
        if _verificar_registro_existe_com_erro_404(resultado_post):
            print(f"   Detectado caso especial: erro 404/200 com 'registro já existe'")
            
            # Verifica se temos PUT e DELETE disponíveis
            if "put" not in metodos or "delete" not in metodos:
                print(f"   AVISO: Não há PUT ou DELETE disponível para estratégia especial")
                # Avalia como falha e continua
                resultado_post = avaliar_sucesso_teste(resultado_post, "crud_post")
                break
            
            # Executa estratégia PUT -> DELETE -> POST
            resultado_estrategia = _executar_estrategia_put_delete_post(
                base_url, caminho, headers, nome_endpoint, metodos,
                resultado_get, resultado_post, body_post, parametros_post,
                nome_campo_id, request_delay, endpoint, resultados
            )
            
            if resultado_estrategia:
                # Estratégia bem-sucedida!
                print(f"   ✓ Estratégia especial concluída com sucesso")
                resultado_post = resultado_estrategia["resultado_post"]
                id_usado = resultado_estrategia["id_usado"]
                parametros_novo_registro = resultado_estrategia["parametros"]
                body_post = resultado_estrategia["body_post"]
                
                # Marca que PUT e DELETE já foram testados
                skip_put_delete_no_final = resultado_estrategia.get("skip_put_delete", False)
                original_record_data = resultado_estrategia.get("original_record_data")
                
                # Sai do loop de tentativas de ID
                break
            else:
                # Estratégia falhou, continua com próximo ID
                print(f"   Estratégia especial falhou, tentando próximo ID...")
                continue
        
        # DESATIVADO: Estratégia de recuperação seletiva - desativada por ser arriscada
        # # Verifica se é erro que justifica tentar recuperação
        # desc_retorno = resultado_post.get("data", {}).get("descRetorno", "")
        # cod_retorno = resultado_post.get("data", {}).get("codRetorno", "")
        # 
        # # Situações que ativam estratégia de recuperação:
        # # 1. Erro de dados inválidos
        # # 2. Erro 404 ou 500 (pode ser rejeição de dados de teste)
        # # 3. Qualquer outro erro que não seja duplicação
        # deve_tentar_recuperacao = (
        #     ("Erro = Dados n" in desc_retorno and "o v" in desc_retorno and "lidos" in desc_retorno) or
        #     cod_retorno in ["404", "500", "400"] or
        #     (cod_retorno != "200" and not verificar_registro_ja_existe(resultado_post))
        # )
        # 
        # if deve_tentar_recuperacao:
        #     print(f"   AVISO: POST falhou (codRetorno={cod_retorno})")
        #     print(f"   Iniciando estratégia de recuperação: DELETE registro existente + POST com dados válidos")
        #     
        #     # Extrai um registro válido do GET
        #     registro_para_deletar = extrair_dados_primeiro_registro(resultado_get)
        #     if not registro_para_deletar:
        #         print(f"   ERRO: Não foi possível extrair registro válido do GET - continuando com próximo ID")
        #         continue
        #     
        #     # Extrai o ID do registro a deletar
        #     id_para_deletar = None
        #     for chave, valor in registro_para_deletar.items():
        #         nome_campo = chave.split(".")[-1] if "." in chave else chave
        #         if nome_campo == nome_campo_id or (nome_campo_id and nome_campo == nome_campo_id.replace("P_", "", 1)):
        #             id_para_deletar = valor
        #             break
        #     
        #     if not id_para_deletar:
        #         print(f"   ERRO: Não foi possível extrair ID do registro para deletar")
        #         continue
        #     
        #     print(f"   Deletando registro existente com ID={id_para_deletar}...")
        #     
        #     # Constrói parâmetros para DELETE
        #     parametros_delete_recuperacao = construir_parametros_validos(
        #         metodos.get("delete", {}).get("parameters", []),
        #         resultado_get,
        #         {"x_objeto_api": endpoint.get("x_objeto_api", "")},
        #         metodo="DELETE"
        #     )
        #     parametros_delete_recuperacao = atualizar_parametros_com_id(
        #         parametros_delete_recuperacao, 
        #         nome_campo_id, 
        #         id_para_deletar
        #     )
        #     
        #     resultado_delete_recuperacao = chamar_api(
        #         base_url, caminho, headers,
        #         params=parametros_delete_recuperacao,
        #         metodo="DELETE"
        #     )
        #     
        #     if not resultado_delete_recuperacao.get("data", {}).get("codRetorno") == "200":
        #         print(f"   ERRO: DELETE de recuperação falhou")
        #         continue
        #     
        #     print(f"   ✓ DELETE bem-sucedido, tentando POST com dados válidos...")
        #     
        #     # Reconstrói body com dados do registro deletado (sem usar ID de teste)
        #     body_post = construir_body_de_parametros(
        #         metodos["post"]["parameters"],
        #         registro_para_deletar,
        #         None  # Não usa ID de teste, mantém os dados originais
        #     )
        #     
        #     # Aplica overrides se houver
        #     body_post = aplicar_overrides_body(body_post, endpoint, "POST")
        #     
        #     # Reconstrói parâmetros POST
        #     parametros_post = construir_parametros_validos(
        #         metodos["post"].get("parameters", []),
        #         resultado_get,
        #         {"x_objeto_api": endpoint.get("x_objeto_api", "")},
        #         metodo="POST"
        #     )
        #     
        #     # Tenta POST novamente
        #     resultado_post = chamar_api(
        #         base_url, caminho, headers,
        #         params=parametros_post,
        #         body=body_post,
        #         metodo="POST",
        #         consumes=metodos["post"].get("consumes")
        #     )
        #     
        #     # Avalia resultado do POST de recuperação
        #     resultado_post = avaliar_sucesso_teste(resultado_post, "crud_post")
        #     
        #     if not resultado_post.get("success", False):
        #         # Verifica se o erro é "registro já existe" - indica que DELETE não teve efeito
        #         desc_retorno_post = resultado_post.get("data", {}).get("descRetorno", "")
        #         if "Erro = O registo j" in desc_retorno_post and " existe" in desc_retorno_post:
        #             print(f"   AVISO: POST falhou com 'registro já existe' - DELETE não teve efeito")
        #             print(f"   O registro não foi realmente deletado, continuando com próximo ID...")
        #             
        #             # Adiciona informação de que DELETE falhou
        #             if "metadata" not in resultado_post:
        #                 resultado_post["metadata"] = {}
        #             resultado_post["metadata"]["delete_tested"] = True
        #             resultado_post["metadata"]["delete_success"] = False
        #             resultado_post["metadata"]["delete_note"] = "DELETE não teve efeito"
        #             
        #             # Continua para próximo ID sem interromper
        #             continue
        #         
        #         # Se não é erro de "já existe", é um erro crítico de perda de dados
        #         print(f"   ERRO CRÍTICO: DELETE bem-sucedido mas POST de recuperação falhou!")
        #         print(f"   ATENÇÃO: Registro deletado NÃO foi recriado!")
        #         print(f"   Dados do registro deletado:")
        #         import json
        #         print(f"   {json.dumps(registro_para_deletar, indent=2, ensure_ascii=False)}")
        #         
        #         # Adiciona informação de recuperação falhada ao resultado
        #         if "metadata" not in resultado_post:
        #             resultado_post["metadata"] = {}
        #         resultado_post["metadata"]["recovery_failed"] = True
        #         resultado_post["metadata"]["deleted_record"] = registro_para_deletar
        #         resultado_post["metadata"]["recovery_note"] = "Registro foi deletado mas não pôde ser recriado. Dados do registro deletado estão salvos em 'deleted_record'."
        #         resultado_post["metadata"]["delete_tested"] = True
        #         resultado_post["metadata"]["delete_success"] = True
        #         resultado_post["metadata"]["delete_note"] = "DELETE foi testado com sucesso (fora de ordem) durante estratégia de recuperação"
        #         
        #         id_usado = id_para_deletar  # Marca com ID que foi deletado
        #         # Marca que não deve fazer DELETE no final (já foi deletado)
        #         resultado_post["metadata"]["skip_final_delete"] = True
        #         
        #         # AVISO: Interrupção crítica desativada temporariamente
        #         print("\n" + "="*80)
        #         print("AVISO CRÍTICO: Teste causou perda de dados")
        #         print("Continuando execução dos testes")
        #         print("="*80)
        #         
        #         # RuntimeError temporariamente suprimido
        #         # raise RuntimeError(
        #         #     f"Erro crítico em {nome_endpoint}: DELETE bem-sucedido mas POST de recuperação falhou. "
        #         #     f"Registro com ID={id_para_deletar} foi deletado mas não pôde ser recriado."
        #         # )
        #         
        #         # Continua para próximo ID
        #         continue
        #     
        #     print(f"   ✓ POST de recuperação bem-sucedido!")
        #     id_usado = id_para_deletar
        #     
        #     # Marca que este registro não deve ser deletado no final (era um registro existente)
        #     if "metadata" not in resultado_post:
        #         resultado_post["metadata"] = {}
        #     resultado_post["metadata"]["skip_final_delete"] = True
        #     resultado_post["metadata"]["recovery_success"] = True
        #     resultado_post["metadata"]["recovery_note"] = "Registro existente foi deletado e recriado para teste PUT"
        #     resultado_post["metadata"]["original_record_data"] = registro_para_deletar  # Guarda dados originais para restauração
        #     break
        
        # Extrai informações de retorno para verificações
        desc_retorno = resultado_post.get("data", {}).get("descRetorno", "")
        cod_retorno = resultado_post.get("data", {}).get("codRetorno", "")
        
        # Verifica se é erro de ID muito longo (ORA-01438)
        if "ORA-01438" in desc_retorno:
            print(f"   ID={id_teste} muito longo para o banco, truncando...")
            # Tenta truncar o ID até funcionar
            id_truncado = id_teste
            tamanho_id_original = len(str(id_teste))
            tamanho_maximo_funcionou = None
            
            while len(str(id_truncado)) > 0:
                id_str = str(id_truncado)[:-1]  # Remove último dígito
                if not id_str or id_str == "":  # Se ficou vazio, para
                    print(f"   Falha: ID truncado até ficar vazio - não é possível continuar")
                    break
                
                id_truncado = int(id_str)
                if id_truncado == 0:  # Se chegou a 0, para
                    print(f"   Falha: ID truncado até 0 - não é possível continuar")
                    break
                    
                print(f"   Tentando com ID truncado={id_truncado}...")
                
                # Reconstrói body e parâmetros com ID truncado
                body_post = construir_body_de_parametros(
                    metodos["post"]["parameters"],
                    dados_registro,
                    id_truncado
                )
                # Aplica overrides configurados ao body
                body_post = aplicar_overrides_body(body_post, endpoint, "POST")
                
                parametros_post = construir_parametros_validos(
                    metodos["post"].get("parameters", []),
                    resultado_get,
                    {"x_objeto_api": endpoint.get("x_objeto_api", "")},
                    metodo="POST"
                )
                if nome_campo_id in post_query_params:
                    parametros_post = atualizar_parametros_com_id(parametros_post, nome_campo_id, id_truncado)
                
                resultado_post = chamar_api(
                    base_url, caminho, headers,
                    params=parametros_post,
                    body=body_post,
                    metodo="POST",
                    consumes=metodos["post"].get("consumes")
                )
                
                # Se ainda tem erro de ID longo, continua truncando
                desc_retorno = resultado_post.get("data", {}).get("descRetorno", "")
                if "ORA-01438" in desc_retorno:
                    continue
                
                # Se é erro de duplicação, sai do loop de truncamento
                if verificar_registro_ja_existe(resultado_post):
                    print(f"   Registro com ID={id_truncado} já existe")
                    break
                
                # Se não tem mais erro de tamanho, usa este ID
                id_teste = id_truncado
                tamanho_maximo_funcionou = len(str(id_truncado))
                print(f"   SUCESSO: ID truncado para {id_truncado} funciona!")
                print(f"   OBSERVAÇÃO: Este endpoint aceita IDs com até {tamanho_maximo_funcionou} dígitos")
                break
            
            # Se ainda tem erro depois de truncar completamente
            if "ORA-01438" in resultado_post.get("data", {}).get("descRetorno", ""):
                print(f"   Falha: Não foi possível encontrar ID que funcione")
                continue
            
            # Se é erro de duplicação após truncamento, tenta próximo ID da lista
            if verificar_registro_ja_existe(resultado_post):
                continue
        
        # Se não é erro de duplicação ou tamanho, avalia sucesso e para (só para não-override)
        resultado_post = avaliar_sucesso_teste(resultado_post, "crud_post")
        
        # Adiciona informação sobre limitação de tamanho de ID se foi truncado
        if tamanho_maximo_funcionou:
            if "metadata" not in resultado_post:
                resultado_post["metadata"] = {}
            resultado_post["metadata"]["max_id_length"] = tamanho_maximo_funcionou
            resultado_post["metadata"]["id_truncation_note"] = f"Gera erro ORA-01438 caso o ID seja maior que {tamanho_maximo_funcionou} dígitos"
        
        # Usa o id_teste para casos sem override
        id_usado = id_teste
        break
    
    # Se todos os IDs falharam (existem ou erro), tenta estratégia de recuperação como última tentativa
    # DESATIVADO: Estratégia de última tentativa (DELETE + POST) - desativada por ser muito arriscada
    # if resultado_post and id_usado is None and not tem_override_post:
    #     print(f"\n   AVISO: Todas as tentativas de POST com IDs de teste falharam")
    #     print(f"   Última tentativa: Estratégia de recuperação (DELETE + POST)")
    #     
    #     # Extrai um registro válido do GET
    #     registro_para_deletar = extrair_dados_primeiro_registro(resultado_get)
    #     if registro_para_deletar and "delete" in metodos:
    #         # Extrai o ID do registro a deletar
    #         id_para_deletar = None
    #         for chave, valor in registro_para_deletar.items():
    #             nome_campo = chave.split(".")[-1] if "." in chave else chave
    #             if nome_campo == nome_campo_id or (nome_campo_id and nome_campo == nome_campo_id.replace("P_", "", 1)):
    #                 id_para_deletar = valor
    #                 break
    #         
    #         if id_para_deletar:
    #             print(f"   Deletando registro existente com ID={id_para_deletar} para teste...")
    #             
    #             # Constrói parâmetros para DELETE
    #             parametros_delete_final = construir_parametros_validos(
    #                 metodos.get("delete", {}).get("parameters", []),
    #                 resultado_get,
    #                 {"x_objeto_api": endpoint.get("x_objeto_api", "")},
    #                 metodo="DELETE"
    #             )
    #             parametros_delete_final = atualizar_parametros_com_id(
    #                 parametros_delete_final, 
    #                 nome_campo_id, 
    #                 id_para_deletar
    #             )
    #             
    #             resultado_delete_final = chamar_api(
    #                 base_url, caminho, headers,
    #                 params=parametros_delete_final,
    #                 metodo="DELETE"
    #             )
    #             
    #             if resultado_delete_final.get("data", {}).get("codRetorno") == "200":
    #                 print(f"   ✓ DELETE bem-sucedido, tentando POST com dados válidos...")
    #                 
    #                 # Reconstrói body com dados do registro deletado
    #                 body_post = construir_body_de_parametros(
    #                     metodos["post"]["parameters"],
    #                     registro_para_deletar,
    #                     None
    #                 )
    #                 body_post = aplicar_overrides_body(body_post, endpoint, "POST")
    #                 
    #                 parametros_post = construir_parametros_validos(
    #                     metodos["post"].get("parameters", []),
    #                     resultado_get,
    #                     {"x_objeto_api": endpoint.get("x_objeto_api", "")},
    #                     metodo="POST"
    #                 )
    #                 
    #                 # Tenta POST novamente
    #                 resultado_post = chamar_api(
    #                     base_url, caminho, headers,
    #                     params=parametros_post,
    #                     body=body_post,
    #                     metodo="POST",
    #                     consumes=metodos["post"].get("consumes")
    #                 )
    #                 resultado_post = avaliar_sucesso_teste(resultado_post, "crud_post")
    #                 
    #                 if resultado_post.get("success", False):
    #                     print(f"   ✓ POST de recuperação bem-sucedido!")
    #                     id_usado = id_para_deletar
    #                     
    #                     # Marca que este registro não deve ser deletado no final
    #                     if "metadata" not in resultado_post:
    #                         resultado_post["metadata"] = {}
    #                     resultado_post["metadata"]["skip_final_delete"] = True
    #                     resultado_post["metadata"]["recovery_success"] = True
    #                     resultado_post["metadata"]["recovery_note"] = "Registro existente foi deletado e recriado para teste (última tentativa)"
    #                     resultado_post["metadata"]["delete_tested"] = True
    #                     resultado_post["metadata"]["delete_success"] = True
    #                     resultado_post["metadata"]["original_record_data"] = registro_para_deletar  # Guarda dados originais para restauração
    #                 else:
    #                     # Verifica se o erro é "registro já existe" - indica que DELETE não teve efeito
    #                     desc_retorno_post_final = resultado_post.get("data", {}).get("descRetorno", "")
    #                     if "Erro = O registo j" in desc_retorno_post_final and " existe" in desc_retorno_post_final:
    #                         print(f"   AVISO: POST falhou com 'registro já existe' - DELETE não teve efeito")
    #                         print(f"   O registro não foi realmente deletado")
    #                         
    #                         # Adiciona informação de que DELETE falhou
    #                         if "metadata" not in resultado_post:
    #                             resultado_post["metadata"] = {}
    #                         resultado_post["metadata"]["delete_tested"] = True
    #                         resultado_post["metadata"]["delete_success"] = False
    #                         resultado_post["metadata"]["delete_note"] = "DELETE não teve efeito"
    #                         # NÃO marca como recovery_failed pois não houve perda de dados
    #                     else:
    #                         print(f"   ERRO: POST de recuperação falhou - registro foi deletado e não pôde ser recriado")
    #                         if "metadata" not in resultado_post:
    #                             resultado_post["metadata"] = {}
    #                         resultado_post["metadata"]["recovery_failed"] = True
    #                         resultado_post["metadata"]["deleted_record"] = registro_para_deletar
    #             else:
    #                 print(f"   ERRO: DELETE de recuperação falhou")
        
        # Se ainda falhou após todas as tentativas
        if id_usado is None:
            print(f"FALHA: Todas as estratégias de POST falharam (IDs de teste e recuperação)")
            if not resultado_post or not isinstance(resultado_post, dict):
                resultado_post = {
                    "success": False,
                    "error": "Todas as tentativas de POST falharam (IDs de teste já existem e estratégia de recuperação não funcionou)",
                    "data": {},
                    "status_code": None,
                    "response_time_ms": None
                }
    
    resultados.append({
        "endpoint": nome_endpoint,
        "test_type": "crud_post",
        "method": "POST",
        "params": parametros_post,
        "body": body_post,
        "result": resultado_post
    })
    
    if not resultado_post or not resultado_post.get("success", False):
        print(f"ERRO: POST falhou - PARANDO testes para este endpoint")
        if resultado_post and "data" in resultado_post:
            print(f"   codRetorno: {resultado_post['data'].get('codRetorno')}")
            print(f"   descRetorno: {resultado_post['data'].get('descRetorno')}")
        return None
    
    print(f"SUCESSO: POST bem-sucedido com ID={id_usado}")
    time.sleep(request_delay)
    
    # Extrai o ID real que foi salvo
    id_salvo = extrair_id_de_resposta(resultado_post, nome_campo_id)
    if id_salvo and str(id_salvo) != str(id_usado):
        print(f"   ATENÇÃO: ID foi modificado pela API: {id_usado} -> {id_salvo}")
        id_usado = id_salvo
    
    # Constrói parâmetros para PUT a partir da especificação PUT (não reusar GET)
    # Se a estratégia especial foi usada, parametros_novo_registro já foi definido
    if parametros_novo_registro is None:
        parametros_novo_registro = construir_parametros_validos(
            metodos.get("put", {}).get("parameters", []),
            resultado_get,
            {"x_objeto_api": endpoint.get("x_objeto_api", "")},
            metodo="PUT"
        )
        # Atualiza com o ID real que foi salvo
        parametros_novo_registro = atualizar_parametros_com_id(parametros_novo_registro, nome_campo_id, id_usado)
    
    # Extrai flags de skip e dados originais se presente
    # Se skip_put_delete_no_final já foi definido pela estratégia especial, usa esse valor
    skip_final_delete = resultado_post.get("metadata", {}).get("skip_final_delete", False)
    skip_put_delete = skip_put_delete_no_final or resultado_post.get("metadata", {}).get("all_operations_tested", False)
    if original_record_data is None:
        original_record_data = resultado_post.get("metadata", {}).get("original_record_data", None)
    
    return {
        "sucesso": True,
        "id_usado": id_usado,
        "parametros": parametros_novo_registro,
        "skip_final_delete": skip_final_delete,
        "skip_put_delete": skip_put_delete,
        "original_record_data": original_record_data
    }


def _executar_crud_put(
    base_url: str,
    caminho: str,
    headers: Dict,
    nome_endpoint: str,
    metodos: Dict,
    dados_registro: Dict,
    parametros_novo_registro: Dict,
    nome_campo_id: str,
    id_usado: int,
    request_delay: float,
    resultados: List[Dict],
    endpoint: Dict,
    original_record_data: Dict = None
):
    """Executa passo PUT do CRUD."""
    print(f"\n[3/4] PUT - Modificando registro...")
    
    # Verifica se há override configurado para este endpoint
    from overrides_endpoints import OVERRIDES_ENDPOINTS
    x_objeto_api = endpoint.get("x_objeto_api", "")
    tem_override_put = (x_objeto_api in OVERRIDES_ENDPOINTS and 
                        "PUT" in OVERRIDES_ENDPOINTS[x_objeto_api].get("substituicoes", {}))
    
    body_put_original = construir_body_de_parametros(
        metodos["put"]["parameters"],
        dados_registro,
        id_usado
    )
    body_put_modificado = modificar_body_put(body_put_original)
    
    # Aplica overrides configurados ao body PUT (substitui completamente se houver override)
    body_put_modificado = aplicar_overrides_body(body_put_modificado, endpoint, "PUT")
    
    # Só inclui o ID no body se NÃO houver override (override já tem os campos necessários)
    if not tem_override_put:
        nome_campo_body = nome_campo_id.replace("P_", "", 1) if nome_campo_id.startswith("P_") else nome_campo_id
        body_put_modificado[nome_campo_body] = id_usado
    
    resultado_put_mod = chamar_api(
        base_url, caminho, headers,
        params=parametros_novo_registro,
        body=body_put_modificado,
        metodo="PUT",
        consumes=metodos["put"].get("consumes")
    )
    resultado_put_mod = avaliar_sucesso_teste(
        resultado_put_mod,
        "crud_put",
        body_enviado=body_put_modificado
    )
    
    resultados.append({
        "endpoint": nome_endpoint,
        "test_type": "crud_put_modificar",
        "method": "PUT",
        "params": parametros_novo_registro,
        "body": body_put_modificado,
        "result": resultado_put_mod
    })
    
    if not resultado_put_mod["success"]:
        print(f"ERRO: PUT falhou - continuando para DELETE para limpar")
        print(f"   codRetorno: {resultado_put_mod['data'].get('codRetorno')}")
        print(f"   descRetorno: {resultado_put_mod['data'].get('descRetorno')}")
        if "_aviso_put" in resultado_put_mod["data"]:
            print(f"   Motivo: {resultado_put_mod['data']['_aviso_put']}")
    else:
        print(f"SUCESSO: PUT bem-sucedido")
        time.sleep(request_delay)
        
        # Se há dados originais (estratégia de recuperação), restaura valores originais
        if original_record_data:
            print(f"\n[3.5/4] PUT RESTAURAÇÃO - Restaurando valores originais do registro...")
            
            # Constrói body com dados originais
            body_put_restauracao = construir_body_de_parametros(
                metodos["put"]["parameters"],
                original_record_data,
                id_usado
            )
            
            # Aplica overrides se houver (mantém consistência)
            body_put_restauracao = aplicar_overrides_body(body_put_restauracao, endpoint, "PUT")
            
            # Adiciona o ID se necessário
            if not tem_override_put:
                nome_campo_body = nome_campo_id.replace("P_", "", 1) if nome_campo_id.startswith("P_") else nome_campo_id
                body_put_restauracao[nome_campo_body] = id_usado
            
            resultado_put_restauracao = chamar_api(
                base_url, caminho, headers,
                params=parametros_novo_registro,
                body=body_put_restauracao,
                metodo="PUT",
                consumes=metodos["put"].get("consumes")
            )
            resultado_put_restauracao = avaliar_sucesso_teste(
                resultado_put_restauracao,
                "crud_put",
                body_enviado=body_put_restauracao
            )
            
            resultados.append({
                "endpoint": nome_endpoint,
                "test_type": "crud_put_restauracao",
                "method": "PUT",
                "params": parametros_novo_registro,
                "body": body_put_restauracao,
                "result": resultado_put_restauracao
            })
            
            if not resultado_put_restauracao["success"]:
                print(f"AVISO: PUT de restauração falhou - registro não voltou ao estado original")
                print(f"   codRetorno: {resultado_put_restauracao['data'].get('codRetorno')}")
                print(f"   descRetorno: {resultado_put_restauracao['data'].get('descRetorno')}")
            else:
                print(f"✓ Valores originais restaurados com sucesso")
                time.sleep(request_delay)


def _executar_crud_delete(
    base_url: str,
    caminho: str,
    headers: Dict,
    nome_endpoint: str,
    parametros_novo_registro: Dict,
    id_usado: int,
    request_delay: float,
    resultados: List[Dict]
):
    """Executa passo DELETE do CRUD."""
    print(f"\n[4/4] DELETE - Deletando registro de teste...")
    
    resultado_delete = chamar_api(
        base_url, caminho, headers,
        params=parametros_novo_registro,
        metodo="DELETE"
    )
    resultado_delete = avaliar_sucesso_teste(resultado_delete, "crud_delete")
    
    resultados.append({
        "endpoint": nome_endpoint,
        "test_type": "crud_delete",
        "method": "DELETE",
        "params": parametros_novo_registro,
        "result": resultado_delete
    })
    
    if not resultado_delete["success"]:
        print(f"ERRO: DELETE falhou - ATENÇÃO: Registro de teste não foi deletado!")
        print(f"   Registro com ID={id_usado} permanece no sistema")
        print(f"   codRetorno: {resultado_delete['data'].get('codRetorno')}")
        print(f"   descRetorno: {resultado_delete['data'].get('descRetorno')}")
    else:
        print(f"SUCESSO: DELETE bem-sucedido")
        time.sleep(request_delay)
