/**
 * Step identity (conformance/API.md): a pointer to the filter, stamped by
 * the build step (identity/stamp.ts) and read by the runtime.
 *
 * vitest runs these files through identity/vite_plugin.ts, so the classes
 * and functions declared at the top of this file carry stamps.
 */
import { describe, it, expect } from "vitest";
import { AnonymousStep, Payload, Pipeline, Valve } from "../src/index.js";
import type { Filter, Hook, Predicate } from "../src/index.js";
import ts from "typescript";
import { labelFor, stampSource, topLevelDeclarations } from "../identity/stamp.js";

const HERE = "@codeupipe/core/tests/step_identity.test";

class Add implements Filter {
  call(p: Payload): Payload {
    return p.insert("n", ((p.get("n", 0) as number) ?? 0) + 1);
  }
}

class Boom implements Filter {
  call(): Payload {
    throw new Error("boom");
  }
}

class Audit {
  observe(): void {}
}

class UserOnboarding extends Pipeline {
  constructor() {
    super();
    this.addFilter(new Add());
  }
}

/** A predicate object: test(payload), identified by its class. */
class IsOn implements Predicate {
  test(p: Payload): boolean {
    return Boolean(p.get("on"));
  }
}

/** A configurable predicate: its setting lives on the instance. */
class AtLeast implements Predicate {
  constructor(private readonly n: number) {}
  test(p: Payload): boolean {
    return ((p.get("n", 0) as number) ?? 0) >= this.n;
  }
}

function isOn(p: Payload): boolean {
  return Boolean(p.get("on"));
}

class Record implements Hook {
  events: [string, string | null][] = [];
  before(step: string | null): void {
    this.events.push(["before", step]);
  }
  after(step: string | null): void {
    this.events.push(["after", step]);
  }
  onError(step: string | null): void {
    this.events.push(["error", step]);
  }
}

describe("identity is the filter's stamped declaration", () => {
  it("reports the package, path and class", () => {
    const p = new Pipeline().addFilter(new Add());
    p.run(new Payload({}));
    expect(p.state.executed).toEqual([`${HERE}#Add`]);
  });

  it("numbers reuse from the second occurrence", () => {
    const p = new Pipeline().addFilter(new Add()).addFilter(new Add()).addFilter(new Add());
    expect(p.identities).toEqual([`${HERE}#Add`, `${HERE}#Add#2`, `${HERE}#Add#3`]);
  });

  it("identifies taps the same way", () => {
    const p = new Pipeline().addFilter(new Add()).addTap(new Audit());
    p.run(new Payload({}));
    expect(p.state.executed).toEqual([`${HERE}#Add`, `${HERE}#Audit`]);
  });

  it("gives hooks the identity", () => {
    const hook = new Record();
    const p = new Pipeline().addFilter(new Add()).addFilter(new Boom()).useHook(hook);
    expect(() => p.run(new Payload({}))).toThrow("boom");
    expect(hook.events).toEqual([
      ["before", null], ["before", `${HERE}#Add`], ["after", `${HERE}#Add`],
      ["before", `${HERE}#Boom`], ["error", `${HERE}#Boom`], ["error", null],
    ]);
  });

  it("identifies a Valve by its inner filter", () => {
    const p = new Pipeline().addFilter(new Valve(new Add(), new IsOn()));
    p.run(new Payload({}));
    expect(p.state.skipped).toEqual([`${HERE}#Add`]);
  });

  it("nests a named Pipeline subclass as one step", () => {
    const outer = new Pipeline().addFilter(new Add()).addPipeline(new UserOnboarding());
    expect(outer.run(new Payload({})).get("n")).toBe(2);
    expect(outer.state.executed).toEqual([`${HERE}#Add`, `${HERE}#UserOnboarding`]);
  });

  it("records where each step was added", () => {
    const p = new Pipeline().addFilter(new Add());
    expect(p.stepSites[`${HERE}#Add`]).toMatch(/step_identity\.test\.ts:\d+$/);
  });
});

function makeLocalClass(): Filter {
  class Local implements Filter {
    call(p: Payload): Payload {
      return p;
    }
  }
  return new Local();
}

function makeLocalSubclass(): Filter {
  class Sneaky extends Add {}
  return new Sneaky();
}

describe("predicates are objects", () => {
  it("identifies the predicate by its class", () => {
    expect(new Valve(new Add(), new IsOn()).predicateSymbol).toBe(`${HERE}#IsOn`);
  });

  it("carries configuration on the instance", () => {
    const p = new Pipeline().addFilter(new Valve(new Add(), new AtLeast(5)));
    expect(p.run(new Payload({ n: 5 })).get("n")).toBe(6);
    expect(p.run(new Payload({ n: 1 })).get("n")).toBe(1);
  });
});

describe("anonymous steps are refused", () => {
  it("refuses an object literal", () => {
    expect(() => new Pipeline().addFilter({ call: (p: Payload) => p } as Filter)).toThrow(AnonymousStep); // cup: allow-anonymous (exercises the refusal)
  });

  it("refuses a class defined inside a function", () => {
    expect(() => new Pipeline().addFilter(makeLocalClass())).toThrow(/Local has no step identity/); // cup: allow-anonymous (exercises the refusal)
  });

  it("refuses a local subclass instead of lending it the parent's identity", () => {
    expect(() => new Pipeline().addFilter(makeLocalSubclass())).toThrow(AnonymousStep); // cup: allow-anonymous (exercises the refusal)
  });

  it("refuses an arrow predicate", () => {
    // @ts-expect-error a function is not a Predicate
    expect(() => new Valve(new Add(), (p: Payload) => Boolean(p.get("on")))).toThrow(/predicate object/); // cup: allow-anonymous (exercises the refusal)
  });

  it("refuses a named function as a predicate", () => {
    // @ts-expect-error a function is not a Predicate
    expect(() => new Valve(new Add(), isOn)).toThrow(/predicate object/); // cup: allow-anonymous (exercises the refusal)
  });

  it("refuses an object-literal predicate", () => {
    expect(() => new Valve(new Add(), { test: () => true })).toThrow(AnonymousStep); // cup: allow-anonymous (exercises the refusal)
  });

  it("refuses a plain Pipeline as a nested step", () => {
    expect(() => new Pipeline().addPipeline(new Pipeline().addFilter(new Add()))).toThrow( // cup: allow-anonymous (exercises the refusal)
      /named Pipeline subclass/,
    );
  });

  it("names the fix", () => {
    expect(() => new Pipeline().addFilter(makeLocalClass())).toThrow(/top-level class/); // cup: allow-anonymous (exercises the refusal)
  });
});

describe("names are gone", () => {
  it("rejects a name argument at the type level and at runtime", () => {
    // @ts-expect-error addFilter takes no name
    expect(() => new Pipeline().addFilter(new Add(), "add")).toThrow(TypeError);
  });
});

describe("the build step", () => {
  const code = [
    "export class A {}",
    "class B {}",
    "export function f() {}",
    "export const g = () => 1;",
    "function outer() { class Inner {} return Inner; }",
    "declare class Ambient {}",
    "export default class {}",
  ].join("\n");

  it("stamps top-level class and function declarations only", () => {
    expect(topLevelDeclarations(code, "x.ts")).toEqual(["A", "B", "f", "outer"]);
  });

  it("stamps each declaration without moving any line", () => {
    const out = stampSource(code, "x.ts", "pkg/src/x");
    expect(out.split("\n").length).toBe(code.split("\n").length);
    expect(out).toContain('Object.defineProperty(A, Symbol.for("cup.identity"), { value: "pkg/src/x#A" });');
    expect(out).not.toContain("#g");
    expect(out).not.toContain("#Inner");
  });

  it("stamps a class before module-level code uses it", () => {
    const src = 'class A {}\nexport const seen = (A as any)[Symbol.for("cup.identity")];\n';
    const js = ts.transpileModule(stampSource(src, "m.ts", "pkg/m"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS },
    }).outputText;
    const mod: { exports: { seen?: string } } = { exports: {} };
    new Function("module", "exports", js)(mod, mod.exports);
    expect(mod.exports.seen).toBe("pkg/m#A");
  });

  it("stamps a function before module-level code uses it (functions are hoisted)", () => {
    const src = 'export const seen = (f as any)[Symbol.for("cup.identity")];\nfunction f() {}\n';
    const js = ts.transpileModule(stampSource(src, "m.ts", "pkg/m"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS },
    }).outputText;
    const mod: { exports: { seen?: string } } = { exports: {} };
    new Function("module", "exports", js)(mod, mod.exports);
    expect(mod.exports.seen).toBe("pkg/m#f");
  });

  it("labels by package name and path without extension", () => {
    expect(labelFor(`${__dirname}/../src/valve.ts`)).toBe("@codeupipe/core/src/valve");
  });

  it("stamps survive minification (they are string literals)", () => {
    const out = stampSource("class LongDescriptiveName {}", "m.js", "pkg/m");
    expect(out).toContain('"pkg/m#LongDescriptiveName"');
  });
});

describe("the build step for tsc output", () => {
  it("gives compiled code the same identities as the source", async () => {
    const { execFileSync } = await import("node:child_process");
    const fs = await import("node:fs");
    const os = await import("node:os");
    const path = await import("node:path");
    const out = fs.mkdtempSync(path.join(os.tmpdir(), "cup_tsc_"));
    const root = path.resolve(__dirname, "..");
    execFileSync(path.join(root, "node_modules/.bin/tsc"), ["-p", root, "--outDir", out], { stdio: "pipe" });
    const { stampDist } = await import("../identity/stamp_dist.js");
    expect(stampDist(out)).toBeGreaterThan(0);
    // plain Node, no build tooling: only the stamps written into dist/
    const script = `import("${path.join(out, "valve.js")}").then(m => ` +
      `console.log(m.Valve[Symbol.for("cup.identity")]))`;
    const identity = execFileSync("node", ["-e", script], { encoding: "utf8" }).trim();
    expect(identity).toBe("@codeupipe/core/src/valve#Valve");
  }, 60_000);
});
