import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any

import psutil

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
from scripts.affinity_tools import get_dynamic_affinity_mask

LLAMA_SERVER = r"F:\tools\lc_b10749\llama-server.exe"
MODEL_PATH = r"F:\data\models\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"
OUTPUT_JSON = r"F:\rotor-llm\MTP_CONTEXT_CURVE_BENCHMARK.json"
SERVER_PORT = 8089

# Safety Thresholds: MoE peak observed RSS is 18.2 GB
MIN_AVAILABLE_RAM_BEFORE_LOAD_GB = 19.5
MIN_RUNTIME_HEADROOM_GB = 2.0

def kill_existing_servers():
    for p in psutil.process_iter(['name']):
        if p.info['name'] and 'llama-server' in p.info['name'].lower():
            try:
                p.kill()
            except Exception:
                pass
    time.sleep(1)

def wait_for_server(timeout=240):
    url = f"http://127.0.0.1:{SERVER_PORT}/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(1.5)
    return False

def query_completion(prompt, n_predict=128, temperature=0.0):
    url = f"http://127.0.0.1:{SERVER_PORT}/completion"
    payload = json.dumps({
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": temperature,
        "stream": False
    }).encode('utf-8')

    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    start = time.time()
    with urllib.request.urlopen(req, timeout=360) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    wall_time = time.time() - start
    return data, wall_time

def tokenize_count(text):
    try:
        url = f"http://127.0.0.1:{SERVER_PORT}/tokenize"
        payload = json.dumps({"content": text}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return len(json.loads(resp.read().decode('utf-8'))['tokens'])
    except Exception:
        return len(text.split()) * 4 // 3

def generate_context_prompt(target_tokens=1800):
    base = (
        "Em arquitetura de sistemas operacionais e hardware, a gerencia de memoria virtual "
        "depende de paginacao sob demanda. "
        "A TLB armazena mapeamentos recentes de enderecos virtuais para fisicos, "
        "acelerando o ciclo de busca de instrucoes. "
        "Quando ocorre um TLB miss, a tabela de paginas precisa ser percorrida pela MMU "
        "na memoria principal. "
    )
    # Each base unit is roughly 55 tokens
    reps = max(1, target_tokens // 55)
    prompt = base * reps + "\nAnalise comparativamente o trade-off entre latencia de busca e overhead de traducao."
    return prompt

def run_context_curve():
    print("=================================================================")
    print("   SPEED RESEARCH — MTP CONTEXT CURVE & REAL ACCEPTANCE RATE     ")
    print("=================================================================")

    mem = psutil.virtual_memory()
    avail_gb = mem.available / (1024**3)
    print(f"RAM Atual do Sistema: {mem.total/(1024**3):.2f} GB | Livre: {avail_gb:.2f} GB")

    if avail_gb < MIN_AVAILABLE_RAM_BEFORE_LOAD_GB:
        print(
            f"ABORTANDO: RAM disponível ({avail_gb:.2f} GB) < "
            f"Mínimo requerido ({MIN_AVAILABLE_RAM_BEFORE_LOAD_GB} GB)."
        )
        return None

    aff = get_dynamic_affinity_mask(num_physical_cores=12, exclude_os_cores=2)
    print(f"Afinidade Dinâmica: 12 Cores Físicos {aff['selected_logical_ids']} | Máscara: {aff['mask_hex']}")

    contexts: list[dict[str, Any]] = [
        {
            "name": "ctx_short",
            "target_tokens": 150,
            "prompt": "Explique de forma concisa o Teorema de Fermat e sua demonstracao por Andrew Wiles.",
        },
        {"name": "ctx_2k",    "target_tokens": 1800, "prompt": generate_context_prompt(1800)},
        {"name": "ctx_5k",    "target_tokens": 4500, "prompt": generate_context_prompt(4500)}
    ]

    mtp_configs: list[dict[str, Any]] = [
        {"name": "MTP_OFF", "spec_type": "none", "draft_n": 0},
        {"name": "MTP_1",   "spec_type": "draft-mtp", "draft_n": 1},
        {"name": "MTP_2",   "spec_type": "draft-mtp", "draft_n": 2},
        {"name": "MTP_3",   "spec_type": "draft-mtp", "draft_n": 3}
    ]

    results: dict[str, Any] = {
        "hardware": "Xeon E5-2697 v3 (14C/28T)",
        "affinity_mask": aff['mask_hex'],
        "threads": 12,
        "priority": "BelowNormal",
        "kv_cache": "q8_0 (configuração de teste; impacto de qualidade a ser avaliado)",
        "model": "Qwen3.6-35B-A3B-UD-Q4_K_M.gguf",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "blocks": []
    }

    for idx, cfg in enumerate(mtp_configs, 1):
        print("\n=================================================================")
        print(f"[{idx}/4] Carregando Servidor: {cfg['name']} (Draft N = {cfg['draft_n']})")
        print("=================================================================")
        kill_existing_servers()

        server_cmd = [
            LLAMA_SERVER,
            "-m", MODEL_PATH,
            "--host", "127.0.0.1",
            "--port", str(SERVER_PORT),
            "--threads", "12",
            "-C", aff["mask_hex"],
            "--ctx-size", "8192",
            "--prio", "-1",
            "-np", "1",
            "--no-repack",
            "-ctk", "q8_0",
            "-ctv", "q8_0"
        ]

        if cfg["draft_n"] > 0:
            server_cmd.extend(["--spec-type", cfg["spec_type"], "--spec-draft-n-max", str(cfg["draft_n"])])
        else:
            server_cmd.extend(["--spec-type", "none"])

        t0 = time.time()
        proc = subprocess.Popen(server_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            psutil.Process(proc.pid).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        except Exception:
            pass

        if not wait_for_server(timeout=240):
            print(f"ERRO: Servidor {cfg['name']} não subiu a tempo.")
            kill_existing_servers()
            continue

        load_time = time.time() - t0
        print(f"Servidor pronto na RAM em {load_time:.2f}s! Executando warm-up...")
        query_completion("Warm-up call", n_predict=16)

        block_data: dict[str, Any] = {
            "config": cfg["name"],
            "draft_n": cfg["draft_n"],
            "load_time_s": round(load_time, 2),
            "contexts": []
        }

        for ctx in contexts:
            print(f"\n--- Testando Contexto Real: {ctx['name']} (~{ctx['target_tokens']} tokens) ---")

            # Check runtime headroom before test
            sys_avail = psutil.virtual_memory().available / (1024**3)
            if sys_avail < MIN_RUNTIME_HEADROOM_GB:
                print(
                    f"[SAFETY GUARD]: RAM disponível ({sys_avail:.2f} GB) < "
                    f"Headroom ({MIN_RUNTIME_HEADROOM_GB} GB). "
                    "Pulando contexto para evitar swap."
                )
                continue

            reps: list[dict[str, Any]] = []
            for r in range(2):
                swap_before = psutil.swap_memory().used

                data, wall = query_completion(ctx["prompt"], n_predict=128)
                timings = data.get("timings", {})

                gen_tps = timings.get("predicted_per_second", 0.0)
                prompt_tps = timings.get("prompt_per_second", 0.0)
                prompt_tokens = timings.get("prompt_n", 0)
                gen_tokens = timings.get("predicted_n", 0)

                draft_n = timings.get("draft_n", 0)
                draft_acc = timings.get("draft_n_accepted", 0)
                acc_pct = (draft_acc / draft_n * 100.0) if draft_n > 0 else 0.0

                p_mem = psutil.Process(proc.pid).memory_info().rss / (1024**3)
                sys_avail = psutil.virtual_memory().available / (1024**3)
                swap_delta = (psutil.swap_memory().used - swap_before) / (1024**2) # in MB

                rep_stat = {
                    "rep": r + 1,
                    "prompt_tokens": prompt_tokens,
                    "generated_tokens": gen_tokens,
                    "generation_tok_s": round(gen_tps, 2),
                    "prompt_tok_s": round(prompt_tps, 2),
                    "wall_time_s": round(wall, 2),
                    "draft_generated": draft_n,
                    "draft_accepted": draft_acc,
                    "acceptance_pct": round(acc_pct, 1),
                    "server_rss_gb": round(p_mem, 2),
                    "available_ram_gb": round(sys_avail, 2),
                    "pagefile_delta_mb": round(swap_delta, 1)
                }
                reps.append(rep_stat)
                print(f"  Rep {r+1} (prompt {prompt_tokens}t -> gen {gen_tokens}t): "
                      f"Ger: {gen_tps:.2f} t/s | Drafts: {draft_acc}/{draft_n} ({acc_pct:.1f}%) | "
                      f"Prompt: {prompt_tps:.2f} t/s | Wall: {wall:.2f}s | RAM RSS: {p_mem:.2f} GB")

            avg_gen = round(sum(x["generation_tok_s"] for x in reps) / len(reps), 2)
            avg_acc = round(sum(x["acceptance_pct"] for x in reps) / len(reps), 2)
            avg_prompt = round(sum(x["prompt_tok_s"] for x in reps) / len(reps), 2)

            ctx_summary = {
                "context_name": ctx["name"],
                "target_prompt_tokens": ctx["target_tokens"],
                "avg_generation_tok_s": avg_gen,
                "avg_prompt_tok_s": avg_prompt,
                "avg_acceptance_pct": avg_acc,
                "repetitions": reps
            }
            block_data["contexts"].append(ctx_summary)

        results["blocks"].append(block_data)
        print(f"\nEncerrando servidor {cfg['name']} de forma graciosa...")
        kill_existing_servers()
        time.sleep(2)

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCESSO COMPLETO] Benchmark gravado em: {OUTPUT_JSON}")
    return results

if __name__ == '__main__':
    run_context_curve()
