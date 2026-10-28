// The entry of the browser check. A bundler makes one script from this file.
// The script runs the pricing pipeline and puts the result on the page and
// on globalThis, where a test can read it.
import { Payload } from "../../../src/index.ts";
import { PricingPipeline } from "../pricing-pipeline.ts";

// The page of a browser. Node has none.
declare const document: { body: { textContent: string | null } } | undefined;

const pipeline = new PricingPipeline();
const output = (await pipeline.run(new Payload({ price: 100.0, qty: 12 }))).toDict();
const result = {
  output,
  labels: pipeline.labels,
  executed: pipeline.state.executed,
  errors: pipeline.state.errors.map(([label, error]) => [label, String(error)]),
};

(globalThis as { cupResult?: unknown }).cupResult = result;
if (typeof document !== "undefined") {
  document.body.textContent = JSON.stringify(result);
}
