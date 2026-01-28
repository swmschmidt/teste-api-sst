import json
from typing import Dict, List, Any
from datetime import datetime
from configuracao import MAX_RESPONSE_SIZE


def truncar_resposta(dados: Any, tamanho_max: int) -> str:
    """Trunca resposta para tamanho máximo"""
    resposta_str = json.dumps(dados, ensure_ascii=False, indent=2)
    if len(resposta_str) > tamanho_max:
        return resposta_str[:tamanho_max] + "\n... (truncado)"
    return resposta_str


def gerar_relatorio_resumido(todos_resultados: List[Dict], base_url: str) -> str:
    """Gera relatório resumido dos testes"""
    linhas = [
        "=" * 80,
        "RELATÓRIO DE TESTES - API SST",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Base URL: {base_url}",
        "=" * 80,
        "",
        "DESCRIÇÃO DOS TESTES:",
        "São realizados 3 tipos de teste para o método GET:",
        "1) Sem parâmetros: espera-se que retornem todos os resultados da tela",
        "2) Parâmetros válidos: espera-se que seja retornado apenas um resultado, equivalente aos parâmetros inseridos",
        "3) Parâmetros inválidos: espera-se que retorne vazio, com codRetorno 404.",
        "",
        "=" * 80,
        ""
    ]
    
    total_testes = len(todos_resultados)
    testes_sucesso = sum(1 for r in todos_resultados if r["result"]["success"])
    testes_falha = total_testes - testes_sucesso
    
    linhas.extend([
        f"Total de testes: {total_testes}",
        f"Sucessos: {testes_sucesso}",
        f"Falhas: {testes_falha}",
        "",
        "DETALHAMENTO POR ENDPOINT:",
        ""
    ])
    
    endpoint_atual = None
    for teste in todos_resultados:
        if teste["endpoint"] != endpoint_atual:
            endpoint_atual = teste["endpoint"]
            linhas.append(f"\n{endpoint_atual}")
            linhas.append("-" * 80)
        
        tipo_teste = teste["test_type"].replace("_", " ").title()
        
        # Verifica se o teste foi pulado (caso especial)
        if teste["result"].get("skipped"):
            linhas.append(f"  {tipo_teste}: PULADO")
            linhas.append(f"    {teste['result']['skip_message']}")
            continue
        
        status = "SUCESSO" if teste["result"]["success"] else "FALHA"
        codigo_status = teste["result"].get("status_code", "N/A")
        
        # Extrai informações adicionais da resposta
        dados = teste["result"].get("data", {})
        cod_retorno = dados.get("codRetorno", "N/A")
        total_registros = dados.get("totalRegistros", "N/A")
        
        linha_info = f"  {tipo_teste}: {status} (HTTP {codigo_status} - codRetorno: {cod_retorno} - totalRegistros: {total_registros})"
        linhas.append(linha_info)
        
        if not teste["result"]["success"]:
            linhas.append(f"    Erro: {teste['result']['error']}")
    
    linhas.append("\n" + "=" * 80)
    return "\n".join(linhas)


def gerar_relatorio_completo(todos_resultados: List[Dict], base_url: str) -> str:
    """Gera relatório completo com todas as respostas"""
    linhas = [
        "=" * 80,
        "RELATÓRIO COMPLETO - API SST",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Base URL: {base_url}",
        "=" * 80,
        "",
        "DESCRIÇÃO DOS TESTES:",
        "São realizados 3 tipos de teste para o método GET:",
        "1) Sem parâmetros: espera-se que retornem todos os resultados da tela",
        "2) Parâmetros válidos: espera-se que seja retornado apenas um resultado, equivalente aos parâmetros inseridos",
        "3) Parâmetros inválidos: espera-se que retorne vazio, com codRetorno 404.",
        "",
        "=" * 80,
        ""
    ]
    
    for teste in todos_resultados:
        linhas.append(f"\nENDPOINT: {teste['endpoint']}")
        linhas.append(f"TIPO DE TESTE: {teste['test_type']}")
        
        # Adiciona método HTTP se disponível
        if "method" in teste:
            linhas.append(f"MÉTODO: {teste['method']}")
        
        resultado = teste["result"]
        
        # Verifica se o teste foi pulado (caso especial)
        if resultado.get("skipped"):
            linhas.append(f"STATUS: PULADO")
            linhas.append(f"MOTIVO: {resultado['skip_message']}")
            linhas.append("-" * 80)
            continue
        
        # Adiciona parâmetros da requisição
        if "params" in teste and teste["params"]:
            linhas.append(f"PARÂMETROS (query): {json.dumps(teste['params'], ensure_ascii=False)}")
        
        # Adiciona body da requisição
        if "body" in teste and teste["body"]:
            linhas.append(f"BODY (formData): {json.dumps(teste['body'], ensure_ascii=False)}")
        
        linhas.append(f"STATUS HTTP: {resultado.get('status_code', 'N/A')}")
        linhas.append(f"TEMPO DE RESPOSTA: {resultado.get('response_time_ms', 'N/A')}ms")
        status_teste = "Sucesso" if resultado["success"] else "Falha"
        linhas.append(f"STATUS DO TESTE: {status_teste}")
        linhas.append("RESPOSTA:")
        linhas.append(truncar_resposta(resultado["data"], MAX_RESPONSE_SIZE))
        
        linhas.append("-" * 80)
    
    return "\n".join(linhas)


def gerar_relatorio_falhas(todos_resultados: List[Dict], base_url: str) -> str:
    """Gera relatório completo apenas dos testes que falharam"""
    testes_falhos = [teste for teste in todos_resultados if not teste["result"]["success"]]
    
    linhas = [
        "=" * 80,
        "RELATÓRIO DE FALHAS - API SST",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Base URL: {base_url}",
        "=" * 80,
        "",
        f"Total de falhas: {len(testes_falhos)}",
        "",
        "=" * 80,
        ""
    ]
    
    for teste in testes_falhos:
        linhas.append(f"\nENDPOINT: {teste['endpoint']}")
        linhas.append(f"TIPO DE TESTE: {teste['test_type']}")
        
        # Adiciona método HTTP se disponível
        if "method" in teste:
            linhas.append(f"MÉTODO: {teste['method']}")
        
        # Adiciona parâmetros da requisição
        if "params" in teste and teste["params"]:
            linhas.append(f"PARÂMETROS (query): {json.dumps(teste['params'], ensure_ascii=False)}")
        
        # Adiciona body da requisição
        if "body" in teste and teste["body"]:
            linhas.append(f"BODY (formData): {json.dumps(teste['body'], ensure_ascii=False)}")
        
        resultado = teste["result"]
        linhas.append(f"STATUS HTTP: {resultado.get('status_code', 'N/A')}")
        linhas.append(f"TEMPO DE RESPOSTA: {resultado.get('response_time_ms', 'N/A')}ms")
        linhas.append(f"SUCESSO: {resultado['success']}")
        linhas.append("RESPOSTA:")
        linhas.append(truncar_resposta(resultado["data"], MAX_RESPONSE_SIZE))
        
        linhas.append("-" * 80)
    
    return "\n".join(linhas)


def salvar_relatorios(todos_resultados: List[Dict], base_url: str) -> Dict[str, str]:
    """
    Gera e salva todos os relatórios
    Retorna um dicionário com os caminhos dos arquivos salvos
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Gera relatórios
    relatorio_resumido = gerar_relatorio_resumido(todos_resultados, base_url)
    relatorio_completo = gerar_relatorio_completo(todos_resultados, base_url)
    
    # Nomes dos arquivos
    arquivo_resumido = f"relatorio_resumido_{timestamp}.txt"
    arquivo_completo = f"relatorio_completo_{timestamp}.txt"
    arquivo_falhas = f"relatorio_falhas_{timestamp}.txt"
    
    # Salva arquivo resumido
    with open(arquivo_resumido, "w", encoding="utf-8") as f:
        f.write(relatorio_resumido)
    
    # Salva arquivo completo
    with open(arquivo_completo, "w", encoding="utf-8") as f:
        f.write(relatorio_completo)
    
    arquivos_salvos = {
        "resumido": arquivo_resumido,
        "completo": arquivo_completo
    }
    
    # Verifica se há falhas para gerar relatório adicional
    testes_falhos = [t for t in todos_resultados if not t["result"]["success"]]
    if testes_falhos:
        relatorio_falhas = gerar_relatorio_falhas(todos_resultados, base_url)
        with open(arquivo_falhas, "w", encoding="utf-8") as f:
            f.write(relatorio_falhas)
        arquivos_salvos["falhas"] = arquivo_falhas
    
    return arquivos_salvos
