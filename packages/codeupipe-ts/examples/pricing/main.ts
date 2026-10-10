// node examples/pricing/main.ts: run the pipeline with a Hook and show its State.
import { Payload } from "../../src/index.ts";
import { PricingPipeline } from "./pricing-pipeline.ts";
import { PrintStepsHook } from "./print-steps-hook.ts";

const pipeline = new PricingPipeline();
pipeline.useHook(new PrintStepsHook());

console.log("steps:");
const result = await pipeline.run(new Payload({ price: 100.0, qty: 12 }));

console.log("result:  ", result.toDict());
console.log("executed:", pipeline.state.executed);
console.log("skipped: ", pipeline.state.skipped);
console.log("errors:  ", pipeline.state.errors.map(([label, error]) => [label, String(error)]));
