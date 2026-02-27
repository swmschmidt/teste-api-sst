"""
Gerador de relatórios de teste.
Responsável por formatar e salvar relatórios em diferentes formatos.
"""
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime


# Configuração de truncamento
MAX_RESPONSE_SIZE = 5000


class RelatorioIncremental:
    """Gerencia escrita incremental de relatórios durante execução dos testes."""
    
    def __init__(self, base_url: str):
        """Inicializa os arquivos de relatório.
        
        Args:
            base_url: URL base da API
        """
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.base_url = base_url
        self.todos_resultados = []
        
        # Nomes dos arquivos
        self.arquivo_resumido = f"relatorio_resumido_{self.timestamp}.txt"
        self.arquivo_completo = f"relatorio_completo_{self.timestamp}.txt"
        self.arquivo_falhas = f"relatorio_verificar_{self.timestamp}.txt"
        
        # Inicializa arquivos com cabeçalhos
        self._inicializar_arquivos()
    
    def _inicializar_arquivos(self):
        """Cria arquivos e escreve cabeçalhos iniciais."""
        # Arquivo resumido
        with open(self.arquivo_resumido, "w", encoding="utf-8") as f:
            linhas = _criar_cabecalho("RELATÓRIO DE TESTES - API SST", self.base_url)
            linhas.extend(_criar_descricao_testes())
            f.write("\n".join(linhas) + "\n\n")
            f.write("=" * 80 + "\n")
            f.write("RESUMO POR ENDPOINT (atualizado em tempo real)\n")
            f.write("=" * 80 + "\n\n")
        
        # Arquivo completo
        with open(self.arquivo_completo, "w", encoding="utf-8") as f:
            linhas = _criar_cabecalho("RELATÓRIO COMPLETO - API SST", self.base_url)
            linhas.extend(_criar_descricao_testes())
            f.write("\n".join(linhas) + "\n\n")
    
    def adicionar_resultado(self, resultado: Dict):
        """Adiciona um resultado de teste e atualiza os relatórios.
        
        Args:
            resultado: Dicionário com resultado do teste
        """
        self.todos_resultados.append(resultado)
        
        # Adiciona ao relatório completo
        with open(self.arquivo_completo, "a", encoding="utf-8") as f:
            linhas = _formatar_teste_completo(resultado)
            f.write("\n".join(linhas) + "\n")
        
        # Se é falha, adiciona ao relatório de falhas
        if not resultado["result"].get("success", False):
            # Cria arquivo de falhas se não existe
            if not os.path.exists(self.arquivo_falhas):
                with open(self.arquivo_falhas, "w", encoding="utf-8") as f:
                    linhas = _criar_cabecalho("RELATÓRIO DE ITENS A VERIFICAR - API SST", self.base_url)
                    linhas.append("")
                    linhas.append("=" * 80)
                    linhas.append("")
                    f.write("\n".join(linhas) + "\n")
            
            # Adiciona a falha
            with open(self.arquivo_falhas, "a", encoding="utf-8") as f:
                linhas = _formatar_teste_completo(resultado)
                f.write("\n".join(linhas) + "\n")
    
    def finalizar(self) -> Dict[str, str]:
        """Finaliza os relatórios com resumos quantitativos.
        
        Returns:
            Dict com os caminhos dos arquivos salvos
        """
        # Atualiza resumo quantitativo no arquivo resumido
        with open(self.arquivo_resumido, "a", encoding="utf-8") as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write("RESUMO QUANTITATIVO FINAL\n")
            f.write("=" * 80 + "\n\n")
            linhas = _criar_resumo_quantitativo(self.todos_resultados)
            f.write("\n".join(linhas) + "\n\n")
            
            linhas = _criar_detalhamento_endpoints(self.todos_resultados)
            f.write("\n".join(linhas) + "\n")
            f.write("\n" + "=" * 80 + "\n")
        
        # Atualiza contagem total de falhas
        if os.path.exists(self.arquivo_falhas):
            testes_falhos = [t for t in self.todos_resultados if not t["result"].get("success", False)]
            
            # Lê o conteúdo atual (todas as falhas já escritas)
            with open(self.arquivo_falhas, "r", encoding="utf-8") as f:
                linhas_antigas = f.readlines()
            
            # Reescreve com contagem total no início
            with open(self.arquivo_falhas, "w", encoding="utf-8") as f:
                linhas = _criar_cabecalho("RELATÓRIO DE ITENS A VERIFICAR - API SST", self.base_url)
                linhas.append(f"Total de itens a verificar: {len(testes_falhos)}")
                linhas.append("")
                linhas.append("=" * 80)
                linhas.append("")
                f.write("\n".join(linhas) + "\n")
                
                # Pula o cabeçalho antigo e adiciona o resto do conteúdo
                # Encontra onde termina o cabeçalho antigo (após a segunda linha de "=" * 80)
                separador_count = 0
                inicio_conteudo = 0
                for i, linha in enumerate(linhas_antigas):
                    if "=" * 40 in linha:  # Linha de separador
                        separador_count += 1
                        if separador_count == 2:  # Segunda linha de separador marca fim do cabeçalho
                            inicio_conteudo = i + 2  # Pula a linha de separador e uma linha vazia
                            break
                
                # Escreve o conteúdo das falhas (sem o cabeçalho antigo)
                if inicio_conteudo < len(linhas_antigas):
                    f.writelines(linhas_antigas[inicio_conteudo:])
        
        arquivos_salvos = {
            "resumido": self.arquivo_resumido,
            "completo": self.arquivo_completo
        }
        
        if os.path.exists(self.arquivo_falhas):
            arquivos_salvos["falhas"] = self.arquivo_falhas
        
        return arquivos_salvos


def truncar_resposta(dados: Any, tamanho_max: int = MAX_RESPONSE_SIZE) -> str:
    """
    Trunca resposta para tamanho máximo.
    
    Args:
        dados: Dados a serem convertidos para string
        tamanho_max: Tamanho máximo permitido
        
    Returns:
        String JSON formatada (possivelmente truncada)
    """
    resposta_str = json.dumps(dados, ensure_ascii=False, indent=2)
    if len(resposta_str) > tamanho_max:
        return resposta_str[:tamanho_max] + "\n... (truncado)"
    return resposta_str


def gerar_relatorio_resumido(todos_resultados: List[Dict], base_url: str) -> str:
    """
    Gera relatório resumido dos testes.
    
    Args:
        todos_resultados: Lista de todos os resultados de testes
        base_url: URL base da API
        
    Returns:
        String com relatório formatado
    """
    linhas = _criar_cabecalho("RELATÓRIO DE TESTES - API SST", base_url)
    linhas.extend(_criar_descricao_testes())
    linhas.extend(_criar_resumo_quantitativo(todos_resultados))
    linhas.extend(_criar_detalhamento_endpoints(todos_resultados))
    
    linhas.append("\n" + "=" * 80)
    return "\n".join(linhas)


def gerar_relatorio_completo(todos_resultados: List[Dict], base_url: str) -> str:
    """
    Gera relatório completo com todas as respostas.
    
    Args:
        todos_resultados: Lista de todos os resultados de testes
        base_url: URL base da API
        
    Returns:
        String com relatório formatado
    """
    linhas = _criar_cabecalho("RELATÓRIO COMPLETO - API SST", base_url)
    linhas.extend(_criar_descricao_testes())
    
    for teste in todos_resultados:
        linhas.extend(_formatar_teste_completo(teste))
    
    return "\n".join(linhas)


def gerar_relatorio_falhas(todos_resultados: List[Dict], base_url: str) -> str:
    """
    Gera relatório completo apenas dos testes que falharam.
    
    Args:
        todos_resultados: Lista de todos os resultados de testes
        base_url: URL base da API
        
    Returns:
        String com relatório formatado
    """
    testes_falhos = [
        teste for teste in todos_resultados
        if not teste["result"].get("success", False)
    ]
    
    linhas = _criar_cabecalho("RELATÓRIO DE ITENS A VERIFICAR - API SST", base_url)
    linhas.append(f"Total de itens a verificar: {len(testes_falhos)}")
    linhas.append("")
    linhas.append("=" * 80)
    linhas.append("")
    
    for teste in testes_falhos:
        linhas.extend(_formatar_teste_completo(teste))
    
    return "\n".join(linhas)


def salvar_relatorios(todos_resultados: List[Dict], base_url: str) -> Dict[str, str]:
    """
    Gera e salva todos os relatórios.
    
    Args:
        todos_resultados: Lista de todos os resultados de testes
        base_url: URL base da API
        
    Returns:
        Dict com os caminhos dos arquivos salvos
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Gera relatórios
    relatorio_resumido = gerar_relatorio_resumido(todos_resultados, base_url)
    relatorio_completo = gerar_relatorio_completo(todos_resultados, base_url)
    
    # Nomes dos arquivos
    arquivo_resumido = f"relatorio_resumido_{timestamp}.txt"
    arquivo_completo = f"relatorio_completo_{timestamp}.txt"
    arquivo_falhas = f"relatorio_verificar_{timestamp}.txt"
    
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
    testes_falhos = [t for t in todos_resultados if not t["result"].get("success", False)]
    if testes_falhos:
        relatorio_falhas = gerar_relatorio_falhas(todos_resultados, base_url)
        with open(arquivo_falhas, "w", encoding="utf-8") as f:
            f.write(relatorio_falhas)
        arquivos_salvos["falhas"] = arquivo_falhas
    
    return arquivos_salvos


def _criar_cabecalho(titulo: str, base_url: str) -> List[str]:
    """Cria cabeçalho padrão do relatório."""
    return [
        "=" * 80,
        titulo,
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Base URL: {base_url}",
        "=" * 80,
        ""
    ]


def _criar_descricao_testes() -> List[str]:
    """Cria seção de descrição dos testes."""
    return [
        "DESCRIÇÃO DOS TESTES:",
        "São realizados 3 tipos de teste para o método GET:",
        "1) Sem parâmetros: espera-se que retornem todos os resultados da tela",
        "2) Parâmetros válidos: espera-se que seja retornado apenas um resultado, equivalente aos parâmetros inseridos",
        "3) Parâmetros inválidos: espera-se que retorne vazio, com codRetorno 404.",
        "",
        "=" * 80,
        ""
    ]


def _criar_resumo_quantitativo(todos_resultados: List[Dict]) -> List[str]:
    """Cria resumo quantitativo dos testes."""
    total_testes = len(todos_resultados)
    testes_sucesso = sum(1 for r in todos_resultados if r.get("result", {}).get("success", False))
    testes_falha = total_testes - testes_sucesso
    
    return [
        f"Total de testes: {total_testes}",
        f"Sucessos: {testes_sucesso}",
        f"Itens a Verificar: {testes_falha}",
        "",
        "DETALHAMENTO POR ENDPOINT:",
        ""
    ]


def _criar_detalhamento_endpoints(todos_resultados: List[Dict]) -> List[str]:
    """Cria detalhamento por endpoint."""
    linhas = []
    endpoint_atual = None
    
    for teste in todos_resultados:
        if teste["endpoint"] != endpoint_atual:
            endpoint_atual = teste["endpoint"]
            linhas.append(f"\n{endpoint_atual}")
            linhas.append("-" * 80)
        
        # Simplifica nomes - mostra apenas o método HTTP para testes CRUD
        tipo_teste = teste["test_type"]
        if tipo_teste.startswith("crud_"):
            # Extrai o método HTTP (ex: crud_put_strategy -> PUT, crud_delete -> DELETE)
            # Pega a parte após "crud_" e antes do próximo "_" (se houver)
            method = tipo_teste.replace("crud_", "").split("_")[0].upper()
            tipo_teste = method
        else:
            tipo_teste = tipo_teste.replace("_", " ").title()
        
        # Verifica se o teste foi pulado
        if teste["result"].get("skipped"):
            linhas.append(f"  {tipo_teste}: PULADO")
            linhas.append(f"    {teste['result']['skip_message']}")
            continue
        
        status = "SUCESSO" if teste["result"].get("success", False) else "VERIFICAR"
        codigo_status = teste["result"].get("status_code", "N/A")
        
        # Extrai informações adicionais da resposta
        dados = teste["result"].get("data", {})
        cod_retorno = dados.get("codRetorno", "N/A")
        total_registros = dados.get("totalRegistros", "N/A")
        
        linha_info = (f"  {tipo_teste}: {status} "
                     f"(HTTP {codigo_status} - codRetorno: {cod_retorno} - "
                     f"totalRegistros: {total_registros})")
        linhas.append(linha_info)
        
        # Adiciona nota sobre limitação de tamanho de ID se existir
        metadata = teste["result"].get("metadata", {})
        if "id_truncation_note" in metadata:
            linhas.append(f"    OBSERVAÇÃO: {metadata['id_truncation_note']}")
        
        if not teste["result"].get("success", False):
            erro = teste["result"].get("error")
            if erro:
                linhas.append(f"    Erro: {erro}")
            desc_retorno = dados.get("descRetorno")
            if desc_retorno:
                linhas.append(f"    descRetorno: {desc_retorno}")
    
    return linhas


def _formatar_teste_completo(teste: Dict) -> List[str]:
    """Formata um teste completo com todos os detalhes."""
    # Simplifica nomes - mostra apenas o método HTTP para testes CRUD
    tipo_teste = teste["test_type"]
    if tipo_teste.startswith("crud_"):
        # Extrai o método HTTP (ex: crud_put_strategy -> PUT, crud_delete -> DELETE)
        # Pega a parte após "crud_" e antes do próximo "_" (se houver)
        method = tipo_teste.replace("crud_", "").split("_")[0].upper()
        tipo_teste_formatado = method
    else:
        tipo_teste_formatado = tipo_teste.replace("_", " ").title()
    
    linhas = [
        f"\nENDPOINT: {teste['endpoint']}",
        f"TIPO DE TESTE: {tipo_teste_formatado}"
    ]
    
    # Adiciona método HTTP se disponível
    if "method" in teste:
        linhas.append(f"MÉTODO: {teste['method']}")
    
    resultado = teste["result"]
    
    # Verifica se o teste foi pulado
    if resultado.get("skipped"):
        linhas.append(f"STATUS: PULADO")
        linhas.append(f"MOTIVO: {resultado['skip_message']}")
        linhas.append("-" * 80)
        return linhas
    
    # Adiciona parâmetros da requisição
    if "params" in teste and teste["params"]:
        linhas.append(f"PARÂMETROS (query): {json.dumps(teste['params'], ensure_ascii=False)}")
    
    # Adiciona body da requisição
    if "body" in teste and teste["body"]:
        linhas.append(f"BODY (formData): {json.dumps(teste['body'], ensure_ascii=False)}")
    
    linhas.append(f"STATUS HTTP: {resultado.get('status_code', 'N/A')}")
    linhas.append(f"TEMPO DE RESPOSTA: {resultado.get('response_time_ms', 'N/A')}ms")
    status_teste = "Sucesso" if resultado.get("success", False) else "Verificar"
    linhas.append(f"STATUS DO TESTE: {status_teste}")
    
    # Adiciona nota sobre limitação de tamanho de ID se existir
    metadata = resultado.get("metadata", {})
    if "id_truncation_note" in metadata:
        linhas.append(f"OBSERVAÇÃO: {metadata['id_truncation_note']}")
    
    linhas.append("RESPOSTA:")
    linhas.append(truncar_resposta(resultado["data"]))
    
    linhas.append("-" * 80)
    
    return linhas
