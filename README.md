# Ferramenta de Testes de API

Framework automatizado para testes de APIs REST que valida endpoints com diferentes cenários de parâmetros.

## Funcionalidades

- Testa endpoints GET com três cenários: sem parâmetros, parâmetros válidos e parâmetros inválidos
- Gera relatórios detalhados e resumidos dos testes
- Delays de requisições e limites de resposta configuráveis

## Instalação

1. Copie `configuracao.py.example` para `configuracao.py` e configure suas credenciais de API
2. Instale as dependências: `pip install requests`
3. Execute os testes: `python executar_testes.py`

## Configuração

Crie um arquivo `configuracao.py` com:
- `API_KEY`: Sua chave de autenticação da API
- `BASE_URL`: URL base da API
- `SWAGGER_URL`: Endpoint da especificação Swagger
- Parâmetros adicionais conforme necessário

## Relatórios

Os testes geram relatórios com timestamp:
- `relatorio_resumido_YYYYMMDD_HHMMSS.txt`: Resumo dos resultados dos testes
- `relatorio_completo_YYYYMMDD_HHMMSS.txt`: Detalhes completos incluindo respostas
- `relatorio_falhas_YYYYMMDD_HHMMSS.txt`: Apenas testes que falharam (gerado quando há falhas)
