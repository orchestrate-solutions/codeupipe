// AddPipeline: `codeupipe add` for TypeScript, built as a codeupipe pipeline.
//
// Steps:
//   1. TypeNameFilter        kind and name -> DiscountFilter, discount-filter
//   2. PlanFilesFilter       the paths of the two files, and the import path
//   3. RefuseExistingFilter  a file that exists stops the run (exit 1)
//   4. RenderFilesFilter     the text of the two files
//   5. WriteFilesFilter      the files, on disk
import { Pipeline } from "codeupipe";

import { PlanFilesFilter } from "./plan-files-filter.ts";
import { RefuseExistingFilter } from "./refuse-existing-filter.ts";
import { RenderFilesFilter } from "./render-files-filter.ts";
import { TypeNameFilter } from "./type-name-filter.ts";
import { WriteFilesFilter } from "./write-files-filter.ts";

/**
 * Input keys: `root`, `kind`, `name`, `directory`, `description`.
 * Output keys: `written`. A step that cannot go on throws Refusal.
 */
export class AddPipeline extends Pipeline {
  constructor() {
    super();
    this.addFilter(new TypeNameFilter()); // the names of the type and of the file
    this.addFilter(new PlanFilesFilter()); // where the two files go
    this.addFilter(new RefuseExistingFilter()); // a file that exists stops the run
    this.addFilter(new RenderFilesFilter()); // the text of the two files
    this.addFilter(new WriteFilesFilter()); // the files, on disk
  }
}
