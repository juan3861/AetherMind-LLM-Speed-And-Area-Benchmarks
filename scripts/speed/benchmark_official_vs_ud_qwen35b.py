"""Head-to-Head Benchmark: Official ggml-org Qwen 35B vs UD Qwen 35B (Baseline & MTP).

Measures:
1. Qwen3.6-35B-A3B-Q4_K_M.gguf (Official) - Baseline
2. Qwen3.6-35B-A3B-Q4_K_M.gguf (Official) - With MTP Head
3. Qwen3.6-35B-A3B-UD-Q4_K_M.gguf (UD) - Baseline
4. Qwen3.6-35B-A3B-UD-Q4_K_M.gguf (UD) - With MTP Head
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

LLAMA_SERVER = r"F:\tools\lc_b10749\llama-server.exe"
MTP_HEAD = r"F:\data\models\mtp-Q4_K_M.gguf"
PORT = 11488
BASE_URL = f"http://127.0.0.1:{PORT}"
PROMPT = "Explain the difference between a process and a thread in operating systems in 2 concise bullet points."

CONFIGS = [
    {
        "id": "official_baseline",
        "name": "Qwen3.6-35B Official (Baseline)",
        "model": r"F:\data\models\Qwen3.6-35B-A3B-Q4_K_M.gguf",
        "extra_args": []
    },
    {
        "id": "official_mtp",
        "name": "Qwen3.6-35B Official (+ MTP Head)",
        "model": r"F:\data\models\Qwen3.6-35B-A3B-Q4_K_M.gguf",
        "extra_args": ["-md", MTP_HEAD, "--spec-type", "draft-mtp", "--spec-draft-n-max", "2"]
    },
    {
        "id": "ud_baseline",
        "name": "Qwen3.6-35B UD (Baseline)",
        "model": r"F:\data\models\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf",
        "extra_args": []
    },
    {
        "id": "ud_mtp",
        "name": "Qwen3.6-35B UD (+ MTP Head)",
        "model": r"F:\data\models\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf",
        "extra_args": ["-md", MTP_HEAD, "--spec-type", "draft-mtp", "--spec-draft-n-max", "2"]
    }
]

def wait_ready(timeout_s=120):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{BASE_URL}/health")
            with urllib.request.urlopen(req, timeout=2) as r:
                if r.status in (200, 204):
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False

def get_rss(pid):
    if pid and psutil:
        try:
            return psutil.Process(pid).memory_info().rss / (1024 * 1024)
        except Exception:
            pass
    return None

def run_bench(cfg):
    cid = cfg["id"]
    name = cfg["name"]
    model = cfg["model"]
    extra = cfg["extra_args"]

    print("\n" + "=" * 75)
    print(f" [RUNNING] {name}")
    print(f" Model: {model}")
    print(f" Extra: {extra}")
    print("=" * 75)

    if not os.path.exists(model):
        print(f" [WAIT/SKIP] Model not yet ready on disk: {model}")
        return {"id": cid, "name": name, "status": "FILE_NOT_READY"}

    log_path = Path(f"F:/rotor-llm/scratch/bench_{cid}.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        LLAMA_SERVER,
        "-m", model,
        "--host", "127.0.0.1",
        "--port", str(PORT),
        "--threads", "10",
        "--ctx-size", "2048",
        "-np", "1",
        "--prio", "-1",
        "--no-repack"
    ] + extra

    t0 = time.perf_counter()
    with open(log_path, "w", encoding="utf-8", errors="replace") as f:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=f)

    pid = proc.pid
    ready = wait_ready(120)
    if not ready:
        print("  -> Startup timeout.")
        proc.kill()
        return {"id": cid, "name": name, "status": "STARTUP_TIMEOUT"}

    load_time = time.perf_counter() - t0
    rss = get_rss(pid)
    print(f"  -> Ready in {load_time:.1f}s | RAM: {rss:.1f} MB. Inferring...")

    payload = {
        "model": "qwen35b",
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 48,
        "temperature": 0.0,
        "seed": 42
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    t_req = time.perf_counter()
    data = {}
    err = None
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        err = str(e)
    t_tot = (time.perf_counter() - t_req) * 1000.0
    peak_rss = get_rss(pid) or rss

    proc.terminate()
    try:
        proc.wait(timeout=8)
    except Exception:
        proc.kill()

    if err:
        print(f"  -> Error: {err}")
        return {"id": cid, "name": name, "status": "ERROR", "error": err}

    timings = data.get("timings", {})
    prompt_ms = timings.get("prompt_ms", 0)
    pred_s = timings.get("predicted_per_second", 0)
    
    result = {
        "id": cid,
        "name": name,
        "status": "SUCCESS",
        "load_time_s": round(load_time, 2),
        "ttft_ms": round(prompt_ms, 1),
        "gen_tok_s": round(pred_s, 2),
        "total_ms": round(t_tot, 1),
        "ram_peak_mb": round(peak_rss, 1) if peak_rss else None
    }
    print(f"  -> [SUCCESS] Gen: {pred_s:.2f} tok/s | TTFT: {prompt_ms:.0f} ms | RAM: {peak_rss:.0f} MB")
    return result

def main():
    print("=" * 80)
    print(" [HEAD-TO-HEAD BENCHMARK] Qwen 35B Official vs UD (Intel Xeon E5-2697 v3)")
    print("=" * 80)
    results = [run_bench(c) for c in CONFIGS]
    out_file = Path("F:/rotor-llm/BENCHMARK_OFFICIAL_VS_UD_RESULTS.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {out_file}")

if __name__ == "__main__":
    main()
