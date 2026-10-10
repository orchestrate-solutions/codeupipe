/**
 * The label of a step: the name of its class. State and Hooks report a step
 * by this label.
 */
export function labelOf(step: unknown): string {
  const type = (step as { constructor?: { name?: unknown } } | null | undefined)?.constructor;
  const name = type?.name;
  return typeof name === "string" && name !== "" ? name : "anonymous";
}
