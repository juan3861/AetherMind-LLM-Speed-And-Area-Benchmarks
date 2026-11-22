import sys, os, time, json, types, importlib.machinery, ctypes, torch
from pathlib import Path
from typing import Any

# Mock mistral_common to prevent soxr/numpy2 crash
m = types.ModuleType('mistral_common')
m.__spec__ = importlib.machinery.ModuleSpec('mistral_common', None)
sys.modules['mistral_common'] = m

ROOT = Path(r"F:\rotor-llm")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

sys.path.insert(0, r"F:\data")
import dory_modeling
import gguf.quants as quants
from gguf.gguf_reader import GGUFReader
from transformers import PreTrainedTokenizerFast

from benchmark_g9v3_english import OPUS_10_TESTS_EN
from router.formal_verifier import formal_verifier

PROOF_PATH = Path(r"F:\data\proof_reteste_18_titas_fable_dual.json")
LOG_PATH = Path(r"F:\data\reteste_novos_contenders_dual.log")

def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def purge_ram():
    try:
        psapi = ctypes.windll.psapi
        kernel32 = ctypes.windll.kernel32
        PROCESS_SET_QUOTA = 0x0100
        PROCESS_QUERY_INFORMATION = 0x0400
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

def build_name_map():
    mapping = {
        "token_embd.weight": "backbone.embeddings.weight",
        "output.weight": "lm_head.weight",
        "output_scale.weight": "lm_head.logit_scale",
    }
    for i in range(72):
        mapping[f"blk.{i}.residual_alpha.weight"] = f"backbone.layers.{i}.attn_alpha" if i % 2 == 0 else f"backbone.layers.{i}.mlp_alpha"
        mapping[f"blk.{i}.attn_q.weight"] = f"backbone.layers.{i}.mixer.q_proj.weight"
        mapping[f"blk.{i}.attn_k.weight"] = f"backbone.layers.{i}.mixer.k_proj.weight"
        mapping[f"blk.{i}.attn_v.weight"] = f"backbone.layers.{i}.mixer.v_proj.weight"
        mapping[f"blk.{i}.attn_gate.weight"] = f"backbone.layers.{i}.mixer.g_proj.weight"
        mapping[f"blk.{i}.attn_output.weight"] = f"backbone.layers.{i}.mixer.o_proj.weight"
        mapping[f"blk.{i}.attn_qk_scale.weight"] = f"backbone.layers.{i}.mixer.sqk"
        mapping[f"blk.{i}.attn_gate_scale.weight"] = f"backbone.layers.{i}.mixer.s_gate"
        mapping[f"blk.{i}.ffn_gate.weight"] = f"backbone.layers.{i}.mixer.gate_proj.weight"
        mapping[f"blk.{i}.ffn_up.weight"] = f"backbone.layers.{i}.mixer.up_proj.weight"
        mapping[f"blk.{i}.ffn_down.weight"] = f"backbone.layers.{i}.mixer.down_proj.weight"
        mapping[f"blk.{i}.ffn_gate_scale.weight"] = f"backbone.layers.{i}.mixer.suv_gate"
        mapping[f"blk.{i}.ffn_up_scale.weight"] = f"backbone.layers.{i}.mixer.suv_up"
    return mapping

def load_dory_fp32(gguf_path: Path, cfg_path: Path):
    log(f"Lendo GGUF: {gguf_path.name} ({gguf_path.stat().st_size / (1024**3):.2f} GB)...")
    reader = GGUFReader(str(gguf_path))
    cfg = dory_modeling.DoryConfig.from_json(str(cfg_path))
    name_map = build_name_map()
    
    with torch.device("meta"):
        model = dory_modeling.DoryForCausalLM(cfg)
    
    state = {}
    t0 = time.time()
    for idx, t in enumerate(reader.tensors):
        if t.name in name_map:
            pt_name = name_map[t.name]
            deq = quants.dequantize(t.data, t.tensor_type)
            tensor_pt = torch.from_numpy(deq).to(torch.float32)
            target_param = dict(model.named_parameters())[pt_name]
            if tensor_pt.shape != target_param.shape:
                if tensor_pt.T.shape == target_param.shape:
                    tensor_pt = tensor_pt.T.contiguous()
            state[pt_name] = tensor_pt
            
    model.load_state_dict(state, strict=True, assign=True)
    dt = time.time() - t0
    log(f" -> [MODEL READY] 507 tensores carregados na memoria FP32 em {dt:.1f}s.")
    model.eval()
    return model

def clean_code(raw: str) -> str:
    text = raw.strip()
    if "<|im_end|>" in text:
        text = text.split("<|im_end|>")[0].strip()
    if "```python" in text:
        parts = text.split("```python")
        if len(parts) > 1:
            return parts[1].split("```")[0].strip()
    elif "```" in text:
        parts = text.split("```")
        if len(parts) > 1:
            return parts[1].split("```")[0].strip()
    return text

def generate(model, tok, prompt: str, max_new_tokens: int = 96, is_lambda: bool = False) -> tuple[str, float, float]:
    clean_p = prompt.replace("/no_think", "").strip()
    if is_lambda:
        user_msg = f"{clean_p}\n[Typed Contract: Strict Python function implementation only. Output valid Python code, no explanation, no markdown.]"
    else:
        user_msg = f"{clean_p}\nWrite concise clean Python code only, no comments."

    formatted = f"<|im_start|>user\n{user_msg}<|im_end|>\n<|im_start|>assistant\n<think>\n</think>"
    ids = torch.tensor([tok.encode(formatted)], dtype=torch.long)
    
    t0 = time.perf_counter()
    with torch.inference_mode():
        out_ids = model.generate(ids, max_new_tokens=max_new_tokens, n_loops=2, temperature=0.0, eos_ids=(11,))
    elapsed = max(0.001, time.perf_counter() - t0)
    
    raw = tok.decode(out_ids[0].tolist()).strip()
    final = clean_code(raw)
    tps = round(len(out_ids[0]) / elapsed, 2)
    lat_ms = round(elapsed * 1000.0, 2)
    return final, tps, lat_ms

def main():
    log("=" * 80)
    log("   AETHERMIND APOTHEOSIS - RETOMADA OPUS: NEMOTRON-LABS-DORY-4B")
    log("   Finalizando os 10 Desafios Claude Opus com Verificacao Formal")
    log("=" * 80)

    mpath = Path(r"E:\models\NVIDIA-Nemotron-Labs-Dory1.0-4B-Q5_K_M.gguf")
    cfg_path = Path(r"F:\rotor-llm\dory_meta\config.json")
    tok_path = Path(r"F:\rotor-llm\dory_meta\tokenizer.json")
    tok = PreTrainedTokenizerFast(tokenizer_file=str(tok_path))

    report = {}
    if PROOF_PATH.exists():
        with open(PROOF_PATH, "r", encoding="utf-8") as f:
            report = json.load(f)

    # Initialize with already audited 13 areas
    cid = "4.0B_nvidia_nemotron_dory1"
    cdata = {
        "name": "NVIDIA-Nemotron-Labs-Dory1.0-4B",
        "filename": "NVIDIA-Nemotron-Labs-Dory1.0-4B-Q5_K_M.gguf",
        "category": "04_Estagiario_4B_8B",
        "tier": "4B nGPT Base Titan",
        "size_gb": 3.42,
        "architecture": "dory_ngpt_native_pytorch",
        "normal": {"p1_areas_passed": 27, "p1_total": 39, "p2_opus_passed": 0, "p2_total": 10, "opus": {}},
        "lambda_rlm": {"p1_areas_passed": 33, "p1_total": 39, "p2_opus_passed": 0, "p2_total": 10, "opus": {}},
        "completed": False
    }

    model = load_dory_fp32(mpath, cfg_path)

    log(f"--- BATERIA 2: 10 DESAFIOS CLAUDE OPUS COM PYTEST FORMAL ---")
    p2_norm_pass, p2_lamb_pass = 0, 0
    for op in OPUS_10_TESTS_EN:
        op_id = op["id"]
        op_name = op["name"]
        prompt = op["prompt"]
        assertions = op["assertions"]

        # 1. Normal
        code_n, tps_n, _ = generate(model, tok, prompt, max_new_tokens=96, is_lambda=False)
        vr_n = formal_verifier.verify_python_code(code_n, assertions, timeout_s=4.0)
        pass_n = vr_n.passed
        if pass_n: p2_norm_pass += 1

        # 2. Lambda-RLM (with self-repair if needed)
        if pass_n:
            pass_l = True
            tps_l = tps_n
        else:
            code_l, tps_l, _ = generate(model, tok, prompt, max_new_tokens=96, is_lambda=True)
            vr_l = formal_verifier.verify_python_code(code_l, assertions, timeout_s=4.0)
            pass_l = vr_l.passed
            if not pass_l:
                err = getattr(vr_l, "details", getattr(vr_l, "counterexample", "Assertion error"))
                repair_prompt = f"{prompt}\nPrevious code failed with:\n{err}\nFix the code and output only clean Python."
                code_rep, _, _ = generate(model, tok, repair_prompt, max_new_tokens=96, is_lambda=True)
                vr_rep = formal_verifier.verify_python_code(code_rep, assertions, timeout_s=4.0)
                pass_l = vr_rep.passed

        if pass_l: p2_lamb_pass += 1

        bn = "PASS" if pass_n else "FAIL"
        bl = "PASS" if pass_l else "FAIL"
        log(f"  {op_name[:38]:<38} | Normal: [{bn:4s}] | Lambda-RLM: [{bl:4s}]")
        cdata["normal"]["opus"][op_id] = {"passed": pass_n, "tps": tps_n}
        cdata["lambda_rlm"]["opus"][op_id] = {"passed": pass_l, "tps": tps_l}

    cdata["normal"]["p2_opus_passed"] = p2_norm_pass
    cdata["lambda_rlm"]["p2_opus_passed"] = p2_lamb_pass
    cdata["completed"] = True
    report["contenders"][cid] = cdata

    with open(PROOF_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    log(f" -> [PLACAR 10 OPUS]: Normal: {p2_norm_pass}/10 | Lambda-RLM: {p2_lamb_pass}/10")
    log(f"[SUCESSO TOTAL] Prova de {cdata['name']} gravada com sucesso em {PROOF_PATH}!")
    del model
    purge_ram()

if __name__ == "__main__":
    main()
