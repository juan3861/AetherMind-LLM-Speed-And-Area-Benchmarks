@echo off
title [QWEN 3.8 Q3_K_XL] COM MTP DRAFT
color 0A

echo.
echo ============================================================
echo  Qwen 3.8 27B UD-Q3_K_XL — COM Multi-Token Prediction
echo ============================================================
echo  Modelo   : F:\data\models\Qwen3.8-27B-UD-Q3_K_XL.gguf (12.24 GB)
echo  Draft    : F:\data\models\mtp-Qwen3.8-27B-Q4_0.gguf (1.28 GB)
echo  Porta    : http://127.0.0.1:8080
echo  Dashboard: http://127.0.0.1:7860/mtp_benchmark.html
echo  Threads  : 14
echo ============================================================
echo.

echo [1/3] Encerrando instancias anteriores...
taskkill /F /IM llama-server.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/3] Abrindo dashboard no navegador...
start "" "http://127.0.0.1:7860/mtp_benchmark.html"

echo [3/3] Iniciando llama-server COM MTP na porta 8080...
echo.
"F:\tools\lc_b10749\llama-server.exe" ^
  -m "F:\data\models\Qwen3.8-27B-UD-Q3_K_XL.gguf" ^
  --model-draft "F:\data\models\mtp-Qwen3.8-27B-Q4_0.gguf" ^
  --spec-type draft-mtp ^
  --spec-draft-n-max 4 ^
  --host 127.0.0.1 ^
  --port 8080 ^
  --threads 14 ^
  --ctx-size 4096 ^
  --no-repack

echo.
echo [INFO] Servidor encerrado.
pause
