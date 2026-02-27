"""
Runner principal para execução de testes da API.
Orquestra a execução completa de testes GET ou CRUD.
"""
import sys

try:
    from configuracao import (
        REQUEST_DELAY_SECONDS,
        ENDPOINT_LIMIT,
        BASE_URL,
        TEST_MODE,
        API_KEY,
        HEADERS_DEFAULT,
        SWAGGER_URL,
        ENDPOINT_ESPECIFICO
    )
except ImportError:
    print("ERRO: Arquivo 'configuracao.py' não encontrado!")
    print()
    print("Use o arquivo como base 'configuracao.py.example' para criar seu 'configuracao.py'")
    print()
    sys.exit(1)

from cliente_swagger import (
    obter_especificacao_api,
    extrair_endpoints_get,
    extrair_endpoints_todos,
    obter_nome_endpoint
)
from cliente_http import construir_headers
from cenarios_teste import testar_endpoint, testar_endpoint_crud
from gerador_relatorios import salvar_relatorios, RelatorioIncremental


def filtrar_endpoints(endpoints: list) -> list:
    """
    Filtra endpoints baseado nas configurações.
    
    Args:
        endpoints: Lista de endpoints
        
    Returns:
        Lista filtrada de endpoints
    """
    # Filtro por endpoint específico
    if ENDPOINT_ESPECIFICO:
        endpoints = [
            e for e in endpoints 
            if e.get("x_objeto_api") == ENDPOINT_ESPECIFICO
        ]
        if not endpoints:
            print(f"AVISO: Endpoint '{ENDPOINT_ESPECIFICO}' não encontrado!")
            return []
    
    # Ordenação
    endpoints.sort(key=lambda e: obter_nome_endpoint(e))
    
    # Limite de quantidade
    if ENDPOINT_LIMIT > 0 and not ENDPOINT_ESPECIFICO:
        endpoints = endpoints[:ENDPOINT_LIMIT]
    
    return endpoints


def main():
    """Função principal que executa os testes."""
    print("Iniciando testes da API SST...")
    print(f"Modo de teste: {TEST_MODE}")
    print()
    
    # Obtém especificação da API
    print("Obtendo especificação da API...")
    spec = obter_especificacao_api(SWAGGER_URL)
    print(f"Especificação obtida: {spec['info']['title']} v{spec['info']['version']}")
    print()
    
    # Prepara configurações
    headers = construir_headers(API_KEY, HEADERS_DEFAULT)
    todos_resultados = []
    
    # Cria gerenciador de relatórios incrementais
    relatorio = RelatorioIncremental(BASE_URL)
    
    if TEST_MODE == "FULL_CRUD":
        _executar_modo_crud(spec, headers, relatorio)
    else:
        _executar_modo_get(spec, headers, relatorio)
    
    # Finaliza relatórios
    print("Finalizando relatórios...")
    arquivos_salvos = relatorio.finalizar()
    
    print(f"Relatório resumido salvo em: {arquivos_salvos['resumido']}")
    print(f"Relatório completo salvo em: {arquivos_salvos['completo']}")
    
    if "falhas" in arquivos_salvos:
        print(f"Relatório de itens a verificar salvo em: {arquivos_salvos['falhas']}")
    
    print()
    print("Testes concluídos!")


def _executar_modo_crud(spec: dict, headers: dict, relatorio: RelatorioIncremental) -> None:
    """
    Executa testes em modo CRUD completo.
    
    Args:
        spec: Especificação da API
        headers: Headers HTTP
        relatorio: Gerenciador de relatórios incrementais
    """
    endpoints = extrair_endpoints_todos(spec)
    endpoints = filtrar_endpoints(endpoints)
    
    if not endpoints:
        print("Nenhum endpoint encontrado para testar.")
        return
    
    print(f"Encontrados {len(endpoints)} endpoint(s)")
    
    if ENDPOINT_ESPECIFICO:
        print(f"Testando APENAS: {ENDPOINT_ESPECIFICO}")
    elif ENDPOINT_LIMIT > 0:
        print(f"Limitando aos primeiros {ENDPOINT_LIMIT} endpoints")
    
    print()
    
    # Executa testes CRUD
    for endpoint in endpoints:
        resultados = testar_endpoint_crud(
            BASE_URL,
            endpoint,
            headers,
            REQUEST_DELAY_SECONDS
        )
        # Adiciona cada resultado ao relatório em tempo real
        for resultado in resultados:
            relatorio.adicionar_resultado(resultado)
        print()


def _executar_modo_get(spec: dict, headers: dict, relatorio: RelatorioIncremental) -> None:
    """
    Executa testes em modo GET apenas.
    
    Args:
        spec: Especificação da API
        headers: Headers HTTP
        relatorio: Gerenciador de relatórios incrementais
    """
    endpoints = extrair_endpoints_get(spec)
    endpoints = filtrar_endpoints(endpoints)
    
    if not endpoints:
        print("Nenhum endpoint encontrado para testar.")
        return
    
    print(f"Encontrados {len(endpoints)} endpoint(s) GET")
    
    if ENDPOINT_ESPECIFICO:
        print(f"Testando APENAS: {ENDPOINT_ESPECIFICO}")
    elif ENDPOINT_LIMIT > 0:
        print(f"Limitando aos primeiros {ENDPOINT_LIMIT} endpoints")
    
    print()
    
    # Executa testes GET
    for endpoint in endpoints:
        resultados = testar_endpoint(
            BASE_URL,
            endpoint,
            headers,
            REQUEST_DELAY_SECONDS
        )
        # Adiciona cada resultado ao relatório em tempo real
        for resultado in resultados:
            relatorio.adicionar_resultado(resultado)
        print()


if __name__ == "__main__":
    main()
