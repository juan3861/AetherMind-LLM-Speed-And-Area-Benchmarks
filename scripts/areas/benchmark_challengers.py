"""
Benchmark Forense dos 3 Novos Modelos Desafiantes:
1. MiniCPM5-2B-Q4_K_M.gguf
2. granite-4.2-3b-Q4_K_M.gguf
3. qwen2.5-coder-1.5b-instruct-q4_k_m.gguf

Executado via llama-bench (b10749) no Xeon E5-2697 v3 (14 threads Haswell AVX2).
Gera relatorio em JSON e Markdown.
"""
import json
import os
import subprocess
import time

LLAMA_BENCH = r"F:\tools\lc_b10749\llama-bench.exe"
MODELS_DIR = r"F:\data\models"

CHALLENGERS = [
    "MiniCPM5-2B-Q4_K_M.gguf",
    "granite-4.2-3b-Q4_K_M.gguf",
    "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
]

results = []

print("=" * 70)
print(" BENCHMARK FORENSE DE DESAFIANTES — XEON E5-2697 v3 (14 THREADS)")
print("=" * 70)

for model_name in CHALLENGERS:
    model_path = os.path.join(MODELS_DIR, model_name)
    if not os.path.exists(model_path):
        print(f"[ERRO] Modelo {model_name} nao encontrado no disco!")
        continue

    print(f"\n>>> Testando: {model_name}...")
    cmd = [
        LLAMA_BENCH,
        "-m", model_path,
        "-p", "64",
        "-n", "32",
        "-t", "14",
        "-r", "2",
        "-o", "json"
    ]

    try:
        t0 = time.time()
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        elapsed = time.time() - t0

        # Parse JSON output from llama-bench
        raw_stdout = p.stdout.strip()
        bench_data = None
        for line in raw_stdout.splitlines():
            line = line.strip()
            if line.startswith("[") or line.startswith("{"):
                try:
                    bench_data = json.loads(line)
                    break
                except json.JSONDecodeError:
                    pass

        # If llama-bench json output was a list
        pp_speed = 0.0
        tg_speed = 0.0

        if bench_data and isinstance(bench_data, list):
            for item in bench_data:
                test_type = item.get("test", "")
                t_per_s = item.get("avg_ts", item.get("t_s", 0.0))
                if "pp" in test_type:
                    pp_speed = t_per_s
                elif "tg" in test_type:
                    tg_speed = t_per_s
        else:
            # Fallback text parse
            for line in raw_stdout.splitlines():
                if "pp64" in line:
                    parts = [pt.strip() for pt in line.split("|") if pt.strip()]
                    if len(parts) >= 6:
                        try:
                            pp_speed = float(parts[-1].split("±")[0].strip())
                        except ValueError:
                            pass
                elif "tg32" in line:
                    parts = [pt.strip() for pt in line.split("|") if pt.strip()]
                    if len(parts) >= 6:
                        try:
                            tg_speed = float(parts[-1].split("±")[0].strip())
                        except ValueError:
                            pass

        file_size_gb = os.path.getsize(model_path) / (1024**3)
        verdict = "APROVADO (>= 7.0 tok/s)" if tg_speed >= 7.0 else "REPROVADO (< 7.0 tok/s)"

        print(f"  [RESULTADO] Prompt: {pp_speed:.2f} tok/s | Geracao: {tg_speed:.2f} tok/s | Veredito: {verdict}")

        results.append({
            "model": model_name,
            "size_gb": round(file_size_gb, 2),
            "prompt_tok_s": pp_speed,
            "generation_tok_s": tg_speed,
            "verdict": verdict,
            "approved": tg_speed >= 7.0,
            "raw_output": raw_stdout
        })
    except Exception as e:
        print(f"  [FALHA] Erro ao executar benchmark: {e}")

out_path = r"F:\rotor-llm\BENCHMARK_CHALLENGERS_RESULTS.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\n" + "=" * 70)
print(f" Relatorio gravado em: {out_path}")
print("=" * 70)
