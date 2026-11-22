@echo off
title GPT-OSS 20B Antidoom - Servidor Maxima Performance Repacked (Ariadne Apex)
color 0A
echo ======================================================================
echo    INICIANDO GPT-OSS 20B ANTIDOOM (ALTA PERFORMANCE REPACKED AVX2)
echo ======================================================================
echo.
echo [1/3] Limpando instancias antigas do llama-server...
taskkill /F /IM llama-server.exe >nul 2>&1
ping 127.0.0.1 -n 2 >nul
echo       Memoria liberada com sucesso.
echo.

set "BINARY=F:\tools\lc\bin\llama-server.exe"
set "MODEL=D:\AetherMind_Models\gpt-oss-20b-antidoom.i1-IQ4_XS.gguf"
set "PORT=8083"

echo [2/3] Carregando GPT-OSS 20B Antidoom (12.1 GB)...
echo       Motor:   %BINARY%
echo       Modelo:  %MODEL%
echo       Porta:   %PORT%
echo.
echo [3/3] Parametros de Aceleracao Campeoes (Auditados pelo Omega):
echo       * Repacking AVX2:   Ativo (--repack) -> Alinhamento 256-bit SIMD na RAM
echo       * Afinidade Fisica: 10 Nucleos Haswell dedicados (-C 0x15555)
echo       * Flash Attention:  Ativo na CPU Haswell AVX2 (-fa on)
echo       * Thread Polling:   100 (Zero latencia de wake-up de thread)
echo       * Prioridade NT:    High Priority (--prio 2)
echo       * Parser Seguro:    --skip-chat-parsing (Zero erros 500 em tags CoT)
echo       * Compressao KV:    ctk/ctv q4_0 + Cache-Reuse 256
echo       * Micro-Batching:   -b 512 -ub 64 (Alinhamento L2 Cache)
echo       * Samplers:         Min-P 0.05, DynaTemp 0.4, DRY 0.8
echo.
echo Nota: O primeiro carregamento faz o repacking dos tensores na RAM (~5 min).
echo       Depois de carregado, o servidor opera em velocidade maxima contínua!
echo ======================================================================
echo.

"%BINARY%" --model "%MODEL%" --host 127.0.0.1 --port %PORT% --ctx-size 2048 -np 1 --alias gpt-oss-20b --repack --threads 10 -C 0x15555 --poll 100 --prio 2 -fa on --cache-reuse 256 -ctk q4_0 -ctv q4_0 -b 512 -ub 64 --skip-chat-parsing --min-p 0.05 --dynatemp-range 0.4 --dry-multiplier 0.8

pause
