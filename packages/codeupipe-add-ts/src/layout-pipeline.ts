// LayoutPipeline: `codeupipe add --layout` for TypeScript (ADD.md, "Phase 2: a layout").
//
// Steps:
//   1. ReadLayoutFilter       the file, as data
//   2. CheckLayoutFilter      the keys, and the shape of each
//   3. NameComponentsFilter   the names and the paths of phase 1
//   4. ResolveStepsFilter     the calls and the imports of each pipeline
//   5. RenderLayoutFilter     the text of the files
//   6. WriteLayoutFilter      the files that are not there yet
//   7. StalePipelinesFilter   a kept pipeline whose steps changed
import { Pipeline } from "codeupipe";

import { CheckLayoutFilter } from "./check-layout-filter.ts";
import { NameComponentsFilter } from "./name-components-filter.ts";
import { ReadLayoutFilter } from "./read-layout-filter.ts";
import { RenderLayoutFilter } from "./render-layout-filter.ts";
import { ResolveStepsFilter } from "./resolve-steps-filter.ts";
import { StalePipelinesFilter } from "./stale-pipelines-filter.ts";
import { WriteLayoutFilter } from "./write-layout-filter.ts";

/**
 * Input keys: `root`, `layout_path`.
 * Output keys: `written`, `kept`, `stale`. The whole layout is checked
 * before a file is written: a step that cannot go on throws Refusal.
 */
export class LayoutPipeline extends Pipeline {
  constructor() {
    super();
    this.addFilter(new ReadLayoutFilter()); // the file, as data
    this.addFilter(new CheckLayoutFilter()); // the keys, and the shape of each
    this.addFilter(new NameComponentsFilter()); // the names and the paths of phase 1
    this.addFilter(new ResolveStepsFilter()); // the calls and the imports of each pipeline
    this.addFilter(new RenderLayoutFilter()); // the text of the files
    this.addFilter(new WriteLayoutFilter()); // the files that are not there yet
    this.addFilter(new StalePipelinesFilter()); // a kept pipeline whose steps changed
  }
}
