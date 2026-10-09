/**
 * Bun adapter for the step-identity build step (stamp.ts).
 *
 *     bun run --preload ./runtimes/ts/identity/bun_preload.ts app.ts
 *
 * or list it under `preload` in bunfig.toml.
 *
 * The plugin stamps, then transpiles with Bun's own transpiler and hands Bun
 * JavaScript: Bun 1.2.21 parses a runtime plugin's `loader: "ts"` result as
 * JavaScript (`import type` fails), and "tsx" would misread `<T>x` casts.
 */

import { plugin } from "bun";
import { shouldStamp, stampSource } from "./stamp.ts";

const transpilers = {
  ts: new Bun.Transpiler({ loader: "ts" }),
  tsx: new Bun.Transpiler({ loader: "tsx" }),
};

plugin({
  name: "cup-identity",
  setup(build) {
    build.onLoad({ filter: /\.[cm]?[jt]sx?$/ }, async (args) => {
      const code = await Bun.file(args.path).text();
      const stamped = shouldStamp(args.path) ? stampSource(code, args.path) : code;
      const ext = (args.path.match(/\.([cm]?[jt]sx?)$/)?.[1] ?? "js").replace(/^[cm]/, "");
      if (ext === "ts" || ext === "tsx") {
        return { contents: transpilers[ext].transformSync(stamped), loader: "js" };
      }
      return { contents: stamped, loader: ext === "jsx" ? "jsx" : "js" };
    });
  },
});
