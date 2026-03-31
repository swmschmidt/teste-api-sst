"""
Servidor Flask para execução de testes via API REST.
Permite disparar testes através de endpoint HTTP.
"""
from flask import Flask, jsonify, request, Response, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from threading import Thread, Lock
from datetime import datetime
import os
import sys
from io import StringIO
import json

from executar_testes import main as executar_testes_completo
from cliente_swagger import obter_especificacao_api, extrair_endpoints_get
from configuracao import SWAGGER_URL, BASE_URL, API_KEY

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Controle de estado da execução
estado_execucao = {
    "em_execucao": False,
    "ultima_execucao": None,
    "ultimo_resultado": None,
    "erro": None,
    "cancelar": False  # Flag para cancelamento
}
trava_execucao = Lock()

# Armazenar endpoints e seus status
endpoints_data = {
    "endpoints": [],
    "status": {}  # {path: "untested" | "success" | "failure"}
}
endpoints_lock = Lock()

# Buffer para logs do console
console_logs = []
console_lock = Lock()
original_stdout = sys.stdout
original_stderr = sys.stderr


class ConsoleCapture:
    """Captura saídas do console e emite via WebSocket."""
    def __init__(self, original_stream):
        self.original_stream = original_stream
        self.buffer = StringIO()
    
    def write(self, text):
        self.original_stream.write(text)
        if text.strip():  # Ignora linhas vazias
            with console_lock:
                console_logs.append({
                    "timestamp": datetime.now().isoformat(),
                    "message": text
                })
                # Limita o buffer a 1000 mensagens
                if len(console_logs) > 1000:
                    console_logs.pop(0)
            
            # Emite via WebSocket
            try:
                socketio.emit('console_output', {'message': text}, namespace='/')
            except:
                pass  # Ignora erros de WebSocket
    
    def flush(self):
        self.original_stream.flush()


def adicionar_log(mensagem):
    """Adiciona uma mensagem ao log do console e emite via WebSocket."""
    with console_lock:
        console_logs.append({
            "timestamp": datetime.now().isoformat(),
            "message": mensagem
        })
        if len(console_logs) > 1000:
            console_logs.pop(0)
    
    # Emite via WebSocket
    try:
        socketio.emit('console_output', {'message': mensagem}, namespace='/')
    except:
        pass  # Ignora erros de WebSocket
    
    # Também imprime no console
    print(mensagem, end='')


def atualizar_status_endpoint(path, status, x_objeto_api=None):
    """Atualiza o status de um endpoint e notifica via WebSocket."""
    with endpoints_lock:
        if path in endpoints_data["status"] or status == "testing":
            endpoints_data["status"][path] = status
            
            # Emite atualização via WebSocket
            try:
                socketio.emit('endpoint_status_update', {
                    'path': path,
                    'status': status,
                    'x_objeto_api': x_objeto_api
                }, namespace='/')
            except:
                pass


def enviar_resultado_teste(path, resultado):
    """Envia resultado de teste individual via WebSocket."""
    try:
        socketio.emit('test_result', {
            'path': path,
            'result': resultado
        }, namespace='/')
    except:
        pass  # Ignora erros de WebSocket


def executar_testes_em_background():
    """Executa os testes em background e atualiza o estado."""
    global estado_execucao
    
    # Redireciona stdout/stderr para capturar output
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = ConsoleCapture(original_stdout)
    sys.stderr = ConsoleCapture(original_stderr)
    
    try:
        adicionar_log("[SYSTEM] Iniciando execução de testes...\n")
        
        # Configura callback para atualização de status, resultado e cancelamento
        import executar_testes
        executar_testes.STATUS_CALLBACK = atualizar_status_endpoint
        executar_testes.RESULT_CALLBACK = enviar_resultado_teste
        executar_testes.SHOULD_CANCEL = lambda: estado_execucao.get("cancelar", False)
        
        arquivos_salvos = executar_testes_completo()
        
        # Verifica se foi cancelado
        with trava_execucao:
            if estado_execucao["cancelar"]:
                adicionar_log("[SYSTEM] Testes cancelados pelo usuário!\n")
                estado_execucao["erro"] = "Cancelado pelo usuário"
            else:
                adicionar_log("[SYSTEM] Testes concluídos com sucesso!\n")
                estado_execucao["ultimo_resultado"] = arquivos_salvos
                estado_execucao["erro"] = None
            
            estado_execucao["em_execucao"] = False
            estado_execucao["ultima_execucao"] = datetime.now().isoformat()
            estado_execucao["cancelar"] = False
            
    except Exception as e:
        adicionar_log(f"[ERROR] Erro durante execução dos testes: {str(e)}\n")
        import traceback
        adicionar_log(traceback.format_exc())
        with trava_execucao:
            estado_execucao["em_execucao"] = False
            estado_execucao["ultima_execucao"] = datetime.now().isoformat()
            estado_execucao["ultimo_resultado"] = None
            estado_execucao["erro"] = str(e)
            estado_execucao["cancelar"] = False
    finally:
        # Restaura stdout/stderr
        sys.stdout = original_stdout
        sys.stderr = original_stderr


@app.route('/api/testes/executar', methods=['POST'])
def iniciar_testes():
    """
    Inicia a execução dos testes em background.
    
    Returns:
        JSON com status da operação
    """
    with trava_execucao:
        if estado_execucao["em_execucao"]:
            return jsonify({
                "sucesso": False,
                "mensagem": "Já existe uma execução de testes em andamento",
                "estado": "em_execucao"
            }), 409
        
        estado_execucao["em_execucao"] = True
        estado_execucao["erro"] = None
        estado_execucao["cancelar"] = False  # Reseta flag de cancelamento
    
    adicionar_log("[SYSTEM] Execução de testes solicitada...\n")
    
    thread = Thread(target=executar_testes_em_background)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "sucesso": True,
        "mensagem": "Execução de testes iniciada",
        "estado": "iniciado"
    }), 202


@app.route('/api/testes/cancelar', methods=['POST'])
def cancelar_testes():
    """
    Cancela a execução de testes em andamento.
    
    Returns:
        JSON com status da operação
    """
    with trava_execucao:
        if not estado_execucao["em_execucao"]:
            return jsonify({
                "sucesso": False,
                "mensagem": "Nenhuma execução em andamento para cancelar"
            }), 400
        
        estado_execucao["cancelar"] = True
    
    adicionar_log("[SYSTEM] Solicitação de cancelamento recebida...\n")
    
    return jsonify({
        "sucesso": True,
        "mensagem": "Cancelamento solicitado. Aguardando conclusão do teste atual..."
    }), 200


@app.route('/api/testes/status', methods=['GET'])
def obter_status():
    """
    Retorna o status atual da execução de testes.
    
    Returns:
        JSON com informações de status
    """
    with trava_execucao:
        resposta = {
            "em_execucao": estado_execucao["em_execucao"],
            "ultima_execucao": estado_execucao["ultima_execucao"],
            "erro": estado_execucao["erro"]
        }
        
        if estado_execucao["ultimo_resultado"]:
            resposta["ultimo_resultado"] = {
                "arquivos": estado_execucao["ultimo_resultado"],
                "mensagem": "Testes concluídos com sucesso"
            }
    
    return jsonify(resposta), 200


@app.route('/api/testes/resultado', methods=['GET'])
def obter_resultado():
    """
    Retorna o resultado da última execução.
    
    Returns:
        JSON com resultado detalhado
    """
    with trava_execucao:
        if estado_execucao["em_execucao"]:
            return jsonify({
                "sucesso": False,
                "mensagem": "Testes ainda em execução"
            }), 409
        
        if estado_execucao["erro"]:
            return jsonify({
                "sucesso": False,
                "mensagem": "Última execução terminou com erro",
                "erro": estado_execucao["erro"]
            }), 500
        
        if not estado_execucao["ultimo_resultado"]:
            return jsonify({
                "sucesso": False,
                "mensagem": "Nenhuma execução encontrada"
            }), 404
        
        return jsonify({
            "sucesso": True,
            "ultima_execucao": estado_execucao["ultima_execucao"],
            "arquivos": estado_execucao["ultimo_resultado"]
        }), 200


@app.route('/api/saude', methods=['GET'])
def verificar_saude():
    """
    Endpoint de health check.
    
    Returns:
        JSON confirmando que o servidor está ativo
    """
    return jsonify({
        "status": "ativo",
        "servico": "API de Testes SST",
        "versao": "1.0"
    }), 200


@app.route('/api/swagger/carregar', methods=['POST'])
def carregar_swagger():
    """
    Carrega a especificação Swagger e extrai os endpoints.
    
    Returns:
        JSON com lista de endpoints e suas informações
    """
    try:
        adicionar_log("[SYSTEM] Carregando especificação Swagger...\n")
        spec = obter_especificacao_api(SWAGGER_URL)
        from cliente_swagger import extrair_endpoints_todos
        endpoints = extrair_endpoints_todos(spec)
        
        with endpoints_lock:
            endpoints_data["endpoints"] = endpoints
            # Inicializa todos como "untested"
            for endpoint in endpoints:
                path = endpoint["path"]
                if path not in endpoints_data["status"]:
                    endpoints_data["status"][path] = "untested"
        
        adicionar_log(f"[SYSTEM] {len(endpoints)} endpoints carregados com sucesso!\n")
        
        return jsonify({
            "sucesso": True,
            "mensagem": f"{len(endpoints)} endpoints carregados",
            "total": len(endpoints)
        }), 200
        
    except Exception as e:
        adicionar_log(f"[ERROR] Erro ao carregar Swagger: {str(e)}\n")
        return jsonify({
            "sucesso": False,
            "mensagem": f"Erro ao carregar Swagger: {str(e)}"
        }), 500


@app.route('/api/endpoints', methods=['GET'])
def obter_endpoints():
    """
    Retorna a lista de endpoints com seus status.
    
    Returns:
        JSON com lista de endpoints
    """
    with endpoints_lock:
        endpoints_com_status = []
        for endpoint in endpoints_data["endpoints"]:
            endpoints_com_status.append({
                "path": endpoint["path"],
                "x_objeto_api": endpoint["x_objeto_api"],
                "summary": endpoint["summary"],
                "methods": endpoint.get("methods", {}),
                "status": endpoints_data["status"].get(endpoint["path"], "untested")
            })
        
        return jsonify({
            "sucesso": True,
            "endpoints": endpoints_com_status,
            "total": len(endpoints_com_status)
        }), 200


@app.route('/api/endpoint/<path:endpoint_path>', methods=['GET'])
def obter_detalhes_endpoint(endpoint_path):
    """
    Retorna os detalhes completos de um endpoint específico.
    
    Args:
        endpoint_path: Caminho do endpoint
        
    Returns:
        JSON com detalhes do endpoint incluindo parâmetros por método HTTP
    """
    with endpoints_lock:
        # Busca o endpoint
        endpoint = None
        for ep in endpoints_data["endpoints"]:
            if ep["path"] == endpoint_path or ep["path"] == f"/{endpoint_path}":
                endpoint = ep
                break
        
        if not endpoint:
            return jsonify({
                "sucesso": False,
                "mensagem": "Endpoint não encontrado"
            }), 404
        
        # Extrai parâmetros organizados por método HTTP
        methods_info = endpoint.get("methods", {})
        
        return jsonify({
            "sucesso": True,
            "endpoint": endpoint,
            "methods": methods_info,
            "status": endpoints_data["status"].get(endpoint["path"], "untested")
        }), 200


@app.route('/api/teste/manual', methods=['POST'])
def executar_teste_manual():
    """
    Executa um teste manual em um endpoint com parâmetros personalizados.
    
    Request JSON:
        {
            "path": "/api/endpoint",
            "method": "GET",
            "parameters": {"param1": "value1"}
        }
        
    Returns:
        JSON com resultado do teste
    """
    try:
        dados = request.get_json()
        
        if not dados or 'path' not in dados:
            return jsonify({
                "sucesso": False,
                "mensagem": "Parâmetro 'path' é obrigatório"
            }), 400
        
        endpoint_path = dados['path']
        method = dados.get('method', 'GET').upper()
        parameters = dados.get('parameters', {})
        consumes = dados.get('consumes', [])
        
        adicionar_log(f"[MANUAL] Executando teste manual: {method} {endpoint_path}\n")
        adicionar_log(f"[MANUAL] Parâmetros: {json.dumps(parameters, ensure_ascii=False)}\n")
        if consumes:
            adicionar_log(f"[MANUAL] Content-Type: {consumes}\n")
        
        # Importa o cliente HTTP
        from cliente_http import chamar_api, construir_headers
        from configuracao import BASE_URL, API_KEY, HEADERS_DEFAULT
        
        headers = construir_headers(API_KEY, HEADERS_DEFAULT)
        
        # Executa a requisição usando chamar_api (calcula response_time_ms automaticamente)
        if method == 'GET' or method == 'DELETE':
            # Para GET/DELETE, parameters são query params
            resultado = chamar_api(BASE_URL, endpoint_path, headers, params=parameters, metodo=method, consumes=consumes)
        else:
            # Para POST/PUT, parameters são body
            resultado = chamar_api(BASE_URL, endpoint_path, headers, body=parameters, metodo=method, consumes=consumes)
        
        # Avalia sucesso usando os mesmos critérios dos testes automatizados
        from avaliador_testes import avaliar_sucesso_teste
        
        # Mapeia método HTTP para tipo de teste
        test_type_map = {
            'GET': 'crud_get',
            'POST': 'crud_post',
            'PUT': 'crud_put',
            'DELETE': 'crud_delete'
        }
        tipo_teste = test_type_map.get(method, 'crud_get')
        
        # Usa a mesma função de avaliação dos testes automatizados
        resultado = avaliar_sucesso_teste(
            resultado, 
            tipo_teste,
            metodo=method,
            body_enviado=parameters if method in ['POST', 'PUT'] else None
        )
        
        # Log do resultado
        if resultado["success"]:
            adicionar_log(f"[SUCCESS] Status: {resultado['status_code']}\n")
            adicionar_log(f"[SUCCESS] Tempo de resposta: {resultado['response_time_ms']}ms\n")
        else:
            adicionar_log(f"[WARNING] Status: {resultado['status_code']}\n")
        
        if resultado.get("data"):
            adicionar_log(f"[RESPONSE] {json.dumps(resultado['data'], ensure_ascii=False, indent=2)}\n")
        
        if resultado.get("error"):
            adicionar_log(f"[ERROR] Erro na requisição: {resultado['error']}\n")
        
        return jsonify({
            "sucesso": True,
            "resultado": resultado
        }), 200
    
    except Exception as e:
        adicionar_log(f"[ERROR] Erro ao executar teste manual: {str(e)}\n")
        return jsonify({
            "sucesso": False,
            "mensagem": f"Erro ao executar teste: {str(e)}"
        }), 500


@app.route('/api/migracao/config', methods=['GET'])
def obter_config_migracao():
    return jsonify({
        "sucesso": True,
        "base_url_padrao": BASE_URL,
        "api_key_padrao": API_KEY
    }), 200


@app.route('/api/migracao/chamada', methods=['POST'])
def executar_chamada_migracao():
    try:
        dados = request.get_json() or {}

        endpoint_path = dados.get('path')
        if not endpoint_path:
            return jsonify({
                "sucesso": False,
                "mensagem": "Parâmetro 'path' é obrigatório"
            }), 400

        method = dados.get('method', 'GET').upper()
        base_url = dados.get('base_url') or BASE_URL
        query_params = dados.get('query_params', {})
        body = dados.get('body', {})
        consumes = dados.get('consumes', [])

        from cliente_http import chamar_api, construir_headers
        from configuracao import HEADERS_DEFAULT

        api_key = dados.get('api_key') or API_KEY

        headers = construir_headers(api_key, HEADERS_DEFAULT)

        if method in ['GET', 'DELETE']:
            resultado = chamar_api(
                base_url,
                endpoint_path,
                headers,
                params=query_params,
                metodo=method,
                consumes=consumes
            )
        else:
            resultado = chamar_api(
                base_url,
                endpoint_path,
                headers,
                body=body,
                metodo=method,
                consumes=consumes
            )

        return jsonify({
            "sucesso": True,
            "resultado": resultado,
            "request": {
                "base_url": base_url,
                "path": endpoint_path,
                "method": method,
                "query_params": query_params,
                "body": body
            }
        }), 200
    except Exception as e:
        return jsonify({
            "sucesso": False,
            "mensagem": f"Erro ao executar chamada de migração: {str(e)}"
        }), 500


@app.route('/api/relatorios/download/<filename>', methods=['GET'])
def download_relatorio(filename):
    """
    Endpoint para download de arquivos de relatório.
    
    Args:
        filename: Nome do arquivo de relatório
        
    Returns:
        Arquivo de relatório para download
    """
    try:
        # Sanitiza o nome do arquivo para evitar path traversal
        filename = os.path.basename(filename)
        
        # Verifica se o arquivo existe
        if not os.path.exists(filename):
            return jsonify({
                "sucesso": False,
                "mensagem": "Arquivo não encontrado"
            }), 404
        
        # Envia o arquivo para download
        return send_file(
            filename,
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain'
        )
    
    except Exception as e:
        return jsonify({
            "sucesso": False,
            "mensagem": f"Erro ao baixar arquivo: {str(e)}"
        }), 500


@app.route('/api/console/logs', methods=['GET'])
def obter_logs():
    """
    Retorna os logs do console.
    
    Returns:
        JSON com lista de logs
    """
    with console_lock:
        return jsonify({
            "sucesso": True,
            "logs": console_logs.copy()
        }), 200


@app.route('/api/console/limpar', methods=['POST'])
def limpar_logs():
    """
    Limpa os logs do console.
    
    Returns:
        JSON confirmando limpeza
    """
    with console_lock:
        console_logs.clear()
    
    return jsonify({
        "sucesso": True,
        "mensagem": "Logs limpos"
    }), 200


@app.route('/api/relatorios/gerar', methods=['POST'])
def gerar_relatorios():
    """
    Gera os relatórios dos testes executados.
    Aceita resultados do frontend ou usa os resultados dos testes automáticos.
    
    Request JSON (opcional):
        resultados: Lista de resultados de testes do frontend
    
    Returns:
        JSON com informações sobre os relatórios gerados
    """
    try:
        # Verifica se há resultados enviados pelo frontend
        request_data = request.get_json() if request.is_json else None
        resultados_frontend = request_data.get('resultados', []) if request_data else []
        
        if resultados_frontend:
            # Usa resultados do frontend (incluindo testes manuais)
            adicionar_log(f"[SYSTEM] Gerando relatórios com {len(resultados_frontend)} resultados do frontend...\n")
            
            from gerador_relatorios import salvar_relatorios
            from configuracao import BASE_URL
            
            # Transforma resultados do frontend para o formato esperado pelo gerador
            # O frontend envia estrutura flat, mas o gerador espera resultado aninhado em "result"
            resultados_formatados = []
            for resultado in resultados_frontend:
                resultado_formatado = {
                    "endpoint": resultado.get("endpoint", ""),
                    "test_type": resultado.get("test_type", "manual"),
                    "method": resultado.get("method", ""),
                    "params": resultado.get("params", {}),
                    "body": resultado.get("body", {}),
                    "result": {
                        "success": resultado.get("success", False),
                        "status_code": resultado.get("status_code"),
                        "response_time_ms": resultado.get("response_time_ms"),
                        "data": resultado.get("data"),
                        "error": resultado.get("error"),
                        "skipped": resultado.get("skipped", False),
                        "skip_message": resultado.get("skip_message", ""),
                        "metadata": resultado.get("metadata", {})
                    }
                }
                resultados_formatados.append(resultado_formatado)
            
            arquivos_salvos = salvar_relatorios(resultados_formatados, BASE_URL)
            
            # Atualiza o estado para que o relatório fique disponível
            with trava_execucao:
                estado_execucao["ultimo_resultado"] = arquivos_salvos
            
            adicionar_log("[SUCCESS] Relatórios gerados com sucesso!\n")
            
            return jsonify({
                "sucesso": True,
                "mensagem": "Relatórios gerados com resultados mais recentes",
                "arquivos": arquivos_salvos,
                "download_urls": {
                    "resumido": f"/api/relatorios/download/{os.path.basename(arquivos_salvos['resumido'])}",
                    "completo": f"/api/relatorios/download/{os.path.basename(arquivos_salvos['completo'])}",
                    "falhas": f"/api/relatorios/download/{os.path.basename(arquivos_salvos['falhas'])}" if arquivos_salvos.get('falhas') else None
                }
            }), 200
            
        else:
            # Usa resultados dos testes automáticos (comportamento original)
            with trava_execucao:
                if estado_execucao["em_execucao"]:
                    return jsonify({
                        "sucesso": False,
                        "mensagem": "Testes ainda em execução"
                    }), 409
                
                if not estado_execucao["ultimo_resultado"]:
                    return jsonify({
                        "sucesso": False,
                        "mensagem": "Nenhum resultado disponível para gerar relatório"
                    }), 404
                
                adicionar_log("[SYSTEM] Retornando relatórios dos testes automáticos...\n")
                
                return jsonify({
                    "sucesso": True,
                    "mensagem": "Relatórios disponíveis",
                    "arquivos": estado_execucao["ultimo_resultado"]
                }), 200
                
    except Exception as e:
        adicionar_log(f"[ERROR] Erro ao gerar relatórios: {str(e)}\n")
        return jsonify({
            "sucesso": False,
            "mensagem": f"Erro ao gerar relatórios: {str(e)}"
        }), 500


@app.route('/', methods=['GET'])
def rota_raiz():
    """
    Rota raiz com informações sobre os endpoints disponíveis.
    
    Returns:
        JSON com documentação básica
    """
    return jsonify({
        "servico": "API de Testes SST",
        "endpoints": {
            "POST /api/testes/executar": "Inicia execução de testes",
            "GET /api/testes/status": "Verifica status da execução",
            "GET /api/testes/resultado": "Obtém resultado da última execução",
            "GET /api/saude": "Health check do servidor"
        }
    }), 200


@socketio.on('connect')
def handle_connect():
    """Cliente WebSocket conectado."""
    print('Cliente WebSocket conectado')
    emit('connected', {'message': 'Conectado ao servidor'})


@socketio.on('disconnect')
def handle_disconnect():
    """Cliente WebSocket desconectado."""
    print('Cliente WebSocket desconectado')


if __name__ == '__main__':
    print("=" * 60)
    print("Servidor de Testes SST")
    print("=" * 60)
    print()
    print("Endpoints disponíveis:")
    print("  POST http://localhost:5000/api/testes/executar")
    print("  GET  http://localhost:5000/api/testes/status")
    print("  GET  http://localhost:5000/api/testes/resultado")
    print("  GET  http://localhost:5000/api/saude")
    print()
    print("WebSocket habilitado para console em tempo real")
    print()
    print("Pressione CTRL+C para encerrar")
    print("=" * 60)
    print()
    
    socketio.run(app, host='127.0.0.1', port=5000, debug=False, allow_unsafe_werkzeug=True)
