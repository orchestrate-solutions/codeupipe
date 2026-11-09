// RenderLayoutFilter: the text of the two files of each component of the layout.
import { Payload } from "codeupipe";
import type { Filter } from "codeupipe";

import { RenderFilesFilter } from "./render-files-filter.ts";
import type { Resolved } from "./resolve-steps-filter.ts";

/** A component, with the text of its two files. */
export type Rendered = Resolved & { component_text: string; test_text: string };

/**
 * Filter (sync).
 *
 * Input keys: `components` (each as ResolveStepsFilter gives it).
 * Output keys: `components`, each with `component_text` and `test_text`. It
 * uses the RenderFilesFilter of phase 1, which writes the steps of a pipeline
 * when it has `calls`.
 */
export class RenderLayoutFilter implements Filter {
  call(payload: Payload): Payload {
    const rendered = payload.get<Resolved[]>("components", []).map((component): Rendered => {
      const out = new RenderFilesFilter().call(new Payload({ ...component }));
      return { ...component, component_text: out.get<string>("component_text", ""), test_text: out.get<string>("test_text", "") };
    });
    return payload.insert("components", rendered);
  }
}
