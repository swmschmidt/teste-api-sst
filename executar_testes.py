import sys
import time
from typing import Dict, List

try:
    from configuracao import REQUEST_DELAY_SECONDS, ENDPOINT_LIMIT, BASE_URL
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
    obter_nome_endpoint,
    chamar_api,
    avaliar_sucesso_teste
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


def main():
    """Função principal que executa os testes"""
    print("Iniciando testes da API SST...")
    print()
    
    # Obtém especificação da API
    print("Obtendo especificação da API...")
    spec = obter_especificacao_api()
    print(f"Especificação obtida: {spec['info']['title']} v{spec['info']['version']}")
    print()
    
    # Extrai endpoints GET
    endpoints = extrair_endpoints_get(spec)
    endpoints.sort(key=lambda e: obter_nome_endpoint(e))
    print(f"Encontrados {len(endpoints)} endpoints GET")
    
    # Aplica limite de endpoints se configurado
    if ENDPOINT_LIMIT > 0:
        endpoints = endpoints[:ENDPOINT_LIMIT]
        print(f"Limitando aos primeiros {ENDPOINT_LIMIT} endpoints")
    
    print()
    
    # Prepara configurações
    base_url = BASE_URL
    headers = construir_headers()
    
    # Executa testes
    todos_resultados = []
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
