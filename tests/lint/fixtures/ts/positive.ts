// Anonymous steps the TypeScript analyzer must flag (expect: comments name the rule).
import { Pipeline, Valve, type Payload } from "@codeupipe/core";
import * as cup from "@codeupipe/core";

class Add {
  call(p: Payload) { return p; }
}

function isOn(p: Payload): boolean { return true; }

const arrowPred = (p: Payload) => true;
const objectStep = { call: (p: Payload) => p };

function makeClosure(k: string) { return function inner(p: Payload) { return p; }; }
function makeLocalClass() { class Local { call(p: Payload) { return p; } } return new Local(); }
const makeArrow = () => (p: Payload) => true;

export function build(): Pipeline {
  class LocalFilter { call(p: Payload) { return p; } }
  function nested(p: Payload) { return true; }

  const p = new Pipeline();
  p.addFilter((payload: Payload) => payload); // expect: CUP-A001
  p.addFilter(function (payload: Payload) { return payload; }); // expect: CUP-A001
  p.addTap({ observe(payload: Payload) {} }); // expect: CUP-A004
  p.addFilter(new (class { call(p: Payload) { return p; } })()); // expect: CUP-A004
  p.addFilter(new LocalFilter()); // expect: CUP-A003
  p.addFilter(new Valve(new Add(), (x: Payload) => true)); // expect: CUP-A001
  p.addFilter(new cup.Valve(new LocalFilter(), isOn)); // expect: CUP-A003 CUP-A008
  p.addFilter(new Valve(new Add(), nested)); // expect: CUP-A002
  p.addFilter(new Valve(new Add(), arrowPred)); // expect: CUP-A001
  p.addFilter(objectStep); // expect: CUP-A004
  p.addParallel([new Add(), (x: Payload) => x]); // expect: CUP-A001
  p.addFilter(makeClosure("x")); // expect: CUP-A001
  p.addFilter(makeLocalClass()); // expect: CUP-A003
  p.addFilter(new Valve(new Add(), makeArrow())); // expect: CUP-A001

  const inner = new Pipeline().addFilter(new Add());
  p.addPipeline(inner); // expect: CUP-A005
  p.addPipeline(new Pipeline()); // expect: CUP-A005
  p.addPipeline(new cup.Pipeline()); // expect: CUP-A005

  const local = new LocalFilter();
  new Pipeline()
    .addFilter(new Add())
    .addFilter(local); // expect: CUP-A003
  return p;
}

export class Builder {
  build() {
    class Inner { call(p: Payload) { return p; } }
    return new Pipeline().addFilter(new Inner()); // expect: CUP-A003
  }
}

// Valve predicates are objects: a named function (isOn, above) is not one.
export function functionPredicate() {
  return new Valve(new Add(), isOn); // expect: CUP-A008
}
