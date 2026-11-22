@echo off
title [MTP] Qwen 3.6 27B — COM Multi-Token Prediction
color 0A

echo.
echo ============================================================
echo  MTP ATIVADO — Qwen 3.6 27B + draft-mtp n=4
echo ============================================================
echo  Modelo  : Qwen3.6-27B-Q4_K_M.gguf  (15.93 GB)
echo  Servidor: http://127.0.0.1:8080
echo  Dashboard: http://127.0.0.1:7860/mtp_benchmark.html
echo  Spec    : --spec-type draft-mtp --spec-draft-n-max 4
echo ============================================================
echo.

:: Mata processos anteriores
echo [1/4] Encerrando instancias anteriores...
taskkill /F /IM llama-server.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: Inicia o servidor de arquivos Python (para resolver CORS)
echo [2/4] Iniciando servidor web local na porta 7860...
start "" /min cmd /c "python -m http.server 7860 --directory F:\rotor-llm"

:: Aguarda o servidor de arquivos subir
timeout /t 2 /nobreak >nul

:: Abre o dashboard no browser
echo [3/4] Abrindo dashboard no navegador...
start "" "http://127.0.0.1:7860/mtp_benchmark.html"

:: Inicia o llama-server COM MTP
echo [4/4] Iniciando llama-server COM MTP na porta 8080...
echo      (aguarde o modelo carregar, pode levar 1-2 minutos)
echo.
"F:\tools\lc_b10749\llama-server.exe" ^
  -m "F:\data\models\Qwen3.6-27B-Q4_K_M.gguf" ^
  --host 127.0.0.1 ^
  --port 8080 ^
  --threads 14 ^
  --ctx-size 2048 ^
  --no-repack ^
  --spec-type draft-mtp ^
  --spec-draft-n-max 4 ^
  --log-disable

echo.
echo [ENCERRADO] Servidor MTP parado.
pause
