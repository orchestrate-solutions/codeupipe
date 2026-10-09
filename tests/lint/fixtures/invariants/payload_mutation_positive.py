"""Every flagged line carries an ``expect:`` comment with its rule id."""


class WritesInternals:
    def call(self, payload):
        payload._data["a"] = 1  # expect: CUP-I001
        payload._data.update({"b": 2})  # expect: CUP-I001
        del payload._data["c"]  # expect: CUP-I001
        return payload


class WritesInternalsOfADerivedPayload:
    def call(self, payload):
        later = payload.insert("a", 1)
        later._data["b"] = 2  # expect: CUP-I001
        return later


class MutatesWhatGetReturned:
    def call(self, payload):
        payload.get("items").append(1)  # expect: CUP-I002
        payload.get("config")["debug"] = True  # expect: CUP-I002
        del payload.get("config")["secret"]  # expect: CUP-I002
        return payload


class MutatesThroughALocalName:
    def call(self, payload):
        items = payload.get("items", [])
        items.append(1)  # expect: CUP-I002
        items[0] = "first"  # expect: CUP-I002
        items.sort()  # expect: CUP-I002
        return payload.insert("items", items)


class MutatesNestedData:
    def call(self, payload):
        config = payload.get("config")
        config["limits"]["max"] = 10  # expect: CUP-I002
        config["tags"].append("x")  # expect: CUP-I002
        return payload


class MutatesAFallback:
    def call(self, payload):
        items = payload.get("items") or []
        items.append(1)  # expect: CUP-I002
        return payload.insert("items", items)


class MutatesEachElement:
    def call(self, payload):
        for row in payload.get("rows", []):
            row["seen"] = True  # expect: CUP-I002
        return payload


class MutatesFromALaterPayload:
    def call(self, payload):
        later = payload.insert("a", 1)
        later.get("items").append(2)  # expect: CUP-I002
        return later


class TapMutates:
    def observe(self, payload):
        payload.get("log").append("seen")  # expect: CUP-I002


class PredicateMutates:
    def test(self, payload):
        payload.get("checks").append("ran")  # expect: CUP-I002
        return True


class AsyncFilterMutates:
    async def call(self, payload):
        payload.get("items").append(1)  # expect: CUP-I002
        return payload


class NamesThePayloadDifferently:
    def call(self, p):
        p.get("items").append(1)  # expect: CUP-I002
        return p
