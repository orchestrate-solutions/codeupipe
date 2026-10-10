import { Pipeline } from "codeupipe";

import { EmitModuleFilter } from "./emit-module-filter.ts";
import { LowerStepsFilter } from "./lower-steps-filter.ts";
import { ResolvePipelineFilter } from "./resolve-pipeline-filter.ts";

/** The compiler, as a codeupipe pipeline. */
export class CompilePipeline extends Pipeline {
  constructor() {
    super();
    this.addFilter(new ResolvePipelineFilter()); // the pipeline class to a list of steps
    this.addFilter(new LowerStepsFilter()); // each step to a plain function
    this.addFilter(new EmitModuleFilter()); // the functions to one module
  }
}
