import sys
import time
from typing import Dict, List

try:
    from configuracao import REQUEST_DELAY_SECONDS, ENDPOINT_LIMIT, BASE_URL, TEST_MODE
except ImportError:
    print("ERRO: Arquivo 'configuracao.py' não encontrado!")
    print()
    print("Use o arquivo como base 'configuracao.py.example' para criar seu 'configuracao.py'")
    print()
    sys.exit(1)

from cliente_api import (
    obter_especificacao_api,
    construir_headers,
    extrair_endpoints_get,
    extrair_endpoints_todos,
    obter_nome_endpoint,
    chamar_api,
    avaliar_sucesso_teste,
    extrair_dados_primeiro_registro,
    extrair_id_de_resposta,
    construir_body_post,
    construir_body_de_parametros,
    modificar_body_put,
    verificar_registro_ja_existe,
    extrair_id_de_parametros,
    atualizar_parametros_com_id
)
from construtor_parametros import (
    construir_parametros_validos,
    construir_parametros_invalidos
)
from gerador_relatorios import salvar_relatorios


def testar_endpoint(base_url: str, endpoint: Dict, headers: Dict) -> List[Dict]:
    """Testa um endpoint com diferentes cenários"""
    resultados = []
    nome_endpoint = obter_nome_endpoint(endpoint)
    caminho = endpoint["path"]
    
    # Teste sem parâmetros
    # Caso especial R082H: não testa sem parâmetros pois P_SCO_ID_HR é obrigatório
    if endpoint.get("x_objeto_api") == "CBR_API_REST_SST_R082H":
        print(f"Testando {nome_endpoint} sem parâmetros (pulado - parâmetro obrigatório)...")
        resultado_sem_params = {
            "status_code": None,
            "data": {},
            "error": None,
            "response_time_ms": None,
            "success": True,
            "skipped": True,
            "skip_message": "Não há teste sem parâmetros para este endpoint. P_SCO_ID_HR é obrigatório."
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
        time.sleep(REQUEST_DELAY_SECONDS)
    
    # Teste com parâmetros válidos
    if endpoint["parameters"]:
        print(f"Testando {nome_endpoint} com parâmetros válidos...")
        parametros_validos = construir_parametros_validos(endpoint["parameters"], resultado_sem_params, endpoint)
        resultado = chamar_api(base_url, caminho, headers, parametros_validos)
        resultado = avaliar_sucesso_teste(resultado, "parametros_validos")
        resultados.append({
            "endpoint": nome_endpoint,
            "test_type": "parametros_validos",
            "params": parametros_validos,
            "result": resultado
        })
        time.sleep(REQUEST_DELAY_SECONDS)
        
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
        time.sleep(REQUEST_DELAY_SECONDS)
    
    return resultados


def testar_endpoint_crud(base_url: str, endpoint: Dict, headers: Dict) -> List[Dict]:
    """Testa um endpoint com sequência completa CRUD: GET -> POST (novo ID) -> PUT -> DELETE"""
    resultados = []
    nome_endpoint = obter_nome_endpoint(endpoint)
    caminho = endpoint["path"]
    metodos = endpoint.get("methods", {})
    
    print(f"\n{'='*80}")
    print(f"Testando CRUD completo: {nome_endpoint}")
    print(f"Métodos disponíveis: {', '.join(metodos.keys()).upper()}")
    print(f"{'='*80}")
    
    # Passo 1: GET - Obter dados válidos
    if "get" not in metodos:
        print("ERRO: GET não disponível - pulando endpoint")
        return resultados
    
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
        return resultados
    
    print(f"✓ GET bem-sucedido (codRetorno: {resultado_get['data'].get('codRetorno')})")
    time.sleep(REQUEST_DELAY_SECONDS)
    
    # Extrai dados do primeiro registro
    dados_registro = extrair_dados_primeiro_registro(resultado_get)
    if not dados_registro:
        print("ERRO: Não foi possível extrair dados do registro - PARANDO")
        return resultados
    
    # Extrai parâmetros para usar nas operações (IDs, etc)
    parametros = {}
    if metodos["get"].get("parameters"):
        parametros = construir_parametros_validos(
            metodos["get"]["parameters"], 
            resultado_get, 
            {"x_objeto_api": endpoint["x_objeto_api"]}
        )
    
    # Identifica o campo ID para substituição
    nome_campo_id, _ = extrair_id_de_parametros(parametros)
    
    # Passo 2: POST - Criar novo registro com ID de teste
    if "post" not in metodos:
        print("\n[2/4] POST não disponível - pulando restante dos testes")
        return resultados
    
    print(f"\n[2/4] POST - Criando novo registro com ID de teste...")
    
    # Lista de IDs para tentar
    ids_teste = [987154874, 23942835]
    resultado_post = None
    body_post = None
    id_usado = None
    parametros_post = {}
    
    for id_teste in ids_teste:
        print(f"   Tentando POST com ID={id_teste}...")
        body_post = construir_body_de_parametros(metodos["post"]["parameters"], dados_registro, id_teste)
        parametros_post = atualizar_parametros_com_id(parametros, nome_campo_id, id_teste)
        resultado_post = chamar_api(base_url, caminho, headers, params=parametros_post, body=body_post, metodo="POST", consumes=metodos["post"].get("consumes"))
        
        # Verifica se deu erro de registro já existe
        if verificar_registro_ja_existe(resultado_post):
            print(f"   Registro com ID={id_teste} já existe, tentando próximo ID...")
            continue
        
        # Se não é erro de duplicação, avalia sucesso e para
        resultado_post = avaliar_sucesso_teste(resultado_post, "crud_post")
        id_usado = id_teste
        break
    
    resultados.append({
        "endpoint": nome_endpoint,
        "test_type": "crud_post",
        "method": "POST",
        "params": parametros_post,
        "body": body_post,
        "result": resultado_post
    })
    
    if not resultado_post or not resultado_post["success"]:
        print(f"ERRO: POST falhou - PARANDO testes para este endpoint")
        if resultado_post:
            print(f"   codRetorno: {resultado_post['data'].get('codRetorno')}")
            print(f"   descRetorno: {resultado_post['data'].get('descRetorno')}")
        return resultados
    
    print(f"SUCESSO: POST bem-sucedido com ID={id_usado} (codRetorno: {resultado_post['data'].get('codRetorno')})")
    time.sleep(REQUEST_DELAY_SECONDS)
    
    # Extrai o ID real que foi salvo (pode ser truncado pela API)
    print(f"   Extraindo ID real da resposta (campo: {nome_campo_id})...")
    id_salvo = extrair_id_de_resposta(resultado_post, nome_campo_id)
    print(f"   ID extraído: {id_salvo} (tipo: {type(id_salvo).__name__})")
    print(f"   ID enviado: {id_usado} (tipo: {type(id_usado).__name__})")
    
    if id_salvo:
        # Converte para o mesmo tipo (int se possível)
        try:
            id_salvo = int(id_salvo)
            id_usado_int = int(id_usado)
            
            if id_salvo != id_usado_int:
                print(f"   ATENÇÃO: ID foi truncado pela API: {id_usado} -> {id_salvo}")
                id_usado = id_salvo
            else:
                print(f"   ID verificado: {id_salvo}")
        except (ValueError, TypeError) as e:
            print(f"   Erro na conversão: {e}")
            # Se não for numérico, compara como string
            if str(id_salvo) != str(id_usado):
                print(f"   ATENÇÃO: ID foi modificado pela API: {id_usado} -> {id_salvo}")
                id_usado = id_salvo
            else:
                print(f"   ID verificado: {id_salvo}")
    else:
        print(f"   AVISO: Não foi possível extrair ID da resposta, usando ID original: {id_usado}")
    
    print(f"   ID final a ser usado em PUT/DELETE: {id_usado}")
    
    # Atualiza parâmetros com o ID real salvo para usar em PUT e DELETE
    parametros_novo_registro = atualizar_parametros_com_id(parametros, nome_campo_id, id_usado)
    print(f"   Parâmetros para PUT/DELETE: {parametros_novo_registro}")
    
    # Passo 3: PUT - Modificar e restaurar
    if "put" not in metodos:
        print("\n[3/4] PUT não disponível - pulando para DELETE")
    else:
        print(f"\n[3/4] PUT - Modificando registro...")
        body_put_original = construir_body_de_parametros(metodos["put"]["parameters"], dados_registro, id_usado)
        body_put_modificado = modificar_body_put(body_put_original)
        
        # IMPORTANTE: Incluir o ID no body para PUT (algumas APIs exigem isso)
        # Remove o prefixo "P_" do nome do campo para incluir no body
        nome_campo_body = nome_campo_id.replace("P_", "", 1) if nome_campo_id.startswith("P_") else nome_campo_id
        body_put_modificado[nome_campo_body] = id_usado
        print(f"   Incluindo ID no body: {nome_campo_body} = {id_usado}")
        
        resultado_put_mod = chamar_api(base_url, caminho, headers, params=parametros_novo_registro, body=body_put_modificado, metodo="PUT", consumes=metodos["put"].get("consumes"))
        resultado_put_mod = avaliar_sucesso_teste(resultado_put_mod, "crud_put", body_enviado=body_put_modificado)
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
                print(f"   NOTA: A API pode não suportar atualizações via PUT para este endpoint")
        else:
            print(f"SUCESSO: PUT bem-sucedido")
            time.sleep(REQUEST_DELAY_SECONDS)
    
    # Passo 4: DELETE - Deletar o registro de teste criado
    if "delete" not in metodos:
        print("\n[4/4] DELETE não disponível - ATENÇÃO: Registro de teste não foi deletado!")
        print(f"   Registro criado com ID={id_usado} permanece no sistema")
    else:
        print(f"\n[4/4] DELETE - Deletando registro de teste...")
        resultado_delete = chamar_api(base_url, caminho, headers, params=parametros_novo_registro, metodo="DELETE")
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
            print(f"SUCESSO: DELETE bem-sucedido (descRetorno: {resultado_delete['data'].get('descRetorno')})")
            time.sleep(REQUEST_DELAY_SECONDS)
    
    print(f"\nSUCESSO: CRUD completo executado para {nome_endpoint}")
    return resultados


def main():
    """Função principal que executa os testes"""
    print("Iniciando testes da API SST...")
    print(f"Modo de teste: {TEST_MODE}")
    print()
    
    # Obtém especificação da API
    print("Obtendo especificação da API...")
    spec = obter_especificacao_api()
    print(f"Especificação obtida: {spec['info']['title']} v{spec['info']['version']}")
    print()
    
    # Prepara configurações
    base_url = BASE_URL
    headers = construir_headers()
    todos_resultados = []
    
    if TEST_MODE == "FULL_CRUD":
        # Modo CRUD completo - testa todos os métodos HTTP
        endpoints = extrair_endpoints_todos(spec)
        endpoints.sort(key=lambda e: obter_nome_endpoint(e))
        print(f"Encontrados {len(endpoints)} endpoints")
        
        # Aplica limite de endpoints se configurado
        if ENDPOINT_LIMIT > 0:
            endpoints = endpoints[:ENDPOINT_LIMIT]
            print(f"Limitando aos primeiros {ENDPOINT_LIMIT} endpoints")
        
        print()
        
        # Executa testes CRUD
        for endpoint in endpoints:
            resultados = testar_endpoint_crud(base_url, endpoint, headers)
            todos_resultados.extend(resultados)
            print()
    
    else:
        # Modo padrão - apenas GET
        endpoints = extrair_endpoints_get(spec)
        endpoints.sort(key=lambda e: obter_nome_endpoint(e))
        print(f"Encontrados {len(endpoints)} endpoints GET")
        
        # Aplica limite de endpoints se configurado
        if ENDPOINT_LIMIT > 0:
            endpoints = endpoints[:ENDPOINT_LIMIT]
            print(f"Limitando aos primeiros {ENDPOINT_LIMIT} endpoints")
        
        print()
        
        # Executa testes GET
        for endpoint in endpoints:
            resultados = testar_endpoint(base_url, endpoint, headers)
            todos_resultados.extend(resultados)
            print()
    
    # Gera e salva relatórios
    print("Gerando relatórios...")
    arquivos_salvos = salvar_relatorios(todos_resultados, base_url)
    
    print(f"Relatório resumido salvo em: {arquivos_salvos['resumido']}")
    print(f"Relatório completo salvo em: {arquivos_salvos['completo']}")
    
    if "falhas" in arquivos_salvos:
        print(f"Relatório de falhas salvo em: {arquivos_salvos['falhas']}")
    
    print()
    print("Testes concluídos!")


if __name__ == "__main__":
    main()
