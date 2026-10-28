import { Pipeline } from "codeupipe";

import { AnalyzeOutsideWritesFilter } from "./analyze-outside-writes-filter.ts";
import { AnalyzePlainLogicFilter } from "./analyze-plain-logic-filter.ts";
import { AnalyzePrimitiveNamesFilter } from "./analyze-primitive-names-filter.ts";
import { AnalyzeStaleMarkersFilter } from "./analyze-stale-markers-filter.ts";
import { AnalyzePrimitivesPerFileFilter } from "./analyze-primitives-per-file-filter.ts";
import { AnalyzeStateReadsFilter } from "./analyze-state-reads-filter.ts";
import { AnalyzeStepsFilter } from "./analyze-steps-filter.ts";
import { ApplySuppressionsFilter } from "./apply-suppressions-filter.ts";
import { CollectFilesFilter } from "./collect-files-filter.ts";
import { DropDisabledFilter } from "./drop-disabled-filter.ts";
import { FormatReportFilter } from "./format-report-filter.ts";
import { ParseFilesFilter } from "./parse-files-filter.ts";

/** The linter, as a codeupipe pipeline. */
export class LintPipeline extends Pipeline {
  constructor() {
    super();
    this.addFilter(new CollectFilesFilter()); // paths to files
    this.addFilter(new ParseFilesFilter()); // files to syntax trees (CUP-I000)
    this.addFilter(new AnalyzeStepsFilter()); // CUP-A001, A002, A003, A005, A008, A009
    this.addFilter(new AnalyzeStateReadsFilter()); // CUP-I003
    this.addFilter(new AnalyzeOutsideWritesFilter()); // CUP-I004
    this.addFilter(new AnalyzePrimitivesPerFileFilter()); // CUP-I005
    this.addFilter(new AnalyzePrimitiveNamesFilter()); // CUP-I006, CUP-I007
    this.addFilter(new AnalyzePlainLogicFilter()); // CUP-I008, a warning
    this.addFilter(new ApplySuppressionsFilter());
    this.addFilter(new AnalyzeStaleMarkersFilter()); // CUP-I009, a warning
    this.addFilter(new DropDisabledFilter()); // last, so that a comment for a rule that is off is not stale
    this.addFilter(new FormatReportFilter());
  }
}
