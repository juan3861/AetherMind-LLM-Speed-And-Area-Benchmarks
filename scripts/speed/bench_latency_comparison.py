import json
import os
import subprocess
import time

# Lista comparativa: (Modelo, Caminho, Categoria/Confronto)
models_to_test = [
    # Confronto 1: Heretic 9B Q8_0 (candidato deleção) vs Heretic 9B IQ4 (fica)
    ("Heretic-9B-Q8_0 (CANDIDATO DELECAO)", r"F:\data\models\Qwen3.8-9B-Distill-Heretic-Uncensored-Q8_0.gguf", "9B"),
    ("Heretic-9B-IQ4_XS (FICARIA)", r"F:\data\models\Qwen3.8-9B-Heretic-IQ4_XS.gguf", "9B"),
    
    # Confronto 2: Granite 3.1 2B (candidato deleção) vs Granite 4.2 3B vs MiniCPM5 2B (ficam)
    ("Granite-3.1-2B (CANDIDATO DELECAO)", r"F:\data\models\granite-3.1-2b-instruct-Q4_K_M.gguf", "2B-3B"),
    ("Granite-4.2-3B (FICARIA)", r"F:\data\models\granite-4.2-3b-Q4_K_M.gguf", "2B-3B"),
    ("MiniCPM5-2B (FICARIA)", r"F:\data\models\MiniCPM5-2B-Q4_K_M.gguf", "2B-3B"),
    
    # Confronto 3: ai9stars 3B (candidato deleção) vs Ministral 3B (fica)
    ("ai9stars-3B (CANDIDATO DELECAO)", r"F:\data\models\ai9stars_G9v3-3B-Q4_K_M.gguf", "3B"),
    ("Ministral-3-3B (FICARIA)", r"F:\data\models\Ministral-3-3B-Reasoning-2512.Q4_K_M.gguf", "3B"),
    
    # Confronto 4: Qwen3.5 4B (candidato deleção) vs Qwen3 4B RLM vs Nemotron 4B (ficam)
    ("Qwen3.5-4B (CANDIDATO DELECAO)", r"F:\data\models\Qwen3.5-4B-Q4_K_M.gguf", "4B"),
    ("Qwen3-4B-RLM (FICARIA)", r"F:\data\models\Qwen3-4B-Instruct-2507-RLM-SFT-v3-per-root-turn--.Q4_K_M.gguf", "4B"),
    ("Nemotron-4B (FICARIA)", r"F:\data\models\NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf", "4B"),
    
    # Confronto 5: Ring-mini 9B (candidato deleção) vs rlm-qwen3-8b (fica)
    ("Ring-mini-2.0-9B (CANDIDATO DELECAO)", r"F:\data\models\Ring-mini-2.0-Q4_K_M.gguf", "8B-9B"),
    ("rlm-qwen3-8B (FICARIA)", r"F:\data\models\rlm-qwen3-8b-v0.1-q4_k_m.gguf", "8B-9B"),
]

llama_bench = r"F:\tools\lc_b10749\llama-bench.exe"
benchmark_results = []

print("=== INICIANDO BENCHMARK RIGOROSO DE LATENCIA (PROMPT & GERACAO) ===")

for label, path, cat in models_to_test:
    if not os.path.exists(path):
        print(f"[PULADO] Arquivo nao encontrado: {path}")
        continue
    
    size_gb = round(os.path.getsize(path) / (1024**3), 2)
    print(f"\n--> Testando Latencia de: {label} ({size_gb} GB)...")
    
    cmd = [
        llama_bench,
        "-m", path,
        "-p", "128",       # Prompt de 128 tokens para medir TTFT (Time to First Token)
        "-n", "64",        # Gerar 64 tokens para medir taxa sustentada
        "-t", "14",        # 14 threads do Xeon E5
        "-r", "1",
        "-o", "json"
    ]
    
    start_t = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        dur = round(time.time() - start_t, 2)
        
        stdout = proc.stdout
        bench_data = None
        for line in stdout.splitlines():
            line_s = line.strip()
            if line_s.startswith("[") or line_s.startswith("{"):
                try:
                    bench_data = json.loads(line_s)
                    break
                except Exception:
                    pass
        if not bench_data:
            start_idx = stdout.find("[")
            end_idx = stdout.rfind("]")
            if start_idx != -1 and end_idx != -1:
                try:
                    bench_data = json.loads(stdout[start_idx:end_idx+1])
                except Exception:
                    pass
        
        pp_ts = 0.0
        tg_ts = 0.0
        ttft_ms = 0.0
        
        if bench_data and isinstance(bench_data, list):
            for entry in bench_data:
                test_name = entry.get("test", "")
                avg_ts = entry.get("avg_ts", 0)
                avg_ns = entry.get("avg_ns", 0)
                if "pp128" in test_name:
                    pp_ts = round(avg_ts, 2)
                    # TTFT para prompt de 128 tokens em ms:
                    ttft_ms = round(avg_ns / 1_000_000, 1)
                elif "tg64" in test_name:
                    tg_ts = round(avg_ts, 2)
        
        res = {
            "label": label,
            "category": cat,
            "size_gb": size_gb,
            "ttft_ms_prompt128": ttft_ms,
            "prompt_speed_tok_s": pp_ts,
            "gen_speed_tok_s": tg_ts,
            "total_benchmark_time_s": dur,
            "status": "OK" if tg_ts > 0 else "PARSE_FAIL"
        }
        benchmark_results.append(res)
        print(f"    RESULTADO: TTFT={ttft_ms}ms ({pp_ts} tok/s prompt) | Geracao={tg_ts} tok/s | Tempo Total={dur}s")
    except Exception as e:
        print(f"    FALHA em {label}: {e}")
        benchmark_results.append({
            "label": label,
            "category": cat,
            "size_gb": size_gb,
            "error": str(e),
            "status": "ERROR"
        })

out_json = r"F:\rotor-llm\COMPARATIVO_LATENCIA_DELECAO_VS_RETENCAO.json"
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(benchmark_results, f, indent=2, ensure_ascii=False)

print("\n=== TODOS OS TESTES COMPARATIVOS DE LATENCIA CONCLUIDOS! ===")
print("Relatorio gerado em:", out_json)
