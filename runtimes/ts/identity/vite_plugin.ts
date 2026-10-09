/**
 * Vite / vitest adapter for the step-identity build step (stamp.ts).
 *
 *     // vitest.config.ts
 *     import { cupIdentity } from "./identity/vite_plugin";
 *     export default defineConfig({ plugins: [cupIdentity()] });
 */

import { shouldStamp, stampSource } from "./stamp.js";

export function cupIdentity() {
  return {
    name: "cup-identity",
    enforce: "pre" as const,
    transform(code: string, id: string) {
      const file = id.split("?", 1)[0] ?? id;
      if (!shouldStamp(file)) return null;
      const stamped = stampSource(code, file);
      return stamped === code ? null : { code: stamped, map: null };
    },
  };
}
