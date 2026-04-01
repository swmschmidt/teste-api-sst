# Sistema de Testes API SST

Sistema automatizado para testes de endpoints da API SST com suporte a testes GET e CRUD completo.

## Estrutura do Projeto

O projeto foi reorganizado seguindo o princípio de **Separação de Responsabilidades (Separation of Concerns)**:

### Módulos Principais

#### Configuração
- **`configuracao.py`** - Configurações centralizadas (URLs, credenciais, modos de teste)

#### Clientes e Comunicação
- **`cliente_swagger.py`** - Interação com especificações Swagger/OpenAPI
- **`cliente_http.py`** - Execução de requisições HTTP (GET, POST, PUT, DELETE)

#### Construção de Dados
- **`construtor_parametros.py`** - Construção de parâmetros válidos/inválidos para testes
- **`construtor_body.py`** - Construção de bodies para requisições POST/PUT
- **`extrator_valores.py`** - Extração inteligente de valores de respostas

#### Processamento de Dados
- **`extrator_dados.py`** - Extração e parsing de dados de respostas
- **`avaliador_testes.py`** - Avaliação de sucesso/falha de testes

#### Casos Especiais
- **`substituicoes_endpoint.py`** - Tratamento de endpoints com requisitos específicos

#### Execução de Testes
- **`cenarios_teste.py`** - Cenários de teste (GET simples e CRUD completo)
- **`executar_testes.py`** - Orquestrador principal de execução
- **`servidor_flask.py`** - Servidor Flask para execução via API REST
- **`index.html`** - Interface web para controle dos testes
- **`iniciar_sistema.bat`** - Script para inicialização automática do sistema

#### Relatórios
- **`gerador_relatorios.py`** - Geração e formatação de relatórios

## Como Usar

### 1. Configuração Inicial

Instale as dependências:
```bash
pip install -r requirements.txt
```

Copie o arquivo de exemplo e configure:
```bash
cp configuracao.py.example configuracao.py
```

Edite `configuracao.py` com suas credenciais e preferências:
```python
API_KEY = "sua_chave_aqui"
BASE_URL = "http://sua-api.com"
TEST_MODE = "GET_ONLY"  # ou "FULL_CRUD"
```

### 2. Executar Testes

#### Modo Direto (Linha de Comando)
```bash
python executar_testes.py
```

#### Modo Servidor (Via API REST)

**Opção 1 - Inicialização Automática (Recomendado):**
```bash
iniciar_sistema.bat
```
Este script irá:
- Iniciar o servidor Flask automaticamente
- Abrir a interface web no navegador
- Manter o servidor rodando em segundo plano

**Opção 2 - Inicialização Manual:**
```bash
python servidor_flask.py
```
Depois abra o arquivo `index.html` no navegador para acessar a interface gráfica interativa.

O servidor estará disponível em `http://localhost:5000` com os seguintes endpoints:

**POST /api/testes/executar** - Inicia execução de testes em background
```bash
curl -X POST http://localhost:5000/api/testes/executar
```
Resposta:
```json
{
  "sucesso": true,
  "mensagem": "Execução de testes iniciada",
  "estado": "iniciado"
}
```

**GET /api/testes/status** - Verifica status da execução atual
```bash
curl http://localhost:5000/api/testes/status
```
Resposta (em execução):
```json
{
  "em_execucao": true,
  "ultima_execucao": "2026-02-27T10:30:00",
  "erro": null
}
```

**GET /api/testes/resultado** - Obtém resultado da última execução
```bash
curl http://localhost:5000/api/testes/resultado
```
Resposta:
```json
{
  "sucesso": true,
  "ultima_execucao": "2026-02-27T10:32:15",
  "arquivos": {
    "resumido": "relatorio_resumido_20260227_103215.txt",
    "completo": "relatorio_completo_20260227_103215.txt"
  }
}
```

**GET /api/saude** - Health check do servidor
```bash
curl http://localhost:5000/api/saude
```

## Funcionalidades

### Modo GET_ONLY (Padrão)
Testa endpoints GET com três cenários:
1. **Sem parâmetros** - Espera retornar todos os resultados
2. **Parâmetros válidos** - Espera retornar 1 resultado específico
3. **Parâmetros inválidos** - Espera retornar 404

### Modo FULL_CRUD
Executa sequência completa para cada endpoint:
1. **GET** - Obtém dados válidos
2. **POST** - Cria novo registro com ID de teste (987154874 ou 23942835)
3. **PUT** - Modifica o registro criado (se disponível)
4. **DELETE** - Remove o registro de teste (se disponível)

Se o POST falhar porque o ID já existe, o sistema tenta automaticamente com outro ID. O teste continua mesmo se PUT falhar, garantindo que o DELETE sempre execute para limpar o registro de teste.

## Relatórios Gerados

Após a execução, são gerados automaticamente:

- **`relatorio_resumido_YYYYMMDD_HHMMSS.txt`** - Visão geral com estatísticas
- **`relatorio_completo_YYYYMMDD_HHMMSS.txt`** - Detalhes completos de todos os testes
- **`relatorio_verificar_YYYYMMDD_HHMMSS.txt`** - Apenas testes que precisam ser verificados (se houver)

## Arquitetura

```
Fluxo de Execução:
executar_testes.py
    ↓
cliente_swagger.py (obtém especificação)
    ↓
cenarios_teste.py (executa testes)
    ├→ cliente_http.py (chamadas HTTP)
    ├→ construtor_parametros.py (constrói parâmetros)
    │   ├→ extrator_valores.py (extrai valores)
    │   └→ substituicoes_endpoint.py (casos especiais)
    ├→ construtor_body.py (constrói bodies)
    ├→ extrator_dados.py (processa respostas)
    └→ avaliador_testes.py (avalia resultados)
    ↓
gerador_relatorios.py (gera relatórios)
```

## Princípios de Design

### Separação de Responsabilidades
Cada módulo tem uma responsabilidade clara e única:
- **Clientes** apenas fazem requisições
- **Builders** apenas constroem dados
- **Extractors** apenas extraem informações
- **Evaluators** apenas avaliam resultados

### Extensibilidade
Fácil adicionar novos:
- Tipos de teste (em `cenarios_teste.py`)
- Formatos de relatório (em `gerador_relatorios.py`)
- Definicoes de endpoints (em `substituicoes_endpoint.py`)

### Manutenibilidade
- Código limpo e bem documentado
- Funções pequenas e focadas
- Nomes descritivos em português
- Comentários explicativos

## Configurações Avançadas

### Critérios de Sucesso dos Testes
Configure os valores esperados para determinar sucesso/falha:
```python
CRITERIOS_SUCESSO = {
    "parametros_validos": {
        "codRetorno": "200",
        "totalRegistros": "1"
    },
    "parametros_invalidos": {
        "codRetorno": "404"
    },
    "crud_delete": {
        "codRetorno": "200",
        "descRetorno_contem": "apagados com sucesso"
    }
    # ... outros critérios
}
```

### Limite de Endpoints
```python
ENDPOINT_LIMIT = 5  # Testa apenas os 5 primeiros endpoints
ENDPOINT_LIMIT = 0  # Testa todos os endpoints
```

### Testar Apenas um Endpoint Específico
```python
# Testar apenas o endpoint R050
ENDPOINT_ESPECIFICO = "CBR_API_REST_SST_R050"

# Testar todos os endpoints (padrão)
ENDPOINT_ESPECIFICO = None
```

### Delay entre Requisições
```python
REQUEST_DELAY_SECONDS = 1  # 1 segundo entre cada requisição
```

### Tamanho Máximo de Resposta nos Relatórios
```python
MAX_RESPONSE_SIZE = 5000  # Trunca respostas maiores que 5000 caracteres
```

### Definicoes de Endpoints

O módulo `definicoes_endpoints.py` é o mecanismo padrão para definir dados e comportamento de teste por endpoint.
Ele centraliza parâmetros e regras de execução para GET, POST, PUT e DELETE.

Configure as definições em `definicoes_endpoints.py` (importado por `configuracao.py`):

```python
DEFINICOES_ENDPOINTS = {
    "CBR_API_REST_SST_R082H": {
        "pular_sem_parametros": True,  # Pula teste sem parâmetros
        "mensagem_pular": "Não há teste sem parâmetros para este endpoint. P_SCO_ID_HR é obrigatório.",
        "substituicoes": {
            "GET": {  # Definições específicas para GET
                "P_SCO_ID_HR": "10609",
                "P_SCO_ID_DISABILITY": "01",
                "P_SCO_DT_START": "2025-10-09"
            },
            "POST": {  # Definições específicas para POST
                "P_SCO_ID_HR": "10610"
            }
        }
    },
    "CBR_API_REST_SST_R050": {
        "validacao_comparativa": True  # Usa validação comparativa de totalRegistros
    }
}
```

**Opções disponíveis:**
- **`pular_sem_parametros`** - Se `True`, pula o teste sem parâmetros
- **`mensagem_pular`** - Mensagem explicativa quando pulado
- **`validacao_comparativa`** - Se `True`, aplica validação comparativa de totalRegistros
- **`substituicoes`** - Dict de parâmetros por método HTTP (GET, POST, PUT, DELETE)

Cada método pode ter suas próprias definições, permitindo valores diferentes para GET, POST, PUT e DELETE.

## Endpoints Especiais

Alguns endpoints requerem tratamento especial (configurados em `DEFINICOES_ENDPOINTS`):

- **R082H** - Requer parâmetros obrigatórios (P_SCO_ID_HR, P_SCO_ID_DISABILITY, P_SCO_DT_START)
- **R057B/R057D** - Requer P_SCO_ID_RISK_FACTOR específico ("AG1")

## Instalação

1. Instale as dependências: `pip install -r requirements.txt`
2. Copie `configuracao.py.example` para `configuracao.py` e configure suas credenciais de API
3. Execute os testes:
   - **Mais fácil**: Execute `iniciar_sistema.bat` (abre tudo automaticamente)
   - Modo direto: `python executar_testes.py`
   - Modo servidor: `python servidor_flask.py` (depois abra `index.html` no navegador)

## Contribuindo

Para adicionar suporte a novos cenários de teste:
1. Implemente a lógica em `cenarios_teste.py`
2. Adicione avaliadores específicos em `avaliador_testes.py`
3. Configure definicoes_endpoints se necessário em `definicoes_endpoints.py`



