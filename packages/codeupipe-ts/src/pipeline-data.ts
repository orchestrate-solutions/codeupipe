/**
 * What a Pipeline carries from step to step.
 *
 * `Payload` is the default: a map that any developer can read, and that
 * every runtime of codeupipe has. A class of your own can take its place,
 * such as the class that your steps would use anyway:
 *
 *     class Order implements PipelineData<Order> {
 *       copy(): Order { ... }
 *     }
 *     class DiscountFilter implements Filter<Order> { ... }
 *     const pipeline = new Pipeline<Order>();
 *
 * The Pipeline asks one thing of it, `copy()`, for the copy that a run works
 * on. The Filters, Predicates, Taps and Hooks of that pipeline then take the
 * class, and a step for another type does not type-check.
 *
 * Lineage (`observe({ lineage: true })`) is kept only by a type that has
 * `_stamp(label)`, as Payload has. For any other type it does nothing.
 */
export interface PipelineData<P> {
  copy(): P;
  _stamp?(label: string): unknown;
}
