"""NameComponentsFilter: the type name and the paths of each component, as in phase 1."""

from codeupipe import Payload

from .plan_files_filter import PlanFilesFilter
from .refusal import Refusal
from .type_name_filter import TypeNameFilter


class NameComponentsFilter:
    """Filter (sync).

    Input keys: ``components``, ``directory``.
    Output keys: ``components``, each with ``type_name``, ``snake``,
    ``component_path``, ``test_path`` and ``module`` added. It uses the
    Filters of phase 1, so the names are the same. A name that phase 1
    refuses, or two components with the same type name, are refused with exit
    code 2.
    """

    def call(self, payload: Payload) -> Payload:
        named, seen = [], {}
        for component in payload.get("components"):
            one = Payload({"kind": component["kind"], "name": component["name"],
                           "directory": payload.get("directory")})
            one = PlanFilesFilter().call(TypeNameFilter().call(one))
            type_name = one.get("type_name")
            if type_name in seen:
                raise Refusal(2, "Two components are %s: %s and %s." % (type_name, seen[type_name], component["name"]))
            seen[type_name] = component["name"]
            named.append(dict(component, **{key: one.get(key) for key in
                                            ("type_name", "snake", "component_path", "test_path", "module")}))
        return payload.insert("components", named)
