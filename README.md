# Ferramenta de Testes de API

Framework automatizado para testes de APIs REST que valida endpoints com diferentes cenários de parâmetros.

## Funcionalidades

- **Modo GET_ONLY**: Testa endpoints GET com três cenários: sem parâmetros, parâmetros válidos e parâmetros inválidos
- **Modo FULL_CRUD**: Testa todos os métodos HTTP (GET, POST, PUT, DELETE) em sequência para validar operações CRUD completas
- Gera relatórios detalhados e resumidos dos testes
- Delays de requisições e limites de resposta configuráveis
- Para no primeiro erro em modo FULL_CRUD para facilitar debugging

## Instalação

1. Copie `configuracao.py.example` para `configuracao.py` e configure suas credenciais de API
2. Instale as dependências: `pip install requests`
3. Execute os testes: `python executar_testes.py`

## Configuração

Crie um arquivo `configuracao.py` com:
- `API_KEY`: Sua chave de autenticação da API
- `BASE_URL`: URL base da API
- `SWAGGER_URL`: Endpoint da especificação Swagger
- `TEST_MODE`: "GET_ONLY" para testar apenas GET, "FULL_CRUD" para testar todos os métodos HTTP
- Parâmetros adicionais conforme necessário

### Modo FULL_CRUD

Quando `TEST_MODE = "FULL_CRUD"`, o sistema executa a seguinte sequência para cada endpoint:

1. **GET**: Obtém dados válidos existentes
2. **POST**: Cria um novo registro usando os dados do GET mas com um ID de teste (987154874 ou 23942835 se o primeiro já existir)
3. **PUT**: Modifica o registro criado (se PUT disponível)
4. **DELETE**: Remove o registro de teste criado (se DELETE disponível)

Se o POST falhar porque o ID já existe, o sistema tenta automaticamente com outro ID. O teste continua mesmo se PUT falhar, garantindo que o DELETE sempre execute para limpar o registro de teste.

## Relatórios

Os testes geram relatórios com timestamp:
- `relatorio_resumido_YYYYMMDD_HHMMSS.txt`: Resumo dos resultados dos testes
- `relatorio_completo_YYYYMMDD_HHMMSS.txt`: Detalhes completos incluindo respostas
- `relatorio_falhas_YYYYMMDD_HHMMSS.txt`: Apenas testes que falharam (gerado quando há falhas)
