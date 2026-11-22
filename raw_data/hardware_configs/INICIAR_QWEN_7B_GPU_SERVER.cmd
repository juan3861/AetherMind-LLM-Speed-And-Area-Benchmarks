@echo off
chcp 65001 >nul
title [AetherMind] Qwen 2.5 7B GPU - Servidor Web e API
color 0A

echo ======================================================================
echo    AETHERMIND - QWEN 2.5 7B GPU SERVER (AMD RX 580 - VULKAN)
echo    VELOCIDADE: ~29 TOKENS/SEGUNDO NA API / WEB INTERFACE
echo ======================================================================
echo Modelo: F:\data\models\Qwen2.5-7B-Instruct-Q4_K_M.gguf
echo Servidor: http://127.0.0.1:8080
echo API OpenAI: http://127.0.0.1:8080/v1
echo ======================================================================
echo.

echo [1/3] Encerrando instancias anteriores do llama-server...
taskkill /F /IM llama-server.exe >nul 2>&1
timeout /t 1 /nobreak >nul

echo [2/3] Programando abertura do navegador apos o carregamento...
start /b cmd /c "timeout /t 8 /nobreak >nul && start http://127.0.0.1:8080"

echo [3/3] Iniciando servidor llama-server na porta 8080...
echo.

set GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM=1
set GGML_VK_ALLOW_SYSMEM_FALLBACK=1

"F:\tools\lc_vulkan_b9245\llama-server.exe" ^
  -m "F:\data\models\Qwen2.5-7B-Instruct-Q4_K_M.gguf" ^
  -ngl 24 ^
  --host 127.0.0.1 ^
  --port 8080 ^
  --threads 8 ^
  --ctx-size 2048 ^
  -np 1 ^
  --no-repack

echo.
echo Servidor encerrado.
pause
