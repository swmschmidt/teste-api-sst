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





def resolver_parametros(parametros: List, spec: Dict) -> List[Dict]:
    """Resolve referências de parâmetros ($ref) no Swagger spec"""
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
    """Extrai todos os endpoints GET da especificação"""
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
    """Extrai todos os endpoints com todos os métodos HTTP disponíveis"""
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
    """Retorna o nome do endpoint no formato especificado"""
    return f"{endpoint['x_objeto_api']} - {endpoint['x_caminho']}"


def chamar_api(base_url: str, caminho: str, headers: Dict, params: Dict = None, metodo: str = "GET", body: Dict = None, consumes: List[str] = None) -> Dict:
    """Realiza chamada à API e retorna resposta com metadados
    
    Args:
        consumes: Lista de content types aceitos (ex: ["multipart/form-data"])
    """
    url = f"{base_url}{caminho}"
    try:
        inicio_tempo = time.time()
        
        if metodo.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif metodo.upper() == "POST":
            # Verifica o tipo de encoding baseado no consumes
            if consumes and "multipart/form-data" in consumes:
                # Para multipart/form-data, usa files= (mesmo para campos não-arquivo)
                files = {k: (None, v) for k, v in body.items()} if body else None
                response = requests.post(url, headers=headers, params=params, files=files)
            else:
                # Usa data= para application/x-www-form-urlencoded (padrão)
                response = requests.post(url, headers=headers, params=params, data=body)
        elif metodo.upper() == "PUT":
            # Verifica o tipo de encoding baseado no consumes
            if consumes and "multipart/form-data" in consumes:
                # Para multipart/form-data, usa files= (mesmo para campos não-arquivo)
                files = {k: (None, v) for k, v in body.items()} if body else None
                response = requests.put(url, headers=headers, params=params, files=files)
            else:
                # Usa data= para application/x-www-form-urlencoded (padrão)
                response = requests.put(url, headers=headers, params=params, data=body)
        elif metodo.upper() == "DELETE":
            response = requests.delete(url, headers=headers, params=params)
        else:
            raise ValueError(f"Método HTTP não suportado: {metodo}")
        
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


def avaliar_sucesso_teste(resultado: Dict, tipo_teste: str, metodo: str = "GET", body_enviado: Dict = None) -> Dict:
    """Avalia se o teste foi bem-sucedido baseado no tipo de teste e resposta"""
    if resultado["error"]:
        return {**resultado, "success": False}
    
    cod_retorno = resultado["data"].get("codRetorno")
    total_registros = resultado["data"].get("totalRegistros")
    desc_retorno = resultado["data"].get("descRetorno", "")
    
    if tipo_teste == "parametros_invalidos":
        # Para parâmetros inválidos, esperamos codRetorno 404
        sucesso = cod_retorno == "404"
    elif tipo_teste == "parametros_validos":
        # Para parâmetros válidos, esperamos codRetorno 200 e totalRegistros 1
        sucesso = cod_retorno == "200" and total_registros == "1"
    elif tipo_teste == "crud_delete":
        # DELETE: codRetorno 200 E descRetorno específica de sucesso
        sucesso = cod_retorno == "200" and "apagados com sucesso" in desc_retorno
    elif tipo_teste == "crud_post" or tipo_teste == "crud_put":
        # POST/PUT: codRetorno 200 e deve retornar os dados criados/atualizados
        sucesso = cod_retorno == "200" and total_registros == "1" and "Key_000000" in resultado["data"]
        
        # Para PUT, verifica se os dados foram realmente atualizados
        if sucesso and tipo_teste == "crud_put" and body_enviado:
            import json
            try:
                dados_json = resultado["data"]["Key_000000"]
                dados_retornados = json.loads(dados_json) if isinstance(dados_json, str) else dados_json
                
                # Verifica se pelo menos um campo foi atualizado com o valor enviado
                campos_verificados = 0
                campos_atualizados = 0
                
                for campo_enviado, valor_enviado in body_enviado.items():
                    # Ignora campos ID na validação (não são modificados)
                    if "_ID_" in campo_enviado or campo_enviado.startswith("ID_") or campo_enviado.endswith("_ID"):
                        continue
                    
                    # Procura o campo na resposta
                    for chave, valor_retornado in dados_retornados.items():
                        nome_campo = chave.split(".")[-1] if "." in chave else chave
                        if nome_campo == campo_enviado:
                            campos_verificados += 1
                            # Compara valores (converte para string para comparação)
                            if str(valor_retornado).strip() == str(valor_enviado).strip():
                                campos_atualizados += 1
                            break
                
                # PUT só é sucesso se pelo menos um campo foi atualizado
                if campos_verificados > 0 and campos_atualizados == 0:
                    sucesso = False
                    resultado["data"]["_aviso_put"] = f"Nenhum campo foi atualizado ({campos_verificados} campos verificados)"
            except:
                pass
    elif tipo_teste == "crud_get":
        # GET para CRUD: codRetorno 200
        sucesso = cod_retorno == "200"
    else:
        # Para sem parâmetros, esperamos codRetorno 200
        sucesso = cod_retorno == "200" if cod_retorno else True
    
    return {**resultado, "success": sucesso}

def extrair_id_de_resposta(resultado: Dict, nome_campo_id: str) -> any:
    """Extrai o valor do campo ID da resposta de POST/PUT
    Retorna o ID salvo ou None se não encontrado"""
    import json
    
    if not resultado.get("data") or "Key_000000" not in resultado["data"]:
        return None
    
    try:
        dados_json = resultado["data"]["Key_000000"]
        dados = json.loads(dados_json) if isinstance(dados_json, str) else dados_json
        
        # Remove prefixo P_ do nome do campo se existir
        nome_campo_busca = nome_campo_id.replace("P_", "") if nome_campo_id else ""
        
        # Procura pelo campo ID no registro retornado
        for chave, valor in dados.items():
            nome_campo = chave.split(".")[-1] if "." in chave else chave
            # Compara ignorando prefixo P_
            nome_campo_sem_prefixo = nome_campo.replace("P_", "")
            
            if nome_campo == nome_campo_busca or nome_campo_sem_prefixo == nome_campo_busca:
                return valor
        
        return None
    except Exception as e:
        return None


def extrair_dados_primeiro_registro(resultado_get: Dict) -> Dict:
    """Extrai os dados do primeiro registro de uma resposta GET"""
    import json
    
    if not resultado_get.get("data") or "Key_000000" not in resultado_get["data"]:
        return {}
    
    try:
        dados_json = resultado_get["data"]["Key_000000"]
        return json.loads(dados_json) if isinstance(dados_json, str) else dados_json
    except:
        return {}


def construir_body_post(dados_registro: Dict) -> Dict:
    """Constrói o body para requisição POST baseado nos dados de um registro"""
    # Remove prefixos de tabela dos campos (ex: "DBR_EXAME.DBR_ID_EXAME" -> "DBR_ID_EXAME")
    body = {}
    for chave, valor in dados_registro.items():
        nome_campo = chave.split(".")[-1] if "." in chave else chave
        body[nome_campo] = valor
    return body


def construir_body_de_parametros(parametros: List[Dict], dados_registro: Dict, id_teste: int = None) -> Dict:
    """Constrói body baseado em parâmetros formData e dados de um registro
    Se id_teste for fornecido, substitui campos ID pelo valor de teste"""
    body = {}
    
    # Filtra apenas parâmetros formData
    parametros_form = [p for p in parametros if isinstance(p, dict) and p.get("in") == "formData"]
    
    for param in parametros_form:
        nome_param = param.get("name")
        if not nome_param:
            continue
        
        # Se é um campo ID e temos um ID de teste, usa o ID de teste
        if id_teste is not None and ("_ID_" in nome_param or nome_param.startswith("ID_") or nome_param.endswith("_ID")):
            body[nome_param] = id_teste
            continue
        
        # Tenta encontrar o valor correspondente no registro
        valor = None
        for chave, val in dados_registro.items():
            nome_campo = chave.split(".")[-1] if "." in chave else chave
            if nome_campo == nome_param:
                valor = val
                break
        
        # Se não encontrou, usa valor padrão baseado no tipo
        if valor is None:
            tipo_param = param.get("type", "string")
            valor = 0 if tipo_param in ["integer", "number"] else ""
        
        body[nome_param] = valor
    
    return body


def verificar_registro_ja_existe(resultado: Dict) -> bool:
    """Verifica se o erro indica que o registro já existe"""
    if resultado.get("error"):
        return False
    
    cod_retorno = resultado.get("data", {}).get("codRetorno")
    desc_retorno = resultado.get("data", {}).get("descRetorno", "")
    
    # Verifica padrão de erro "registro já existe"
    return (cod_retorno == "404" and 
            ("registo j" in desc_retorno.lower() and "existe" in desc_retorno.lower()))


def extrair_id_de_parametros(parametros: Dict) -> tuple:
    """Extrai o nome e valor do campo ID dos parâmetros
    Retorna (nome_campo_id, valor_id) ou (None, None)"""
    for nome, valor in parametros.items():
        if "_ID_" in nome or nome.startswith("ID_") or nome.endswith("_ID"):
            return (nome, valor)
    return (None, None)


def atualizar_parametros_com_id(parametros: Dict, nome_campo_id: str, novo_id: int) -> Dict:
    """Cria uma cópia dos parâmetros substituindo o valor do campo ID"""
    parametros_novos = parametros.copy()
    if nome_campo_id:
        parametros_novos[nome_campo_id] = novo_id
    return parametros_novos


def modificar_body_put(body: Dict) -> Dict:
    """Modifica valores do body para teste de PUT"""
    body_modificado = body.copy()
    
    # Modifica campos de texto para "MODIFICADO"
    for chave, valor in body_modificado.items():
        if isinstance(valor, str) and not chave.startswith("DT_") and not chave.endswith("_ID"):
            # Não modifica IDs nem datas
            if len(valor) > 0 and not valor.isdigit():
                body_modificado[chave] = "MODIFICADO"
    
    return body_modificado