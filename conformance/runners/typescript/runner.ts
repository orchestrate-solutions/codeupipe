/**
 * TypeScript conformance runner: runs the cases and reports what happened.
 *
 *     node runner.ts <target> < cases.json > results.json
 *
 * Targets
 *     run      the Pipeline of packages/codeupipe-ts
 *     static   the same pipeline as plain code from packages/codeupipe-compile-ts,
 *              written to a file and imported from it
 *
 * The runner never judges; conformance/run.py compares the results of every
 * target with the same expectations. Node runs this file as it is (Node
 * 22.18 or later removes the types). The static target needs the compile
 * package to be installed (npm ci in packages/codeupipe-compile-ts). Plain
 * code has no State and no Hooks, so the static target reports neither.
 */
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

import { Payload, Pipeline, State } from "../../../packages/codeupipe-ts/src/index.ts";
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
import { RunAgainFilter } from "./cup-ops/run-again-filter.ts";
import { INNER_STATES, TAPS } from "./cup-ops/sink.ts";
import { TruthyPredicate } from "./cup-ops/truthy-predicate.ts";

type Spec = Record<string, any>;
type Case = { id: string; hooks?: boolean; given_state?: boolean; steps: Spec[]; input: Record<string, unknown> };

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
    case "run_again": return new RunAgainFilter(spec.input);
    default: throw new Unsupported(`unknown filter op '${spec.op}'`);
  }
}

function makeTap(spec: Spec): Tap {
  switch (spec.op) {
    case "record": return new RecordTap(spec.key);
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

function build(steps: Spec[], pipeline: Pipeline): Pipeline {
  for (const step of steps) {
    if (step.kind === "filter") {
      const filter = makeFilter(step);
      if (filter instanceof RunAgainFilter) filter.pipeline = pipeline;
      pipeline.addFilter(filter);
    } else if (step.kind === "tap") {
      pipeline.addTap(makeTap(step));
    } else if (step.kind === "valve") {
      pipeline.addValve(makePredicate(step.when), makeFilter(step.filter));
    } else if (step.kind === "pipeline") {
      pipeline.addPipeline(build(step.steps, new NestedPipeline()));
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
  const events: string[] = [];
  const pipeline = build(spec.steps, new Pipeline());
  const names = namesByLabel(pipeline, spec.steps);
  const named = (label: string) => names.get(label) ?? label;
  if (spec.hooks) pipeline.useHook(new RecordHook(events));

  const data = structuredClone(spec.input);
  const result: Record<string, unknown> = { id: spec.id };
  // With "given_state", the caller gives the State of the run. If not, the run makes one.
  const given = spec.given_state ? new State() : undefined;
  try {
    result.output = (await (given === undefined ? pipeline.run(new Payload(data)) : pipeline.run(new Payload(data), given))).toDict();
  } catch (error) {
    result.error = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
  }
  const report = (state: { executed: string[]; skipped: string[]; errors: Array<[string, unknown]> }) => ({
    executed: state.executed.map(named),
    skipped: state.skipped.map(named),
    errors: state.errors.map(([label]) => named(label)),
  });
  result.state = report(given ?? pipeline.state);
  result.pipeline_state = report(pipeline.state);
  result.inner_states = INNER_STATES.map(report);
  result.taps = [...TAPS];
  if (spec.hooks) {
    result.hooks = events.map((event) => {
      const at = event.indexOf(":");
      return event.slice(0, at + 1) + named(event.slice(at + 1));
    });
  }
  result.input_after = data;
  return result;
}

// -- the static target --------------------------------------------------

const HERE = import.meta.dirname;
const CLASS_OF: Record<string, [string, string]> = {
  set: ["SetFilter", "set-filter"], copy: ["CopyFilter", "copy-filter"], add: ["AddFilter", "add-filter"],
  append: ["AppendFilter", "append-filter"], remove: ["RemoveFilter", "remove-filter"],
  merge: ["MergeFilter", "merge-filter"], has: ["HasFilter", "has-filter"], mutate: ["MutateFilter", "mutate-filter"],
  fail: ["FailFilter", "fail-filter"], record: ["RecordTap", "record-tap"], "tap:fail": ["FailTap", "fail-tap"],
  noop: ["NoopTap", "noop-tap"], equals: ["EqualsPredicate", "equals-predicate"], truthy: ["TruthyPredicate", "truthy-predicate"],
};
const ARGUMENTS: Record<string, string[]> = {
  set: ["key", "value"], copy: ["from", "to"], add: ["key", "by"], append: ["key", "value"], remove: ["key"],
  merge: ["value"], has: ["key", "to"], mutate: ["key", "value"], fail: ["message"], record: ["key"],
  "tap:fail": ["message"], noop: [], equals: ["key", "value"], truthy: ["key"],
};

/** The case as the source of a pipeline class: the form that the compiler reads. */
function sourceOf(spec: Case): string {
  const imports = new Map<string, string>();
  const classes: string[] = [];
  const made = (op: string, step: Spec): string => {
    const entry = CLASS_OF[op];
    if (entry === undefined) throw new Unsupported(`unknown op '${op}'`);
    imports.set(entry[0], join(HERE, "cup-ops", entry[1] + ".ts"));
    return `new ${entry[0]}(${(ARGUMENTS[op] ?? []).map((name) => JSON.stringify(step[name])).join(", ")})`;
  };
  const pipelineClass = (name: string, steps: Spec[]): void => {
    const lines: string[] = [];
    for (const step of steps) {
      if (step.kind === "filter") {
        lines.push(`this.addFilter(${made(step.op, step)});`);
      } else if (step.kind === "tap") {
        lines.push(`this.addTap(${made(step.op === "fail" ? "tap:fail" : step.op, step)});`);
      } else if (step.kind === "valve") {
        lines.push(`this.addValve(${made(step.when.op, step.when)}, ${made(step.filter.op, step.filter)});`);
      } else if (step.kind === "pipeline") {
        const inner = `Inner${classes.length + 1}Pipeline`;
        classes.push(""); // keeps the place, so that each nested class has its own number
        pipelineClass(inner, step.steps);
        lines.push(`this.addPipeline(new ${inner}());`);
      } else {
        throw new Unsupported(`unknown step kind '${step.kind}'`);
      }
    }
    classes.push(`export class ${name} extends Pipeline {\n  constructor() {\n    super();\n${lines.map((line) => "    " + line).join("\n")}\n  }\n}`);
  };
  pipelineClass("CasePipeline", spec.steps);
  const head = [`import { Pipeline } from ${JSON.stringify(join(HERE, "../../../packages/codeupipe-ts/src/index.ts"))};`,
    ...[...imports].map(([name, file]) => `import { ${name} } from ${JSON.stringify(file)};`)];
  return [...head, "", ...classes.filter((text) => text !== "")].join("\n") + "\n";
}

type Compile = (file: string, className: string, options: { outFile: string }) => Promise<string>;

async function runStatic(spec: Case, compile: Compile, directory: string, index: number): Promise<Record<string, unknown>> {
  if (spec.steps.some((step) => step.op === "run_again")) {
    throw new Unsupported("the compiled form is one function: it has no Pipeline that a step can run again");
  }
  const sourceFile = join(directory, `case-${index}-pipeline.ts`);
  const outFile = join(directory, `case-${index}-compiled.ts`);
  writeFileSync(sourceFile, sourceOf(spec));
  try {
    await compile(sourceFile, "CasePipeline", { outFile });
  } catch (error) {
    if (error instanceof Error && error.name === "CompileRefusal") throw new Unsupported(error.message);
    throw error;
  }
  const compiled: { run(input: Record<string, unknown>): Promise<Record<string, unknown>> } = await import(pathToFileURL(outFile).href);

  const data = structuredClone(spec.input);
  const result: Record<string, unknown> = { id: spec.id };
  try {
    result.output = await compiled.run(data);
  } catch (error) {
    result.error = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
  }
  result.taps = [...TAPS];
  result.input_after = data;
  return result;
}

// -- main -----------------------------------------------------------------

const target = process.argv[2];
if (target !== "run" && target !== "static") {
  console.error(`unknown target '${target}'. The targets are: run, static`);
  process.exit(2);
}
let compile: Compile | undefined;
let directory = "";
if (target === "static") {
  ({ compile } = await import("../../../packages/codeupipe-compile-ts/src/index.ts"));
  directory = mkdtempSync(join(tmpdir(), "cup-conformance-"));
}

const cases: Case[] = JSON.parse(readFileSync(0, "utf8"));
const results: Record<string, unknown>[] = [];
for (const [index, spec] of cases.entries()) {
  TAPS.length = 0;
  INNER_STATES.length = 0;
  try {
    results.push(compile === undefined ? await runCase(spec) : await runStatic(spec, compile, directory, index));
  } catch (error) {
    if (!(error instanceof Unsupported)) throw error;
    results.push({ id: spec.id, unsupported: error.message });
  }
}
process.stdout.write(JSON.stringify(results));
