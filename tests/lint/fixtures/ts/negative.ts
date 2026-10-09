// Named steps the TypeScript analyzer must NOT flag.
import { Pipeline, Valve, type Payload } from "@codeupipe/core";
import { Imported, importedPred } from "./elsewhere";

class Add {
  call(p: Payload) { return p; }
}

class Audit {
  observe(p: Payload) {}
}

class UserOnboarding extends Pipeline {
  constructor() {
    super();
    this.addFilter(new Add());
  }
}

class IsOn { test(p: Payload): boolean { return true; } } // a predicate object
function makeAdd() { return new Add(); }

export function build(steps: Add[], pred: (p: Payload) => boolean): Pipeline {
  const p = new Pipeline(); // a plain pipeline at the top level is fine
  p.addFilter(new Add());
  p.addTap(new Audit());
  p.addFilter(new Valve(new Add(), new IsOn()));
  p.addFilter(new Valve(new Imported(), importedPred));
  p.addFilter(new Valve(new Add(), pred));
  p.addPipeline(new UserOnboarding());
  p.addParallel([new Add(), new Add()]);
  p.addFilter(makeAdd());
  for (const s of steps) p.addFilter(s);
  let reassigned: any = (x: Payload) => x;
  reassigned = new Add();
  p.addFilter(reassigned); // let: not provably anonymous
  [1, 2].map((x) => x * 2); // an arrow that is not a step
  return p;
}

// The typed variant still takes hand-written step names: out of scope.
import { TypedPipeline } from "@codeupipe/core/typed";
export function typed() {
  class Peek { observe(ctx: unknown) {} }
  const pipe = new TypedPipeline<{ n: number }>().addTap(new Peek(), "peek");
  pipe.addTap(new Peek(), "again");
  return pipe;
}
