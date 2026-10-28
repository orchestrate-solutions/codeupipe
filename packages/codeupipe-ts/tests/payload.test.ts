import assert from "node:assert/strict";
import { test } from "node:test";

import { Payload } from "../src/index.ts";

test("the map that the caller gives is copied", () => {
  const data = { a: 1 };
  const payload = new Payload(data);
  payload.insert("b", 2);
  assert.deepEqual(data, { a: 1 });
  assert.deepEqual(payload.toDict(), { a: 1, b: 2 });
});

test("an empty Payload has no keys", () => {
  assert.deepEqual(new Payload().toDict(), {});
});

test("get gives the value, the fallback, or null", () => {
  const payload = new Payload({ a: 1, n: null });
  assert.equal(payload.get("a"), 1);
  assert.equal(payload.get("missing"), null);
  assert.equal(payload.get("missing", 7), 7);
  assert.equal(payload.get("n", 7), null);
});

test("has is true for a key with a null value", () => {
  const payload = new Payload({ n: null });
  assert.equal(payload.has("n"), true);
  assert.equal(payload.has("missing"), false);
});

test("insert, remove, merge and withTrace change the Payload and return it", () => {
  const payload = new Payload({ a: 1 });
  assert.equal(payload.insert("b", 2), payload);
  assert.equal(payload.remove("a"), payload);
  assert.equal(payload.merge(new Payload({ c: 3 })), payload);
  assert.equal(payload.withTrace("t-1"), payload);
  assert.deepEqual(payload.toDict(), { b: 2, c: 3 });
  assert.equal(payload.traceId, "t-1");
});

test("remove of a key that is not there does nothing", () => {
  assert.deepEqual(new Payload({ a: 1 }).remove("zz").toDict(), { a: 1 });
});

test("in a merge the other Payload wins", () => {
  const payload = new Payload({ a: 1, b: 1 }).merge(new Payload({ b: 2 }));
  assert.deepEqual(payload.toDict(), { a: 1, b: 2 });
});

test("a merge keeps the trace id it has, and takes one when it has none", () => {
  const other = new Payload({}).withTrace("other");
  assert.equal(new Payload({}).withTrace("mine").merge(other).traceId, "mine");
  assert.equal(new Payload({}).merge(other).traceId, "other");
});

test("copy gives a separate Payload with the same contents", () => {
  const payload = new Payload({ a: 1 }).withTrace("t-1");
  const copy = payload.copy();
  copy.insert("a", 2);
  assert.equal(payload.get("a"), 1);
  assert.equal(copy.traceId, "t-1");
});

test("copy is shallow: the two Payloads share their values", () => {
  const list = [1];
  const payload = new Payload({ list });
  assert.equal(payload.copy().get("list"), list);
});

test("toDict gives a new map each time", () => {
  const payload = new Payload({ a: 1 });
  const out = payload.toDict();
  out.a = 2;
  assert.equal(payload.get("a"), 1);
});

test("the trace id is null until it is set, and the lineage starts empty", () => {
  const payload = new Payload({});
  assert.equal(payload.traceId, null);
  assert.deepEqual(payload.lineage, []);
});

test("a key with the name of an Object property is only a key", () => {
  const payload = new Payload({});
  assert.equal(payload.has("constructor"), false);
  assert.equal(payload.get("toString"), null);
  payload.insert("__proto__", 1);
  assert.equal(payload.get("__proto__"), 1);
  assert.deepEqual(Object.keys(payload.toDict()), ["__proto__"]);
});
