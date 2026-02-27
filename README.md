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

#### Relatórios
- **`gerador_relatorios.py`** - Geração e formatação de relatórios

## Como Usar

### 1. Configuração Inicial

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

```bash
python executar_testes.py
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
- Overrides de endpoints (em `substituicoes_endpoint.py`)

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

### Overrides de Endpoints

Configure valores hardcoded para endpoints específicos em `configuracao.py`:

```python
ENDPOINT_OVERRIDES = {
    "CBR_API_REST_SST_R082H": {
        "skip_no_params": True,  # Pula teste sem parâmetros
        "skip_message": "Não há teste sem parâmetros para este endpoint. P_SCO_ID_HR é obrigatório.",
        "overrides": {
            "GET": {  # Overrides específicos para GET
                "P_SCO_ID_HR": "10609",
                "P_SCO_ID_DISABILITY": "01",
                "P_SCO_DT_START": "2025-10-09"
            },
            "POST": {  # Overrides específicos para POST
                "P_SCO_ID_HR": "10610"
            }
        }
    },
    "CBR_API_REST_SST_R050": {
        "special_validation": True  # Usa validação especial
    }
}
```

**Opções disponíveis:**
- **`skip_no_params`** - Se `True`, pula o teste sem parâmetros
- **`skip_message`** - Mensagem explicativa quando pulado
- **`special_validation`** - Se `True`, aplica validação especial de totalRegistros
- **`overrides`** - Dict de parâmetros por método HTTP (GET, POST, PUT, DELETE)

Cada método pode ter seus próprios overrides, permitindo valores diferentes para GET, POST, PUT e DELETE.

## Endpoints Especiais

Alguns endpoints requerem tratamento especial (configurados em `ENDPOINT_OVERRIDES`):

- **R082H** - Requer parâmetros obrigatórios (P_SCO_ID_HR, P_SCO_ID_DISABILITY, P_SCO_DT_START)
- **R057B/R057D** - Requer P_SCO_ID_RISK_FACTOR específico ("AG1")

## Instalação

1. Copie `configuracao.py.example` para `configuracao.py` e configure suas credenciais de API
2. Instale as dependências: `pip install requests`
3. Execute os testes: `python executar_testes.py`

## Contribuindo

Para adicionar suporte a novos cenários de teste:
1. Implemente a lógica em `cenarios_teste.py`
2. Adicione avaliadores específicos em `avaliador_testes.py`
3. Configure overrides se necessário em `ENDPOINT_OVERRIDES` no `configuracao.py`

