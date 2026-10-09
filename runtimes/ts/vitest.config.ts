import { defineConfig } from "vitest/config";
import { cupIdentity } from "./identity/vite_plugin";

export default defineConfig({
  // Step identity build step (conformance/API.md): stamps every top-level
  // class and function declaration with its identity.
  plugins: [cupIdentity()],
  test: {
    include: ["tests/**/*.test.ts"],
  },
});
