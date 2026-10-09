"""Python native hop bench — matches cpp schema.
Usage: python bench_hop.py [filters] [iterations]
"""
import asyncio, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from codeupipe.core.payload import Payload
from codeupipe.core.pipeline import Pipeline


class IncFilter:
    def __init__(self, i): self._name = f"inc_{i}"
    @property
    def name(self): return self._name
    async def call(self, payload):
        n = payload.get("n") or 0
        return payload.insert("n", n + 1)


async def main(filters: int, iters: int):
    pipe = Pipeline()
    for i in range(filters):
        pipe.add_filter(IncFilter(i), name=f"inc_{i}")  # cup: allow-anonymous (upstream codeupipe bench; not the codeupipe runtime)

    seed = Payload({"n": 0})
    for _ in range(1000):
        await pipe.run(seed)

    t0 = time.perf_counter_ns()
    out = seed
    for _ in range(iters):
        out = await pipe.run(seed)
    ns_total = time.perf_counter_ns() - t0

    ns_per_iter = ns_total / iters
    ns_per_hop = ns_per_iter / filters
    print(json.dumps({
        "runtime": "python",
        "variant": "async",
        "filters": filters,
        "iterations": iters,
        "ns_per_iter": round(ns_per_iter, 2),
        "ns_per_hop": round(ns_per_hop, 2),
        "ops_per_sec": round(1e9 / ns_per_iter),
        "final_n": out.get("n"),
    }))


if __name__ == "__main__":
    fs = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    it = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
    asyncio.run(main(fs, it))
