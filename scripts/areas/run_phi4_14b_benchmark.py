"""
Runner dedicado para o unsloth-Phi-4-reasoning-14B:
13 Areas Cognitivas (39 testes duais) + 10 Desafios Opus/Fable Pytest.
"""
import ctypes, json, os, subprocess, sys, time, urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LAMBDA_RLM_DIR = ROOT / "lambda_rlm"
if str(LAMBDA_RLM_DIR) not in sys.path:
    sys.path.insert(0, str(LAMBDA_RLM_DIR))

from benchmark_g9v3_english import SUITE_13_AREAS_EN, OPUS_10_TESTS_EN
from rlm import LambdaRLM
from router.formal_verifier import formal_verifier

PORT = 8089
SERVER_BIN = r"F:\tools\lc\bin\llama-server.exe"
PROOF_PATH = Path(r"F:\data\proof_reteste_18_titas_fable_dual.json")
LOG_PATH = Path(r"F:\data\reteste_phi4_14b.log")
MODEL_PATH = Path(r"E:\models\phi-4-reasoning-Q4_K_M.gguf")

def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def purge_ram():
    psapi = ctypes.windll.psapi
    kernel32 = ctypes.windll.kernel32
    PROCESS_SET_QUOTA = 0x0100
    PROCESS_QUERY_INFORMATION = 0x0400
    try:
        import psutil
        for p in psutil.process_iter(['pid']):
            try:
                if p.pid > 4:
                    h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA, False, p.pid)
                    if h:
                        psapi.EmptyWorkingSet(h)
                        kernel32.CloseHandle(h)
            except Exception:
                pass
    except Exception:
        pass

def stop_any_llama_server():
    subprocess.run(["taskkill.exe", "/F", "/IM", "llama-server.exe", "/IM", "llama-cli.exe"], capture_output=True)
    time.sleep(1.0)
    purge_ram()

def start_safe_server(model_path: Path, port: int = PORT, timeout_s: float = 240.0) -> subprocess.Popen[str]:
    stop_any_llama_server()
    cmd = [
        SERVER_BIN,
        "-m", str(model_path),
        "-c", "2048",
        "-b", "512",
        "-ub", "128",
        "-t", "12",
        "-fit", "off",
        "--host", "127.0.0.1",
        "--port", str(port),
    ]
    log_server = open(r"F:\data\llama_phi4_14b_server.log", "w", encoding="utf-8")
    proc = subprocess.Popen(cmd, stdout=log_server, stderr=subprocess.STDOUT, text=True)

    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if proc.poll() is not None:
            raise RuntimeError(f"Servidor encerrou prematuramente (codigo: {proc.returncode})")
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/health")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    dt = time.time() - t0
                    log(f" -> [ONLINE ANTI-TDR] {model_path.name} pronto na porta {port} ({dt:.2f}s).")
                    return proc
        except Exception:
            time.sleep(1.5)
    proc.terminate()
    raise TimeoutError(f"Timeout ({timeout_s}s) ao carregar {model_path.name}")

def clean_code(raw: str) -> str:
    text = raw.strip()
    if "```python" in text:
        parts = text.split("```python")
        if len(parts) > 1:
            return parts[1].split("```")[0].strip()
    elif "```" in text:
        parts = text.split("```")
        if len(parts) > 1:
            return parts[1].split("```")[0].strip()
    return text

def query_normal(prompt: str, is_code: bool = False) -> tuple[str, float, float]:
    clean = prompt.replace("/no_think", "").strip()
    effective = f"{clean}\nWrite concise clean Python code only, no comments." if is_code else clean
    payload = json.dumps({"prompt": effective, "n_predict": 512, "temperature": 0.2, "cache_prompt": True}).encode("utf-8")
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/completion", data=payload, headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=90.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw = data.get("content", "").strip()
    except Exception as e:
        raw = f"[ERROR: {e}]"
    elapsed = max(0.001, time.perf_counter() - t0)
    final = clean_code(raw) if is_code else raw
    tps = round((len(raw) // 4) / elapsed, 2)
    lat_ms = round(elapsed * 1000.0, 2)
    return final, tps, lat_ms

def query_lambda(engine: LambdaRLM, prompt: str, is_code: bool = False) -> tuple[str, float, float]:
    clean = prompt.replace("/no_think", "").strip()
    effective = f"{clean}\nWrite concise clean Python code only, no comments." if is_code else clean
    t0 = time.perf_counter()
    try:
        res = engine.completion(effective)
        raw = res.response.strip()
    except Exception as e:
        raw = f"[ERROR: {e}]"
    elapsed = max(0.001, time.perf_counter() - t0)
    final = clean_code(raw) if is_code else raw
    tps = round((len(raw) // 4) / elapsed, 2)
    lat_ms = round(elapsed * 1000.0, 2)
    return final, tps, lat_ms

def main():
    log("=" * 80)
    log("   AETHERMIND APOTHEOSIS - RETESTE DUAL: unsloth-Phi-4-reasoning-14B")
    log("   Baterias: 13 Areas (39 Testes EN) + 10 Desafios Opus/Fable")
    log("   Modo DUAL: Inferencia Normal vs Lambda-RLM")
    log("=" * 80)

    report: dict[str, Any] = {"contenders": {}}
    if PROOF_PATH.exists():
        try:
            with open(PROOF_PATH, "r", encoding="utf-8") as f:
                report = json.load(f)
        except Exception:
            pass

    cid = "14.0B_phi4_reasoning_full"
    cname = "unsloth-Phi-4-reasoning-14B"
    fn = "phi-4-reasoning-Q4_K_M.gguf"
    size_gb = round(MODEL_PATH.stat().st_size / (1024**3), 2)

    proc = start_safe_server(MODEL_PATH, port=PORT, timeout_s=180.0)

    lambda_engine = LambdaRLM(
        backend="openai",
        backend_kwargs={
            "model_name": fn,
            "base_url": f"http://127.0.0.1:{PORT}/v1",
            "api_key": "none",
            "temperature": 0.1,
            "max_tokens": 512,
        },
        context_window_chars=2000,
        verbose=False,
    )

    cdata: dict[str, Any] = {
        "name": cname,
        "filename": fn,
        "category": "05_Jovem_Tita_9B_12B",
        "tier": "14B Full Reasoning Titan",
        "size_gb": size_gb,
        "normal": {"p1_areas_passed": 0, "p1_total": 0, "p2_opus_passed": 0, "p2_total": 0, "areas": {}, "opus": {}},
        "lambda_rlm": {"p1_areas_passed": 0, "p1_total": 0, "p2_opus_passed": 0, "p2_total": 0, "areas": {}, "opus": {}},
        "completed": False,
    }

    # Bateria 1: 13 Areas
    log(f"--- BATERIA 1: 13 AREAS COGNITIVAS EM INGLES (39 TESTES DUAIS) ---")
    p1_norm_pass, p1_lamb_pass, p1_total = 0, 0, 0
    for area in SUITE_13_AREAS_EN:
        aid = area["area_id"]
        aname = area["area_name"]
        cdata["normal"]["areas"][aid] = {"name": aname, "passed": 0, "total": len(area["tests"])}
        cdata["lambda_rlm"]["areas"][aid] = {"name": aname, "passed": 0, "total": len(area["tests"])}

        for t in area["tests"]:
            p1_total += 1
            prompt = t["prompt"]
            verify_fn = t["verify"]
            is_code = t.get("is_code", False)

            out_n, _, _ = query_normal(prompt, is_code=is_code)
            try:
                if bool(verify_fn(out_n)):
                    p1_norm_pass += 1
                    cdata["normal"]["areas"][aid]["passed"] += 1
            except Exception:
                pass

            out_l, _, _ = query_lambda(lambda_engine, prompt, is_code=is_code)
            try:
                if bool(verify_fn(out_l)):
                    p1_lamb_pass += 1
                    cdata["lambda_rlm"]["areas"][aid]["passed"] += 1
            except Exception:
                pass

        badge_n = f"{cdata['normal']['areas'][aid]['passed']}/{len(area['tests'])}"
        badge_l = f"{cdata['lambda_rlm']['areas'][aid]['passed']}/{len(area['tests'])}"
        log(f"  {aname[:45]:<45} | Normal: {badge_n} | Lambda-RLM: {badge_l}")

    cdata["normal"]["p1_areas_passed"] = p1_norm_pass
    cdata["normal"]["p1_total"] = p1_total
    cdata["lambda_rlm"]["p1_areas_passed"] = p1_lamb_pass
    cdata["lambda_rlm"]["p1_total"] = p1_total
    log(f" -> [PLACAR 13 AREAS]: Normal: {p1_norm_pass}/{p1_total} | Lambda-RLM: {p1_lamb_pass}/{p1_total}")

    # Bateria 2: 10 Desafios Opus/Fable
    log(f"--- BATERIA 2: 10 DESAFIOS CLAUDE OPUS/FABLE COM PYTEST FORMAL ---")
    p2_norm_pass, p2_lamb_pass = 0, 0
    for op in OPUS_10_TESTS_EN:
        op_id = op["id"]
        op_name = op["name"]
        prompt = op["prompt"]
        assertions = op["assertions"]

        code_n, tps_n, _ = query_normal(prompt, is_code=True)
        vr_n = formal_verifier.verify_python_code(code_n, assertions, timeout_s=4.0)
        pass_n = vr_n.passed
        if pass_n: p2_norm_pass += 1

        code_l, tps_l, _ = query_lambda(lambda_engine, prompt, is_code=True)
        vr_l = formal_verifier.verify_python_code(code_l, assertions, timeout_s=4.0)
        pass_l = vr_l.passed
        if not pass_l:
            err = getattr(vr_l, "details", getattr(vr_l, "counterexample", "Assertion error"))
            repair_prompt = f"{prompt}\nPrevious code failed with:\n{err}\nFix the code and output only clean Python."
            code_rep, _, _ = query_lambda(lambda_engine, repair_prompt, is_code=True)
            vr_rep = formal_verifier.verify_python_code(code_rep, assertions, timeout_s=4.0)
            pass_l = vr_rep.passed

        if pass_l: p2_lamb_pass += 1

        bn = "PASS" if pass_n else "FAIL"
        bl = "PASS" if pass_l else "FAIL"
        log(f"  {op_name[:38]:<38} | Normal: [{bn:4s}] | Lambda-RLM: [{bl:4s}]")
        cdata["normal"]["opus"][op_id] = {"passed": pass_n, "tps": tps_n}
        cdata["lambda_rlm"]["opus"][op_id] = {"passed": pass_l, "tps": tps_l}

    cdata["normal"]["p2_opus_passed"] = p2_norm_pass
    cdata["normal"]["p2_total"] = len(OPUS_10_TESTS_EN)
    cdata["lambda_rlm"]["p2_opus_passed"] = p2_lamb_pass
    cdata["lambda_rlm"]["p2_total"] = len(OPUS_10_TESTS_EN)
    log(f" -> [PLACAR 10 OPUS]: Normal: {p2_norm_pass}/10 | Lambda-RLM: {p2_lamb_pass}/10")

    cdata["completed"] = True
    report["contenders"][cid] = cdata
    with open(PROOF_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    log(f"[SALVO] Prova de {cname} gravada com sucesso em {PROOF_PATH}!")
    proc.terminate()
    stop_any_llama_server()
    time.sleep(2.0)
    log("=== RETESTE DO PHI-4-14B FINALIZADO COM SUCESSO! ===")

if __name__ == "__main__":
    main()
