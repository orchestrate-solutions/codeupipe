import type ts from "typescript";

import type { ClassRef, Source } from "./source-files.ts";

/** A step class, with the arguments that the pipeline gives to its constructor. */
export type Made = { ref: ClassRef; args: readonly ts.Expression[]; argSource: Source };

/** One step of the pipeline, in the order of the run. A nested pipeline is already flattened. */
export type StepPlan =
  | { kind: "filter"; filter: Made }
  | { kind: "valve"; predicate: Made; filter: Made }
  | { kind: "tap"; tap: Made };

/** One step as plain code. */
export type LoweredFunction = {
  /** The name of the function. */
  name: string;
  /** The constants that hold the settings of the instance. */
  consts: string[];
  /** The function. */
  code: string;
  isAsync: boolean;
  /** The identifiers that the constants and the function use. */
  names: Set<string>;
  /** The file that the class is in. */
  source: Source;
};

export type LoweredStep =
  | { kind: "filter"; filter: LoweredFunction }
  | { kind: "valve"; predicate: LoweredFunction; filter: LoweredFunction }
  | { kind: "tap"; tap: LoweredFunction };
