import re
import subprocess
import time

import psutil

LLAMA_CLI = r"F:\tools\lc_b10749\llama-cli.exe"
MODEL_PATH = r"F:\data\models\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"

# Core 0 reserved for OS (Logical 0 and 1 untouched)
# Cores 1 to 13 active (12 physical cores: 0x5555554)
AFFINITY_12_PHYS = "0x5555554"
AFFINITY_14_PHYS = "0x5555555"

def ensure_safe_system():
    # 1. Kill any stray llama processes
    for p in psutil.process_iter(['name']):
        if p.info['name'] and p.info['name'].lower().startswith('llama'):
            try:
                p.kill()
            except Exception:
                pass
    time.sleep(1)

    # 2. Check RAM
    mem = psutil.virtual_memory()
    avail_gb = mem.available / (1024**3)
    if avail_gb < 20.0:
        raise RuntimeError(
            f"RAM insuficiente para rodar o modelo 35B com segurança! "
            f"Disponível: {avail_gb:.1f} GB (Mínimo: 20 GB)."
        )
    print(f"[SAFETY GUARD] RAM Disponível: {avail_gb:.1f} GB. Sistema seguro para carregar modelo 21 GB.")

def run_single_benchmark(mtp_n=2, threads=12, use_affinity=True, n_gen=48, ctx=2048):
    ensure_safe_system()

    prompt = "Escreva uma funcao em Python para calcular os primeiros 10 numeros primos e explique brevemente a logica."

    cmd = [
        LLAMA_CLI,
        "-m", MODEL_PATH,
        "-p", prompt,
        "-n", str(n_gen),
        "-c", str(ctx),
        "-t", str(threads),
        "-st",
        "--prio", "-1",
        "--temp", "0.0",
        "--no-warmup"
    ]

    if mtp_n > 0:
        cmd.extend(["--spec-type", "draft-mtp", "--spec-draft-n-max", str(mtp_n)])
    else:
        cmd.extend(["--spec-type", "none"])

    mask = AFFINITY_12_PHYS if threads <= 12 else AFFINITY_14_PHYS
    if use_affinity:
        cmd.extend(["-C", mask])

    print("\n=======================================================")
    affinity = f"ON ({mask})" if use_affinity else "OFF"
    print(f"Executando Teste: MTP={mtp_n} | Threads={threads} | Affinity={affinity}")
    print("=======================================================")

    start_time = time.time()
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace'
    )

    # Lower python priority as well
    try:
        psutil.Process(proc.pid).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    except Exception:
        pass

    stdout, stderr = proc.communicate(timeout=180)
    elapsed = time.time() - start_time

    # Parse llama_perf stats from stderr
    eval_ts = None
    prompt_ts = None
    acceptance_rate = None
    draft_stats = None

    for line in stderr.splitlines():
        # llama_perf_context_print: eval time = 4321.12 ms / 48 runs
        # (11.11 ms per token, 90.00 tokens per second)
        if "eval time =" in line:
            m = re.search(r'([0-9.]+)\s+tokens per second', line)
            if m:
                eval_ts = float(m.group(1))
        if "prompt eval time =" in line:
            m = re.search(r'([0-9.]+)\s+tokens per second', line)
            if m:
                prompt_ts = float(m.group(1))
        # draft acceptance: draft = 48, accepted = 32 ( 66.67%)
        if "draft" in line.lower() and "accept" in line.lower():
            draft_stats = line.strip()
            m = re.search(r'([0-9.]+)%', line)
            if m:
                acceptance_rate = float(m.group(1))

    result = {
        "mtp_n": mtp_n,
        "threads": threads,
        "affinity": use_affinity,
        "generation_ts": eval_ts,
        "prompt_ts": prompt_ts,
        "draft_stats": draft_stats,
        "acceptance_rate": acceptance_rate,
        "total_wall_time_s": elapsed
    }

    print(f"--> Geração: {eval_ts} t/s | Prompt: {prompt_ts} t/s")
    if draft_stats:
        print(f"--> MTP Stats: {draft_stats}")
    print(f"--> Tempo Total: {elapsed:.2f}s")
    return result

if __name__ == '__main__':
    # Probe rápido com MTP=2 e 12 threads com afinidade
    res = run_single_benchmark(mtp_n=2, threads=12, use_affinity=True, n_gen=32)
    print("\nResultado do Probe Seguro:")
    print(res)
