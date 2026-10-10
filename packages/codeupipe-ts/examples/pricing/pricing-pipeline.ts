import { Pipeline } from "../../src/index.ts";
import { AtLeastPredicate } from "./at-least-predicate.ts";
import { AuditTap } from "./audit-tap.ts";
import { DiscountFilter } from "./discount-filter.ts";
import { MarkBulkFilter } from "./mark-bulk-filter.ts";

/** The pipeline file: the place where the steps come together. */
export class PricingPipeline extends Pipeline {
  constructor() {
    super();
    this.addFilter(new DiscountFilter(0.1));
    // MarkBulkFilter runs only when the predicate is true.
    this.addValve(new AtLeastPredicate("qty", 10), new MarkBulkFilter());
    // A Tap failure is recorded and does not stop the run.
    this.addTap(new AuditTap());
  }
}
