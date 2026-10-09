/**
 * Raised when the synchronous `Pipeline.run()` meets async work: an `async`
 * filter, tap, or hook, or a step that returns a Promise. `run()` never
 * awaits; use `runAsync()` for pipelines with async steps (conformance/API.md).
 */
export class AsyncStepInSyncRun extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AsyncStepInSyncRun";
  }
}
