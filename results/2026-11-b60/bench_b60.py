#!/usr/bin/env python3
"""bench_b60.py — reproducible throughput/latency/VRAM benchmark of every model lane
currently serving on the Intel Arc Pro B60 in this host.

Lanes are discovered live: every llama-server process whose --device resolves to the
Arc (Vulkan0 on both llama.cpp builds in use) is benchmarked in place, co-resident,
exactly as production runs it. Nothing is started or stopped.

For each generation lane x each context fill (prompt size) x REPS:
  * prompt built to N tokens via the lane's own /tokenize + /detokenize
  * POST /completion  stream=true  cache_prompt=false  n_predict=GEN  temperature=0
  * TTFT        = wall time to the first streamed token (client-side)
  * prefill t/s = server timings.prompt_per_second
  * decode t/s  = server timings.predicted_per_second
  * VRAM        = xe fdinfo drm-total-vram0 of the lane pid (baseline + peak during run)
Rerank lane: /v1/rerank with 8/32/64 docs, latency + docs/s + VRAM.

Usage:  sudo -n true && python3 bench_b60.py [--reps 3] [--out DIR]
(sudo is only used to read /proc/<pid>/fdinfo of root-owned lanes.)
"""
import argparse, csv, json, os, re, statistics, subprocess, sys, threading, time, datetime, platform
import urllib.request

CTX_FILLS = [1024, 4096, 7680]      # prompt tokens; 7680+GEN fits the 8192 per-slot lanes
GEN = 128
RERANK_DOCS = [8, 32, 64]
FILLER = ("The Arc Pro B60 is a 24 GB workstation GPU. Vulkan is the backend. "
          "Context length changes prefill cost and KV cache size but decode speed is mostly "
          "bandwidth bound. This sentence exists only to fill tokens for a benchmark. ")

def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout

def http(url, body=None, timeout=600, stream=False):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"content-type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout)

def jget(url, body=None, timeout=120):
    with http(url, body, timeout) as r:
        return json.load(r)

# ---------- discovery ----------
def list_devices(binary):
    out = sh(f"{binary} --list-devices 2>/dev/null")
    return dict(re.findall(r"(Vulkan\d+): (.+?) \(\d+ MiB", out))

def discover():
    lanes = []
    # root-owned lanes only show their pid to a root ss; fall back to plain ss if sudo -n is refused
    ss_out = sh("sudo -n ss -lntpH 2>/dev/null") or sh("ss -lntpH")
    for line in ss_out.splitlines():
        m = re.search(r":(\d+)\s.*pid=(\d+)", line)
        if not m or "llama-server" not in line: continue
        port, pid = int(m.group(1)), int(m.group(2))
        argv = open(f"/proc/{pid}/cmdline", "rb").read().split(b"\0")
        argv = [a.decode() for a in argv if a]
        def flag(f, default=None):
            return argv[argv.index(f) + 1] if f in argv else default
        dev = flag("--device")
        devname = list_devices(argv[0]).get(dev, "?") if dev else "?"
        if "Arc" not in devname and "BMG" not in devname: continue
        lanes.append(dict(port=port, pid=pid, binary=argv[0], device=dev, device_name=devname.strip(),
                          model_path=flag("-m") or flag("--model"), alias=flag("--alias"),
                          rerank=("--rerank" in argv or "--reranking" in argv),
                          owner=sh(f"ps -o user= -p {pid}").strip()))
    lanes.sort(key=lambda l: l["port"])
    return lanes

def vram_mib(pid):
    """Sum drm-total-vram0 across distinct DRM clients of this pid (xe driver fdinfo)."""
    txt = sh(f"sudo -n sh -c 'cat /proc/{pid}/fdinfo/*' 2>/dev/null")  # glob must expand as root
    seen, total, cid = {}, 0, None
    for l in txt.splitlines():
        if l.startswith("drm-client-id:"): cid = l.split()[1]
        elif l.startswith("drm-total-vram0:") and cid is not None:
            seen[cid] = int(l.split()[1])
    return round(sum(seen.values()) / 1024, 1)

class Peak:
    def __init__(self, pid): self.pid, self.peak, self.run = pid, 0, True
    def __enter__(self):
        def loop():
            while self.run:
                self.peak = max(self.peak, vram_mib(self.pid)); time.sleep(0.25)
        self.t = threading.Thread(target=loop, daemon=True); self.t.start(); return self
    def __exit__(self, *a): self.run = False; self.t.join()

# ---------- generation bench ----------
def build_prompt(base, n_tokens):
    text = FILLER * (n_tokens // 20 + 2)
    toks = jget(f"{base}/tokenize", {"content": text})["tokens"][:n_tokens - 8]
    body = jget(f"{base}/detokenize", {"tokens": toks})["content"]
    return body + "\n\nSummarize the above in one sentence."

def one_run(base, prompt):
    body = {"prompt": prompt, "n_predict": GEN, "cache_prompt": False, "temperature": 0,
            "stream": True, "samplers": ["temperature"]}
    t0 = time.perf_counter(); ttft = None; last = None
    with http(f"{base}/completion", body, timeout=900) as r:
        for raw in r:
            raw = raw.decode().strip()
            if not raw.startswith("data:"): continue
            d = json.loads(raw[5:])
            if ttft is None and d.get("content"): ttft = time.perf_counter() - t0
            if d.get("stop"): last = d
    wall = time.perf_counter() - t0
    t = last.get("timings", {})
    return dict(ttft_ms=round(ttft * 1000, 1), wall_s=round(wall, 3),
                prompt_tokens=t.get("prompt_n"), gen_tokens=t.get("predicted_n"),
                prefill_tok_s=round(t.get("prompt_per_second", 0), 1),
                decode_tok_s=round(t.get("predicted_per_second", 0), 2))

def bench_gen(lane, reps, raw):
    base = f"http://127.0.0.1:{lane['port']}"
    props = jget(f"{base}/props")
    slot_ctx = props["default_generation_settings"]["n_ctx"]; slots = props.get("total_slots")
    rows = []
    for fill in CTX_FILLS:
        if fill + GEN > slot_ctx:
            rows.append(dict(ctx_fill=fill, note=f"skipped: exceeds slot n_ctx {slot_ctx}")); continue
        prompt = build_prompt(base, fill)
        base_v = vram_mib(lane["pid"]); runs = []
        with Peak(lane["pid"]) as pk:
            for i in range(reps):
                r = one_run(base, prompt); r.update(lane=lane["alias"], ctx_fill=fill, rep=i); runs.append(r)
                raw.write(json.dumps(r) + "\n"); raw.flush()
                print(f"  {lane['alias']:16} ctx={fill:5} rep={i} ttft={r['ttft_ms']:7.1f}ms "
                      f"prefill={r['prefill_tok_s']:7.1f} t/s decode={r['decode_tok_s']:6.2f} t/s", flush=True)
        med = lambda k: statistics.median(x[k] for x in runs)
        rows.append(dict(ctx_fill=fill, prompt_tokens=runs[0]["prompt_tokens"], gen_tokens=runs[0]["gen_tokens"],
                         ttft_ms=round(med("ttft_ms"), 1), prefill_tok_s=round(med("prefill_tok_s"), 1),
                         decode_tok_s=round(med("decode_tok_s"), 2), wall_s=round(med("wall_s"), 2),
                         vram_mib_baseline=base_v, vram_mib_peak=pk.peak, note=""))
    for r in rows: r.update(slot_n_ctx=slot_ctx, slots=slots)
    return rows

def bench_rerank(lane, reps, raw):
    base = f"http://127.0.0.1:{lane['port']}"
    props = jget(f"{base}/props"); slot_ctx = props["default_generation_settings"]["n_ctx"]
    doc = (FILLER * 6)[:600]
    rows = []
    for n in RERANK_DOCS:
        docs = [f"Document {i}: {doc}" for i in range(n)]
        base_v = vram_mib(lane["pid"]); runs = []
        with Peak(lane["pid"]) as pk:
            for i in range(reps):
                t0 = time.perf_counter()
                j = jget(f"{base}/v1/rerank", {"model": "r", "query": "Which document describes the B60?", "documents": docs}, 300)
                wall = time.perf_counter() - t0
                ptok = (j.get("usage") or {}).get("prompt_tokens")
                r = dict(lane=lane["alias"], docs=n, rep=i, wall_s=round(wall, 3), prompt_tokens=ptok,
                         prefill_tok_s=round(ptok / wall, 1) if ptok else None, docs_per_s=round(n / wall, 1))
                runs.append(r); raw.write(json.dumps(r) + "\n"); raw.flush()
                print(f"  {lane['alias']:16} docs={n:3} rep={i} wall={wall:6.3f}s tok={ptok}", flush=True)
        med = lambda k: statistics.median(x[k] for x in runs if x[k] is not None)
        rows.append(dict(ctx_fill=runs[0]["prompt_tokens"] or n, prompt_tokens=runs[0]["prompt_tokens"], gen_tokens=0,
                         ttft_ms=round(med("wall_s") * 1000, 1), prefill_tok_s=round(med("prefill_tok_s"), 1) if runs[0]["prompt_tokens"] else None,
                         decode_tok_s=None, wall_s=round(med("wall_s"), 3), vram_mib_baseline=base_v, vram_mib_peak=pk.peak,
                         note=f"rerank {n} docs; ttft_ms = full rerank latency", slot_n_ctx=slot_ctx, slots=props.get("total_slots")))
    return rows

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    lanes = discover()
    if not lanes: sys.exit("no Arc-resident llama-server lanes found")
    gpu = lanes[0]["device_name"]
    env = dict(ts=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), host=platform.node(),
               kernel=platform.release(), gpu=gpu, reps=a.reps, gen_tokens=GEN, ctx_fills=CTX_FILLS,
               load_avg=os.getloadavg(), mesa=sh("vulkaninfo --summary 2>/dev/null | grep -m1 driverInfo").strip(),
               lanes=[{k: v for k, v in l.items()} for l in lanes],
               method="in-place, co-resident lanes, cache_prompt=false, temperature=0, median of reps; "
                      "VRAM = xe fdinfo drm-total-vram0 per lane pid")
    print(json.dumps(env, indent=1))
    json.dump(env, open(os.path.join(a.out, "env.json"), "w"), indent=2)
    raw = open(os.path.join(a.out, "raw_runs.jsonl"), "w")
    out = []
    for lane in lanes:
        print(f"== {lane['alias']} :{lane['port']} ({os.path.basename(lane['model_path'])}) on {lane['device']}={gpu}")
        rows = bench_rerank(lane, a.reps, raw) if lane["rerank"] else bench_gen(lane, a.reps, raw)
        for r in rows:
            r.update(ts=env["ts"], host=env["host"], gpu=gpu, port=lane["port"], alias=lane["alias"],
                     model=os.path.basename(lane["model_path"]).replace(".gguf", ""), kind="rerank" if lane["rerank"] else "generate")
            out.append(r)
    cols = ["ts", "host", "gpu", "port", "alias", "model", "kind", "slot_n_ctx", "slots", "ctx_fill", "prompt_tokens", "gen_tokens",
            "ttft_ms", "prefill_tok_s", "decode_tok_s", "wall_s", "vram_mib_baseline", "vram_mib_peak", "note"]
    with open(os.path.join(a.out, "results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(out)
    print(f"wrote {a.out}/results.csv ({len(out)} rows), raw_runs.jsonl, env.json")

if __name__ == "__main__":
    main()
