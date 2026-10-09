// TypeScript native hop bench — uses the built dist/. Matches cpp schema.
// Run: node runtimes/ts/bench/bench_hop.js [filters] [iters]
import { Payload, Pipeline } from "../dist/index.js";

const filters = parseInt(process.argv[2] ?? "8", 10);
const iters   = parseInt(process.argv[3] ?? "200000", 10);

class Inc {
  constructor(i) { this.i = i; this.name = `inc_${i}`; }
  async call(p) {
    const n = (p.get("n") ?? 0);
    return p.insert("n", n + 1);
  }
}

const pipe = new Pipeline();
for (let i = 0; i < filters; i++) pipe.addFilter(new Inc(i), `inc_${i}`);

const seed = new Payload({ n: 0 });
for (let i = 0; i < 1000; i++) await pipe.run(seed);

const t0 = process.hrtime.bigint();
let out = seed;
for (let i = 0; i < iters; i++) out = await pipe.run(seed);
const nsTotal = Number(process.hrtime.bigint() - t0);

const nsPerIter = nsTotal / iters;
const nsPerHop  = nsPerIter / filters;
console.log(JSON.stringify({
  runtime: "typescript",
  variant: "async",
  filters, iterations: iters,
  ns_per_iter: +nsPerIter.toFixed(2),
  ns_per_hop:  +nsPerHop.toFixed(2),
  ops_per_sec: Math.round(1e9 / nsPerIter),
  final_n:     out.get("n"),
}));
