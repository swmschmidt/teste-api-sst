@echo off
REM Script para iniciar servidor Flask e interface web
REM Sistema de Testes API SST

echo ================================================
echo   Sistema de Testes API SST
echo ================================================
echo.
echo Iniciando servidor Flask...
echo.

REM Inicia o servidor Flask em uma nova janela
start "Servidor Flask - Testes API SST" python servidor_flask.py

REM Aguarda 3 segundos para o servidor iniciar
echo Aguardando servidor iniciar...
timeout /t 3 /nobreak >nul

REM Abre a interface web no navegador padrão
echo Abrindo interface web...
start index.html

echo.
echo ================================================
echo Interface web aberta no navegador!
echo O servidor está rodando em segundo plano.
echo ================================================
echo.
echo Pressione qualquer tecla para sair...
echo (Nota: O servidor continuará rodando)
pause >nul
