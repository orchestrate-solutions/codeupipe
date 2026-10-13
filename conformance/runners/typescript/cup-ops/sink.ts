/** Where the Taps of the runner record what they see. The runner empties it before each case. */
export const TAPS: unknown[] = [];

/** The State of each run that a `run_again` step started, in order. */
export const INNER_STATES: Array<{ executed: string[]; skipped: string[]; errors: Array<[string, unknown]> }> = [];
