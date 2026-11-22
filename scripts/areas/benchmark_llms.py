"""ROTOR LLM - Benchmark de Latencia e Tempo de Resposta por LLM."""
from __future__ import annotations

import json
import time

import httpx

ROUTER = "http://127.0.0.1:3700"
HEADERS = {
    "Authorization": "Bearer sk-rotor-local",
    "Content-Type": "application/json",
    "anthropic-version": "2023-06-01",
}

MODELS_TO_BENCHMARK = [
    {"label": "Ox Alpha (Flagship)", "model": "ox-alpha", "anthropic_alias": "claude-3-7-sonnet-20250219"},
    {"label": "Qwen 3.8 Max (Alibaba)", "model": "qwen3.8-max", "anthropic_alias": "qwen3.8-max"},
    {"label": "Qwen 3.7 Plus (Fast)", "model": "qwen3.7-plus", "anthropic_alias": "qwen3.7-plus"},
    {"label": "DeepSeek V4 (Proxy/Auto)", "model": "deepseek-v4-pro", "anthropic_alias": "deepseek-v4-pro"},
    {"label": "ChatGPT 5.6 (Stealth/Auto)", "model": "gpt-5.6", "anthropic_alias": "gpt-5.6"},
]

BASH_TOOL = {
    "name": "Bash",
    "description": "Execute a shell command",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"]
    }
}


def bench_model(info: dict) -> dict:
    label = info["label"]
    model_alias = info["anthropic_alias"]
    print(f"\n[BENCHMARK] Testando {label} (model: {model_alias})...", flush=True)

    result = {
        "label": label,
        "model": model_alias,
        "status": "FAIL",
        "ttft_ms": 0,
        "total_ms": 0,
        "tool_latency_ms": 0,
        "chars_generated": 0,
        "error": None,
    }

    # 1. Teste de Streaming Texto Simples + TTFT
    payload_text = {
        "model": model_alias,
        "max_tokens": 128,
        "stream": True,
        "messages": [{"role": "user", "content": "Escreva uma frase curta explicando o que e um router de IA."}]
    }

    t0 = time.perf_counter()
    ttft = None
    accumulated_text = ""

    try:
        with httpx.Client(timeout=120) as client:
            with client.stream("POST", f"{ROUTER}/v1/messages", json=payload_text, headers=HEADERS) as resp:
                if resp.status_code != 200:
                    result["error"] = f"HTTP {resp.status_code}: {resp.read().decode('utf-8', errors='ignore')[:100]}"
                    print(f"  [FAIL] {result['error']}", flush=True)
                    return result

                for line in resp.iter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if ttft is None and "[DONE]" not in data_str:
                            try:
                                j = json.loads(data_str)
                                if j.get("type") == "content_block_delta":
                                    ttft = (time.perf_counter() - t0) * 1000
                            except Exception:
                                pass
                        try:
                            j = json.loads(data_str)
                            if j.get("type") == "content_block_delta":
                                accumulated_text += j.get("delta", {}).get("text", "")
                        except Exception:
                            pass

        t_end = time.perf_counter()
        total_time_ms = (t_end - t0) * 1000
        result["ttft_ms"] = int(ttft) if ttft else int(total_time_ms)
        result["total_ms"] = int(total_time_ms)
        result["chars_generated"] = len(accumulated_text)
        result["status"] = "OK"
        print(
            f"  [OK] Streaming: TTFT={result['ttft_ms']}ms | "
            f"Total={result['total_ms']}ms | Caracteres={result['chars_generated']}",
            flush=True,
        )

    except Exception as e:
        result["error"] = str(e)[:100]
        print(f"  [FAIL] Erro no streaming: {result['error']}", flush=True)
        return result

    # 2. Teste de Tool Calling (Bash)
    payload_tool = {
        "model": model_alias,
        "max_tokens": 256,
        "stream": True,
        "tools": [BASH_TOOL],
        "messages": [{"role": "user", "content": "Use a ferramenta Bash para executar: echo BENCH_OK"}]
    }

    t_tool_0 = time.perf_counter()
    try:
        with httpx.Client(timeout=120) as client:
            with client.stream("POST", f"{ROUTER}/v1/messages", json=payload_tool, headers=HEADERS) as resp:
                if resp.status_code == 200:
                    for _ in resp.iter_lines():
                        pass
                    result["tool_latency_ms"] = int((time.perf_counter() - t_tool_0) * 1000)
                    print(f"  [OK] Tool Calling (Bash): Latencia={result['tool_latency_ms']}ms", flush=True)
                else:
                    result["tool_latency_ms"] = -1
    except Exception:
        result["tool_latency_ms"] = -1

    return result


def main():
    print("=" * 75, flush=True)
    print("  ROTOR LLM - RELATORIO DE BENCHMARK & TEMPO DE RESPOSTA (CLAUDE CODE)", flush=True)
    print("=" * 75, flush=True)

    results = []
    for info in MODELS_TO_BENCHMARK:
        res = bench_model(info)
        results.append(res)
        time.sleep(1)

    print("\n" + "=" * 75, flush=True)
    print("  TABELA CONSOLIDADA DE PERFORMANCE:", flush=True)
    print("=" * 75, flush=True)
    print(
        f"{'Modelo / Provedor':<26} | {'Status':<6} | {'TTFT':<10} | {'Total':<10} | {'Tool Call':<10} | {'Info'}",
        flush=True,
    )
    print("-" * 75, flush=True)

    for r in results:
        status = r["status"]
        ttft = f"{r['ttft_ms']} ms" if status == "OK" else "-"
        total = f"{r['total_ms']} ms" if status == "OK" else "-"
        tool = f"{r['tool_latency_ms']} ms" if r['tool_latency_ms'] > 0 else "-"
        extra = f"{r['chars_generated']} chars" if status == "OK" else f"Falha: {r['error']}"
        print(f"{r['label']:<26} | {status:<6} | {ttft:<10} | {total:<10} | {tool:<10} | {extra}", flush=True)

    print("=" * 75, flush=True)


if __name__ == "__main__":
    main()
