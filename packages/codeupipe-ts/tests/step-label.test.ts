import assert from "node:assert/strict";
import { test } from "node:test";

import * as codeupipe from "../src/index.ts";
import { Payload, Pipeline } from "../src/index.ts";

class AddFilter {
  call(payload: Payload): Payload {
    return payload.insert("n", payload.get("n", 0) + 1);
  }
}

class SeeTap {
  observe(): void {}
}

class IsOnPredicate {
  test(payload: Payload): boolean {
    return payload.get("on") === true;
  }
}

class InnerPipeline extends Pipeline {}

test("the label is the name of the class", () => {
  const pipeline = new Pipeline();
  pipeline.addFilter(new AddFilter());
  pipeline.addTap(new SeeTap());
  assert.deepEqual(pipeline.labels, ["AddFilter", "SeeTap"]);
});

test("the second use of a class gets a number", () => {
  const pipeline = new Pipeline();
  pipeline.addFilter(new AddFilter());
  pipeline.addFilter(new AddFilter());
  pipeline.addFilter(new AddFilter());
  assert.deepEqual(pipeline.labels, ["AddFilter", "AddFilter#2", "AddFilter#3"]);
});

test("a Valve has the label of its Filter", () => {
  const pipeline = new Pipeline();
  pipeline.addFilter(new AddFilter());
  pipeline.addValve(new IsOnPredicate(), new AddFilter());
  assert.deepEqual(pipeline.labels, ["AddFilter", "AddFilter#2"]);
});

test("a nested pipeline has the label of its class", () => {
  const pipeline = new Pipeline();
  pipeline.addPipeline(new InnerPipeline());
  pipeline.addPipeline(new Pipeline());
  assert.deepEqual(pipeline.labels, ["InnerPipeline", "Pipeline"]);
});

test("a class defined in a function works", () => {
  function make() {
    class LocalFilter {
      call(payload: Payload): Payload {
        return payload;
      }
    }
    return new LocalFilter();
  }
  const pipeline = new Pipeline();
  pipeline.addFilter(make());
  assert.deepEqual(pipeline.labels, ["LocalFilter"]);
});

test("a step from a class with no name has the label 'anonymous'", () => {
  const pipeline = new Pipeline();
  pipeline.addFilter(new (class {
    call(payload: Payload): Payload {
      return payload;
    }
  })());
  assert.deepEqual(pipeline.labels, ["anonymous"]);
});

test("labels gives a new list each time", () => {
  const pipeline = new Pipeline();
  pipeline.addFilter(new AddFilter());
  pipeline.labels.push("x");
  assert.deepEqual(pipeline.labels, ["AddFilter"]);
});

const untyped = (value: unknown) => value as never;

test("a step without the method of its role is refused when it is added", () => {
  const pipeline = new Pipeline();
  assert.throws(() => pipeline.addFilter(untyped((p: Payload) => p)), { name: "TypeError", message: /A Filter has call\(payload\)/ });
  assert.throws(() => pipeline.addFilter(untyped(new SeeTap())), { name: "TypeError", message: /call\(payload\)/ });
  assert.throws(() => pipeline.addTap(untyped(new AddFilter())), { name: "TypeError", message: /A Tap has observe\(payload\)/ });
  assert.throws(() => pipeline.addValve(untyped(() => true), new AddFilter()), { name: "TypeError", message: /A Predicate has test\(payload\)/ });
  assert.throws(() => pipeline.addValve(new IsOnPredicate(), untyped(null)), { name: "TypeError", message: /A Filter has call\(payload\)/ });
  assert.throws(() => pipeline.addPipeline(untyped(new AddFilter())), { name: "TypeError", message: /addPipeline takes a Pipeline/ });
  assert.deepEqual(pipeline.labels, []);
});

test("addValve says so when the arguments are in the wrong order", () => {
  const pipeline = new Pipeline();
  assert.throws(() => pipeline.addValve(untyped(new AddFilter()), untyped(new IsOnPredicate())),
    { name: "TypeError", message: /wrong order/ });
});

test("the package exports the primitives a user needs, and no Valve", () => {
  assert.deepEqual(Object.keys(codeupipe).sort(), ["Hook", "Payload", "Pipeline", "State"]);
});
