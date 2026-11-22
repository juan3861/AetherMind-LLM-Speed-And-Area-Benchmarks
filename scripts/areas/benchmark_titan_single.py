# -*- coding: utf-8 -*-
r"""
AETHERMIND APOTHEOSIS — BENCHMARK E MIGRAÇÃO BARE-METAL TITAN 1
Modelo: gemma-4-26B-A4B-it-Claude-Opus-Distill.q4_k_m.gguf (15.64 GB)
Baterias: 13 Áreas Cognitivas + 10 Desafios Opus (com AST/pytest + Auto-Reparo)
Ao finalizar: Move para Google Drive gdrive_01:AetherMind_High_Titans para liberar disco F:
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROTOR_ROOT = Path(r"F:\rotor-llm")
if str(ROTOR_ROOT) not in sys.path:
    sys.path.insert(0, str(ROTOR_ROOT))

from router.formal_verifier import formal_verifier
from benchmark_13_areas_39_testes import BENCHMARK_SUITE
from duelo_nivel_opus_8b_vs_9b import OPUS_10_TESTS

SERVER_BIN = r"F:\tools\lc\bin\llama-server.exe"
PORT = 8089
BASE_URL = f"http://127.0.0.1:{PORT}"

MODEL_PATH = Path(r"F:\AetherMind_Contenders\gemma-4-26B-A4B-it-Claude-Opus-Distill.q4_k_m.gguf")
PROOF_FILE = Path(r"F:\data\proof_novos_titans_pendentes.json")
MASTER_MD = Path(r"F:\data\MASTER_LIVRO_SAGRADO_BENCHMARKS.md")
LOG_FILE = Path(r"F:\data\benchmark_titan_1.log")
RCLONE_BIN = r"C:\Users\juanp\.gemini\antigravity\scratch\aether_gdrive_turbo\bin\rclone.exe"
RCLONE_CONF = r"C:\Users\juanp\.gemini\antigravity\scratch\aether_gdrive_turbo\config\rclone.conf"

def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8", errors="replace") as f:
        f.write(line + "\n")

def stop_llama_server():
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-Process -Name llama-server, llama-cli -ErrorAction SilentlyContinue | Stop-Process -Force"],
                   capture_output=True)
    time.sleep(1.5)

def query_model(prompt: str, max_tokens: int = 1024, temperature: float = 0.0) -> Dict[str, Any]:
    url = f"{BASE_URL}/completion"
    payload = {
        "prompt": prompt,
        "n_predict": max_tokens,
        "temperature": temperature,
        "stop": ["<|im_end|>", "<|endoftext|>", "</s>", "```\n\n"]
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180.0) as resp:
            res = json.loads(resp.read().decode("utf-8", errors="replace"))
            lat_s = time.time() - t0
            content = res.get("content", "")
            timings = res.get("timings", {})
            pp_tok_s = timings.get("prompt_per_second", 0.0)
            tg_tok_s = timings.get("predicted_per_second", 0.0)
            return {
                "content": content,
                "latency_s": lat_s,
                "pp_tok_s": pp_tok_s,
                "tg_tok_s": tg_tok_s
            }
    except Exception as e:
        log(f"    [!] Erro query_model: {e}")
        return {"content": "", "latency_s": time.time() - t0, "pp_tok_s": 0.0, "tg_tok_s": 0.0}

def run_13_areas() -> Dict[str, Any]:
    log("  [*] Iniciando Bateria: 13 Áreas Cognitivas (39 Testes)...")
    results = {}
    passed_total = 0
    total_tests = 0
    pp_speeds = []
    tg_speeds = []

    for area in BENCHMARK_SUITE:
        area_id = area.get("area_id", str(len(results) + 1))
        area_name = area.get("area_name", f"Area_{area_id}")
        area_passed = 0
        tests_details = []
        for test in area["tests"]:
            total_tests += 1
            t_id = test.get("id", test.get("name", str(total_tests)))
            p_text = test["prompt"]
            validator = test.get("verify") or test.get("validator")
            n_predict = test.get("n_predict", 512)
            
            resp = query_model(p_text, max_tokens=n_predict)
            out_txt = resp["content"]
            if resp["pp_tok_s"] > 0: pp_speeds.append(resp["pp_tok_s"])
            if resp["tg_tok_s"] > 0: tg_speeds.append(resp["tg_tok_s"])

            try:
                ok = bool(validator(out_txt))
            except Exception:
                ok = False

            if ok:
                area_passed += 1
                passed_total += 1

            tests_details.append({
                "test_id": t_id,
                "passed": ok,
                "latency_s": round(resp["latency_s"], 2)
            })

        results[area_id] = {
            "name": area_name,
            "passed": area_passed,
            "total": len(area["tests"]),
            "tests": tests_details
        }
        log(f"    -> Área {area_id} ({area_name[:35]}...): {area_passed}/{len(area['tests'])}")

    avg_pp = sum(pp_speeds) / len(pp_speeds) if pp_speeds else 0.0
    avg_tg = sum(tg_speeds) / len(tg_speeds) if tg_speeds else 0.0

    return {
        "passed_total": passed_total,
        "total_tests": total_tests,
        "pass_rate_pct": round((passed_total / total_tests) * 100, 2) if total_tests else 0.0,
        "avg_pp_tok_s": round(avg_pp, 2),
        "avg_tg_tok_s": round(avg_tg, 2),
        "areas": results
    }

def clean_python_code(text: str) -> str:
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()
    pattern = r"```(?:python)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, cleaned, re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
    return cleaned

def run_10_opus() -> Dict[str, Any]:
    log("  [*] Iniciando Bateria: 10 Desafios de Código Nível Opus (com Formal Verifier)...")
    results = {}
    passed_total = 0
    zero_shot_passed = 0
    repaired_passed = 0

    for test in OPUS_10_TESTS:
        t_id = test["id"]
        t_name = test["name"]
        prompt = test["prompt"]
        assertions = test["assertions"]

        log(f"    -> Avaliando {t_id} ({t_name[:30]})...")
        resp = query_model(prompt, max_tokens=512)
        code1 = clean_python_code(resp["content"])

        passed = False
        was_repaired = False
        last_error = ""

        try:
            ver1 = formal_verifier.verify_python_code(code1, assertions, timeout_s=4.0)
            if ver1.passed:
                passed = True
            else:
                last_error = ver1.counterexample or "Assertion failed"
                repair_prompt = (
                    f"{prompt}\n\n"
                    f"Sua tentativa anterior falhou no verificador formal:\n{last_error}\n"
                    f"Corrija o algoritmo para passar em todos os casos de borda (sem comentarios, apenas o bloco python):"
                )
                r_resp = query_model(repair_prompt, max_tokens=512)
                code2 = clean_python_code(r_resp["content"])
                ver2 = formal_verifier.verify_python_code(code2, assertions, timeout_s=4.0)
                if ver2.passed:
                    passed = True
                    was_repaired = True
                else:
                    last_error = ver2.counterexample or "Assertion failed"
        except Exception as e:
            last_error = str(e)

        if passed:
            passed_total += 1
            if was_repaired:
                repaired_passed += 1
                status_str = "PASS (Auto-Reparo)"
            else:
                zero_shot_passed += 1
                status_str = "PASS (Zero-Shot)"
        else:
            status_str = f"FAIL ({last_error[:40]})"

        log(f"       Resultado: {status_str}")
        results[t_id] = {
            "name": t_name,
            "passed": passed,
            "zero_shot": (passed and not was_repaired),
            "repaired": was_repaired,
            "status": status_str
        }

    return {
        "passed_total": passed_total,
        "total_tests": len(OPUS_10_TESTS),
        "pass_rate_pct": round((passed_total / len(OPUS_10_TESTS)) * 100, 2),
        "zero_shot_passed": zero_shot_passed,
        "repaired_passed": repaired_passed,
        "challenges": results
    }

def main():
    log("================================================================================")
    log("AETHERMIND APOTHEOSIS — EXECUÇÃO DE BENCHMARK TITAN 1 (15.64 GB)")
    log(f"Arquivo: {MODEL_PATH}")
    log("================================================================================")

    if not MODEL_PATH.exists():
        log(f"[ERRO] Arquivo {MODEL_PATH} não encontrado!")
        sys.exit(1)

    stop_llama_server()

    cmd = [
        SERVER_BIN,
        "-m", str(MODEL_PATH),
        "-c", "3072",
        "-b", "256",
        "-ub", "64",
        "-t", "12",
        "-np", "1",
        "--no-repack",
        "--no-warmup",
        "-fit", "off",
        "--host", "127.0.0.1",
        "--port", str(PORT)
    ]

    log(f"-> Subindo llama-server...")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    server_ready = False
    for i in range(120):
        time.sleep(1.0)
        try:
            req = urllib.request.Request(f"{BASE_URL}/health")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    server_ready = True
                    break
        except Exception:
            pass

    if not server_ready:
        log("[FALHA BOOT] llama-server falhou ao subir na porta 8089!")
        stop_llama_server()
        sys.exit(1)

    log("[+] Servidor pronto (200 OK)! Iniciando baterias...")
    t0_all = time.time()
    res_13 = run_13_areas()
    res_opus = run_10_opus()
    total_elapsed = time.time() - t0_all

    stop_llama_server()

    # Salva resultado JSON
    m_id = "gemma_4_26b_claude_opus_distill_v2"
    m_name = "gemma-4-26B-A4B-it-Claude-Opus-Distill-v2"
    res_final = {
        "id": m_id,
        "name": m_name,
        "file": str(MODEL_PATH),
        "size_gb": 15.64,
        "arch": "Dense/MoE 26B Gemma-4 Claude Opus Distill v2",
        "status": "COMPLETED",
        "benchmark_13_areas": res_13,
        "benchmark_10_opus": res_opus,
        "total_elapsed_s": round(total_elapsed, 2),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    all_results = {}
    if PROOF_FILE.exists():
        try:
            with open(PROOF_FILE, "r", encoding="utf-8") as f:
                all_results = json.load(f)
        except Exception:
            all_results = {}

    all_results[m_id] = res_final
    with open(PROOF_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    log(f"\n[SUCESSO] Benchmark concluído:")
    log(f"   -> 13 Áreas: {res_13['passed_total']}/39 ({res_13['pass_rate_pct']}%)")
    log(f"   -> 10 Desafios Opus: {res_opus['passed_total']}/10 ({res_opus['pass_rate_pct']}%)")
    log(f"   -> Velocidade: Prompt {res_13['avg_pp_tok_s']} tok/s | Geração {res_13['avg_tg_tok_s']} tok/s")

    # Mover para Google Drive para liberar espaço no disco F:
    log("\n[*] Arquivando modelo no Google Drive (gdrive_01:AetherMind_High_Titans)...")
    rclone_cmd = [
        RCLONE_BIN,
        "move",
        str(MODEL_PATH),
        "gdrive_01:AetherMind_High_Titans/",
        "--config", RCLONE_CONF,
        "--progress"
    ]
    r_proc = subprocess.run(rclone_cmd)
    if r_proc.returncode == 0:
        log("[+] Modelo arquivado com sucesso no Google Drive! Espaço em F: liberado.")
    else:
        log(f"[AVISO] rclone move retornou código {r_proc.returncode}.")

if __name__ == "__main__":
    main()
