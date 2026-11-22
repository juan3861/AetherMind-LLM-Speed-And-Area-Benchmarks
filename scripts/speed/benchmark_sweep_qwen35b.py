"""Scientific Empirical Sweep Matrix for Qwen 35B MoE.

Executes a controlled, non-freezing parameter sweep:
1. Thread count sweep: [6, 8, 10, 12, 14]
2. KV Cache quantization: [f16, q8_0]
3. Fixed seed, prompt, below_normal priority, clean process cleanup between runs.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

LLAMA_SERVER = r"F:\tools\lc_b10749\llama-server.exe"
MODEL_PATH = r"F:\data\models\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"
PORT = 11488
BENCHMARK_PROMPT = "Explain the difference between a process and a thread in operating systems in 3 bullet points."


@dataclass
class SweepRun:
    threads: int
    kv_type: str
    load_time_s: float
    prompt_tokens: int
    completion_tokens: int
    prompt_tok_s: float | None
    gen_tok_s: float | None
    ttft_ms: float | None
    total_ms: float
    ram_peak_mb: float | None
    success: bool
    error: str | None = None


def wait_for_ready(url: str, timeout_s: float = 90.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{url}/health", headers={"User-Agent": "Rotor-Sweep/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status in (200, 204):
                    return True
        except Exception:
            pass
        time.sleep(1.5)
    return False


def measure_rss(pid: int | None) -> float | None:
    if pid is None or psutil is None:
        return None
    try:
        p = psutil.Process(pid)
        return p.memory_info().rss / (1024 * 1024)
    except Exception:
        return None


def run_single_config(threads: int, kv_type: str = "f16") -> SweepRun:
    cmd = [
        LLAMA_SERVER,
        "-m", MODEL_PATH,
        "--host", "127.0.0.1",
        "--port", str(PORT),
        "--threads", str(threads),
        "--ctx-size", "2048",
        "-np", "1",
        "--prio", "-1",  # Below normal priority (prevents freezing)
        "--no-repack",
        "-ctk", kv_type,
        "-ctv", kv_type,
    ]

    print(f"\n[SWEEP] Starting Config: Threads={threads}, KV={kv_type}...")
    log_file = Path(f"F:/rotor-llm/scratch/sweep_{threads}_{kv_type}.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    t_start = time.perf_counter()
    with open(log_file, "w", encoding="utf-8", errors="replace") as err_out:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=err_out,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

    pid = proc.pid
    base_url = f"http://127.0.0.1:{PORT}"
    ready = wait_for_ready(base_url, timeout_s=90.0)

    if not ready:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        return SweepRun(
            threads=threads,
            kv_type=kv_type,
            load_time_s=time.perf_counter() - t_start,
            prompt_tokens=0,
            completion_tokens=0,
            prompt_tok_s=None,
            gen_tok_s=None,
            ttft_ms=None,
            total_ms=0.0,
            ram_peak_mb=None,
            success=False,
            error="Timeout waiting for server to be READY",
        )

    load_time = time.perf_counter() - t_start
    print(f"  -> READY in {load_time:.1f}s (PID={pid}). Sending inference request...")

    # Execute request
    payload = {
        "model": "qwen35b",
        "messages": [{"role": "user", "content": BENCHMARK_PROMPT}],
        "max_tokens": 64,
        "temperature": 0.0,
        "seed": 42,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "Rotor-Sweep/1.0"},
        method="POST",
    )

    t0 = time.perf_counter()
    run_err = None
    data = {}
    try:
        with urllib.request.urlopen(req, timeout=60.0) as resp:
            raw = resp.read()
            data = json.loads(raw.decode("utf-8"))
    except Exception as e:
        run_err = str(e)
    t_total = (time.perf_counter() - t0) * 1000.0

    ram_mb = measure_rss(pid)

    # Terminate process cleanly
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except Exception:
        proc.kill()

    if run_err:
        print(f"  -> [FAILED] Inference error: {run_err}")
        return SweepRun(
            threads=threads,
            kv_type=kv_type,
            load_time_s=load_time,
            prompt_tokens=0,
            completion_tokens=0,
            prompt_tok_s=None,
            gen_tok_s=None,
            ttft_ms=None,
            total_ms=t_total,
            ram_peak_mb=ram_mb,
            success=False,
            error=run_err,
        )

    usage = data.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)

    timings = data.get("timings", {})
    prompt_tok_s = None
    gen_tok_s = None
    ttft_ms = None

    if isinstance(timings, dict):
        prompt_ms = timings.get("prompt_ms")
        if prompt_ms:
            ttft_ms = float(prompt_ms)
            if prompt_tokens > 0 and prompt_ms > 0:
                prompt_tok_s = prompt_tokens / (prompt_ms / 1000.0)
        
        pred_tok_s = timings.get("predicted_per_second")
        if pred_tok_s is not None:
            gen_tok_s = float(pred_tok_s)
        elif completion_tokens > 0 and t_total > 0:
            gen_tok_s = completion_tokens / (t_total / 1000.0)

    print(f"  -> [RESULT] Threads={threads}, KV={kv_type} | Gen: {gen_tok_s:.2f} tok/s | Prompt: {prompt_tok_s:.1f} tok/s | TTFT: {ttft_ms:.0f}ms | RAM: {ram_mb:.0f}MB")

    return SweepRun(
        threads=threads,
        kv_type=kv_type,
        load_time_s=load_time,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        prompt_tok_s=prompt_tok_s,
        gen_tok_s=gen_tok_s,
        ttft_ms=ttft_ms,
        total_ms=t_total,
        ram_peak_mb=ram_mb,
        success=True,
    )


def main():
    print("=" * 80)
    print(" [SCIENTIFIC BENCHMARK SWEEP] Qwen 35B MoE Hardware Empirical Optimization")
    print(" Host: Intel Xeon E5-2697 v3 (14C/28T)")
    print(f" Model: {MODEL_PATH}")
    print("=" * 80)

    runs = []
    
    # 1. Thread sweep: [6, 8, 10, 12] with f16 KV
    thread_candidates = [6, 8, 10, 12]
    for th in thread_candidates:
        r = run_single_config(threads=th, kv_type="f16")
        runs.append(r)
        time.sleep(2)  # Cooldown between runs to settle RAM and CPU caches

    # Find best thread count
    successful_runs = [r for r in runs if r.success and r.gen_tok_s is not None]
    if successful_runs:
        best_thread_run = max(successful_runs, key=lambda x: x.gen_tok_s or 0)
        best_threads = best_thread_run.threads
        print(f"\n[INTERMEDIATE WINNER] Best CPU Thread Count: {best_threads} ({best_thread_run.gen_tok_s:.2f} tok/s)")

        # 2. KV Cache sweep: Test best_threads with q8_0 KV
        r_q8 = run_single_config(threads=best_threads, kv_type="q8_0")
        runs.append(r_q8)
    else:
        print("[WARNING] No runs completed successfully.")

    # Save complete forensic report
    report_file = Path("F:/rotor-llm/BENCHMARK_SWEEP_QWEN35B_RESULTS.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in runs], f, indent=2)
    print(f"\n[SAVED] All sweep results written to: {report_file}")


if __name__ == "__main__":
    main()
