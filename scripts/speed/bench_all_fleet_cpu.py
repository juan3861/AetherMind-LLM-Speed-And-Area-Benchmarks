import json
import os
import subprocess
import sys

models = [
    ("qwen2.5-coder-1.5b", r"F:\data\models\qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"),
    ("MiniCPM5-2B", r"F:\data\models\MiniCPM5-2B-Q4_K_M.gguf"),
    ("granite-4.2-3b", r"F:\data\models\granite-4.2-3b-Q4_K_M.gguf"),
    ("Ministral-3-3B", r"F:\data\models\Ministral-3-3B-Reasoning-2512.Q4_K_M.gguf"),
    ("Phi-4-mini-instruct", r"F:\data\models\Phi-4-mini-instruct.Q4_K_M.gguf"),
    ("Qwen3.6-35B-A3B-UD", r"F:\data\models\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"),
]

llama_bench = r"F:\tools\lc_b10749\llama-bench.exe"
results = []

for name, path in models:
    if not os.path.exists(path):
        print(f"PULANDO {name}: arquivo nao existe em {path}")
        continue
    
    file_size_gb = round(os.path.getsize(path) / (1024**3), 2)
    print(f"--> Testando {name} ({file_size_gb} GB)...")
    
    # Executa llama-bench com 14 threads no Xeon E5
    cmd = [
        llama_bench,
        "-m", path,
        "-p", "128",
        "-n", "64",
        "-t", "14",
        "-r", "1",
        "-o", "json"
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        stdout = proc.stdout
        # Procura o JSON na saída do llama-bench
        bench_data = None
        for line in stdout.splitlines():
            line_s = line.strip()
            if line_s.startswith("[") or line_s.startswith("{"):
                try:
                    bench_data = json.loads(line_s)
                    break
                except Exception:
                    pass
        
        # Se nao achou json direto em uma linha, tenta o stdout todo
        if not bench_data:
            try:
                # pode ter saida JSON multi-linha
                start = stdout.find("[")
                end = stdout.rfind("]")
                if start != -1 and end != -1:
                    bench_data = json.loads(stdout[start:end+1])
            except Exception:
                pass
        
        pp_ts = None
        tg_ts = None
        if bench_data and isinstance(bench_data, list):
            for entry in bench_data:
                test_name = entry.get("test", "")
                avg_ts = entry.get("avg_ts", 0)
                if "pp128" in test_name:
                    pp_ts = round(avg_ts, 2)
                elif "tg64" in test_name:
                    tg_ts = round(avg_ts, 2)
        
        results.append({
            "name": name,
            "path": path,
            "size_gb": file_size_gb,
            "pp128_tok_s": pp_ts,
            "tg64_tok_s": tg_ts,
            "raw_stdout": stdout[-300:] if not pp_ts else "OK"
        })
        print(f"    SUCESSO: pp128={pp_ts} tok/s | tg64={tg_ts} tok/s")
    except Exception as e:
        print(f"    ERRO em {name}: {e}")
        results.append({
            "name": name,
            "size_gb": file_size_gb,
            "error": str(e)
        })

output_file = r"F:\rotor-llm\BENCHMARK_FLEET_XEON_E5.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\nTodos os benchmarks concluidos. Salvo em:", output_file)
