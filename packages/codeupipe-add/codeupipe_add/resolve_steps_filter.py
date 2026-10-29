"""ResolveStepsFilter: the calls and the imports of each pipeline of the layout."""

from codeupipe import Payload

from .refusal import Refusal

CALLS = {"filter": "add_filter", "tap": "add_tap", "pipeline": "add_pipeline"}


class ResolveStepsFilter:
    """Filter (sync).

    Input keys: ``components``, each with ``kind``, ``name``, ``type_name``,
    ``module``, ``steps`` and ``hooks``.
    Output keys: ``components``, each with ``calls`` (a list of
    ``(method, [type names])``, steps first, then hooks) and ``imports`` (a
    sorted list of ``(module, type name)``). A name that is not a component,
    a step of the wrong kind, or a pipeline that has itself as a step is
    refused with exit code 2.
    """

    def call(self, payload: Payload) -> Payload:
        components = payload.get("components")
        found = {}
        for component in components:
            found[component["name"]] = found[component["type_name"]] = component
        resolved = [self._resolve(component, found) for component in components]
        by_type = {component["type_name"]: component for component in resolved}
        for component in resolved:
            self._refuse_a_loop(component, by_type, [])
        return payload.insert("components", resolved)

    def _resolve(self, component, found):
        calls = []
        for step in component["steps"]:
            if isinstance(step, dict):
                pair = [self._find(name, found, component) for name in step["valve"]]
                for used, wanted in zip(pair, ("predicate", "filter")):
                    if used["kind"] != wanted:
                        raise Refusal(2, "valve: [%s] in %s: a valve is [Predicate, Filter], and %s is a %s, not a %s."
                                      % (", ".join(step["valve"]), component["name"], used["name"], used["kind"],
                                         wanted))
                calls.append(("add_valve", pair))
                continue
            step = self._find(step, found, component)
            if step["kind"] == "predicate":
                raise Refusal(2, "%s is a predicate. A predicate is not a step: put it in a valve: [%s, Filter]."
                              % (step["name"], step["name"]))
            if step["kind"] == "hook":
                raise Refusal(2, "%s is a hook. A hook is not a step: put it in hooks: of %s."
                              % (step["name"], component["name"]))
            calls.append((CALLS[step["kind"]], [step]))
        for name in component["hooks"]:
            hook = self._find(name, found, component)
            if hook["kind"] != "hook":
                raise Refusal(2, "%s in the hooks of %s is a %s, not a hook." % (name, component["name"], hook["kind"]))
            calls.append(("use_hook", [hook]))
        imports = sorted({(used["module"], used["type_name"]) for _, used_list in calls for used in used_list})
        return dict(component, calls=[(method, [used["type_name"] for used in used_list])
                                      for method, used_list in calls], imports=imports)

    def _find(self, name, found, component):
        if name not in found:
            raise Refusal(2, "%s, a step of %s, is not a component of the layout." % (name, component["name"]))
        return found[name]

    def _refuse_a_loop(self, component, by_type, path):
        if component["type_name"] in path:
            loop = path[path.index(component["type_name"]):] + [component["type_name"]]
            raise Refusal(2, "A pipeline has itself as a step: %s." % " -> ".join(loop))
        for method, names in component["calls"]:
            if method == "add_pipeline":
                self._refuse_a_loop(by_type[names[0]], by_type, path + [component["type_name"]])
