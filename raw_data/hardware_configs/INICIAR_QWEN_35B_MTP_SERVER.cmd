@echo off
chcp 65001 >nul
title [AetherMind] Qwen 3.6 35B MoE com MTP - Servidor Web e API (Perfil: qwen35b_xeon_perf_v1)
color 0E

echo ======================================================================
echo    AETHERMIND - QWEN 3.6 35B MoE SERVER (PERFIL: qwen35b_xeon_perf_v1)
echo    VELOCIDADE: ATE ~12.2 TOKENS/S (SHORT) / ~9.8 TOKENS/S (2K)
echo    CONFIG: 12 CORES FISICOS, AFINIDADE 0x5555550, MTP DRAFT 2, KV q8_0
echo ======================================================================
echo Modelo: F:\data\models\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf
echo Servidor: http://127.0.0.1:8080
echo API OpenAI: http://127.0.0.1:8080/v1
echo ======================================================================
echo.

echo [1/3] Encerrando instancias anteriores do llama-server...
taskkill /F /IM llama-server.exe >nul 2>&1
timeout /t 1 /nobreak >nul

echo [2/3] Programando abertura do navegador apos o carregamento...
start /b cmd /c "timeout /t 15 /nobreak >nul && start http://127.0.0.1:8080"

echo [3/3] Carregando modelo MoE de 21 GB na RAM com MTP Draft 2...
echo.

start "" /affinity 5555550 /belownormal /b /wait "F:\tools\lc_b10749\llama-server.exe" ^
  -m "F:\data\models\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf" ^
  --spec-type draft-mtp ^
  --spec-draft-n-max 2 ^
  --host 127.0.0.1 ^
  --port 8080 ^
  --threads 12 ^
  -C 5555550 ^
  -ctk q8_0 ^
  -ctv q8_0 ^
  --ctx-size 4096 ^
  -np 1 ^
  --no-repack

echo.
echo Servidor encerrado.
pause

