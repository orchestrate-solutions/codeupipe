/**
 * TypeScript conformance runner: runs the cases and reports what happened.
 *
 *     node runner.ts run < cases.json > results.json
 *
 * The runner never judges; conformance/run.py compares the results of every
 * target with the same expectations. Node runs this file as it is (Node
 * 22.18 or later removes the types), so nothing is built or downloaded.
 */
import { readFileSync } from "node:fs";

import { Payload, Pipeline } from "../../../packages/codeupipe-ts/src/index.ts";
import type { Filter, Predicate, Tap } from "../../../packages/codeupipe-ts/src/index.ts";
import { AddFilter } from "./cup-ops/add-filter.ts";
import { AppendFilter } from "./cup-ops/append-filter.ts";
import { CopyFilter } from "./cup-ops/copy-filter.ts";
import { EqualsPredicate } from "./cup-ops/equals-predicate.ts";
import { FailFilter } from "./cup-ops/fail-filter.ts";
import { FailTap } from "./cup-ops/fail-tap.ts";
import { HasFilter } from "./cup-ops/has-filter.ts";
import { MergeFilter } from "./cup-ops/merge-filter.ts";
import { MutateFilter } from "./cup-ops/mutate-filter.ts";
import { NestedPipeline } from "./cup-ops/nested-pipeline.ts";
import { NoopTap } from "./cup-ops/noop-tap.ts";
import { RecordHook } from "./cup-ops/record-hook.ts";
import { RecordTap } from "./cup-ops/record-tap.ts";
import { RemoveFilter } from "./cup-ops/remove-filter.ts";
import { SetFilter } from "./cup-ops/set-filter.ts";
import { TruthyPredicate } from "./cup-ops/truthy-predicate.ts";

type Spec = Record<string, any>;
type Case = { id: string; hooks?: boolean; steps: Spec[]; input: Record<string, unknown> };

class Unsupported extends Error {}

function makeFilter(spec: Spec): Filter {
  switch (spec.op) {
    case "set": return new SetFilter(spec.key, spec.value);
    case "copy": return new CopyFilter(spec.from, spec.to);
    case "add": return new AddFilter(spec.key, spec.by);
    case "append": return new AppendFilter(spec.key, spec.value);
    case "remove": return new RemoveFilter(spec.key);
    case "merge": return new MergeFilter(spec.value);
    case "has": return new HasFilter(spec.key, spec.to);
    case "mutate": return new MutateFilter(spec.key, spec.value);
    case "fail": return new FailFilter(spec.message);
    default: throw new Unsupported(`unknown filter op '${spec.op}'`);
  }
}

function makeTap(spec: Spec, taps: unknown[]): Tap {
  switch (spec.op) {
    case "record": return new RecordTap(spec.key, taps);
    case "fail": return new FailTap(spec.message);
    case "noop": return new NoopTap();
    default: throw new Unsupported(`unknown tap op '${spec.op}'`);
  }
}

function makePredicate(when: Spec): Predicate {
  switch (when.op) {
    case "equals": return new EqualsPredicate(when.key, when.value);
    case "truthy": return new TruthyPredicate(when.key);
    default: throw new Unsupported(`unknown valve op '${when.op}'`);
  }
}

function build(steps: Spec[], pipeline: Pipeline, taps: unknown[]): Pipeline {
  for (const step of steps) {
    if (step.kind === "filter") {
      pipeline.addFilter(makeFilter(step));
    } else if (step.kind === "tap") {
      pipeline.addTap(makeTap(step, taps));
    } else if (step.kind === "valve") {
      pipeline.addValve(makePredicate(step.when), makeFilter(step.filter));
    } else if (step.kind === "pipeline") {
      pipeline.addPipeline(build(step.steps, new NestedPipeline(), taps));
    } else {
      throw new Unsupported(`unknown step kind '${step.kind}'`);
    }
  }
  return pipeline;
}

/**
 * Label to the step name of the case. The cases name their steps, and the
 * runtime reports labels (conformance/API.md). The steps are added in the
 * order of the case, so the two lists are side by side. A label that the
 * runtime reports and that is not in this map stays as it is, and fails the
 * comparison.
 */
function namesByLabel(pipeline: Pipeline, steps: Spec[]): Map<string, string> {
  return new Map(pipeline.labels.map((label, index) => [label, String(steps[index]?.name)]));
}

async function runCase(spec: Case): Promise<Record<string, unknown>> {
  const taps: unknown[] = [];
  const events: string[] = [];
  const pipeline = build(spec.steps, new Pipeline(), taps);
  const names = namesByLabel(pipeline, spec.steps);
  const named = (label: string) => names.get(label) ?? label;
  if (spec.hooks) pipeline.useHook(new RecordHook(events));

  const data = structuredClone(spec.input);
  const result: Record<string, unknown> = { id: spec.id };
  try {
    result.output = (await pipeline.run(new Payload(data))).toDict();
  } catch (error) {
    result.error = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
  }
  const state = pipeline.state;
  result.state = {
    executed: state.executed.map(named),
    skipped: state.skipped.map(named),
    errors: state.errors.map(([label]) => named(label)),
  };
  result.taps = taps;
  if (spec.hooks) {
    result.hooks = events.map((event) => {
      const at = event.indexOf(":");
      return event.slice(0, at + 1) + named(event.slice(at + 1));
    });
  }
  result.input_after = data;
  return result;
}

const target = process.argv[2];
if (target !== "run") {
  console.error(`unknown target '${target}'. The target is: run`);
  process.exit(2);
}

const cases: Case[] = JSON.parse(readFileSync(0, "utf8"));
const results: Record<string, unknown>[] = [];
for (const spec of cases) {
  try {
    results.push(await runCase(spec));
  } catch (error) {
    if (!(error instanceof Unsupported)) throw error;
    results.push({ id: spec.id, unsupported: error.message });
  }
}
process.stdout.write(JSON.stringify(results));
