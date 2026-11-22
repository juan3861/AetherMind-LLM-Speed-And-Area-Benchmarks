@echo off
chcp 65001 >nul
title [AetherMind] Qwen 3.8 27B UD-IQ3_XXS - Híbrido GPU + CPU
color 0D

echo ======================================================================
echo    AETHERMIND - QWEN 3.8 27B UD-IQ3_XXS (HÍBRIDO RX 580 + XEON)
echo    DIVISÃO DE PESOS: 30 CAMADAS NA GPU RX 580 + RESTANTE NA CPU
echo ======================================================================
echo Modelo: F:\data\models\Qwen3.8-27B-UD-IQ3_XXS.gguf (10.18 GB)
echo Servidor: http://127.0.0.1:8080
echo API OpenAI: http://127.0.0.1:8080/v1
echo Prompt Processing: ~15.4 tokens/segundo (2.16x mais rápido via GPU)
echo ======================================================================
echo.

echo [1/3] Encerrando instâncias anteriores do llama-server...
taskkill /F /IM llama-server.exe >nul 2>&1
timeout /t 1 /nobreak >nul

echo [2/3] Abrindo interface Web no navegador...
start "" "http://127.0.0.1:8080"

echo [3/3] Iniciando servidor híbrido na porta 8080...
echo.

set GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM=1
set GGML_VK_ALLOW_SYSMEM_FALLBACK=1

"F:\tools\lc_vulkan_b9245\llama-server.exe" ^
  -m "F:\data\models\Qwen3.8-27B-UD-IQ3_XXS.gguf" ^
  -ngl 30 ^
  --host 127.0.0.1 ^
  --port 8080 ^
  --threads 8 ^
  --ctx-size 4096 ^
  --no-repack

echo.
echo Servidor encerrado.
pause
