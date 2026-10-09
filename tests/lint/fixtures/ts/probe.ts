// Step-identity probe cases, with describe(label, f) replaced by
// p.addFilter(f): the probe's cases as lint fixtures.
import { Pipeline } from "@codeupipe/core";
import { Validate, normalize } from "./filters";

const lambda = (p: any) => p;
function makeClosure(k: string) { return function inner(p: any) { return { ...p, k }; }; }
function makeLocalClass() { class Local { call(p: any) { return p; } } return new Local(); }

const p = new Pipeline();
p.addFilter(new Validate());
p.addFilter(new Validate());
p.addFilter(normalize);
p.addFilter(lambda); // expect: CUP-A001
p.addFilter((p: any) => p); // expect: CUP-A001
p.addFilter(makeClosure("x")); // expect: CUP-A001
p.addFilter(makeLocalClass()); // expect: CUP-A003
