"""PythonStepVisitor: finds anonymous steps in one parsed Python module.

A step is an argument of ``add_filter``, ``add_async_filter``,
``insert_filter_after``, ``add_tap``, ``add_async_tap``, ``add_pipeline`` or
``add_parallel`` (on any receiver), or of ``Valve(inner, predicate)``. It is
anonymous when it is (or, through a simple local name, is bound to):

- a lambda (CUP-A001);
- a function defined inside a function (CUP-A002);
- a class defined inside a function, or an instance of one (CUP-A003);
- a plain ``Pipeline()`` (CUP-A005);
- as a Valve predicate, a named function (CUP-A008): predicates are
  objects with ``test(payload)``;
- the result of calling a function in this module that returns one of the
  above (a closure factory), reported with the same rule;
- a module-level class or function of a script, added from its
  ``if __name__ == "__main__":`` block or a function that block calls
  (CUP-A006). Only then: a module that is merely importable is fine.

Names are resolved lexically: innermost function scope outwards to the
module, stopping at the first scope that binds the name. A name bound more
than one way in a scope (``x = lambda ...`` then ``x = Add()``) is not
provably anonymous and is not flagged. Parameters, loop targets, imports and
anything else are opaque.
"""

import ast
from typing import Dict, List, Optional, Set, Tuple

from .finding import Finding
from .rules import (ENTRY_SCRIPT, FUNCTION_PREDICATE, LAMBDA, LOCAL_FUNCTION, LOCAL_TYPE, UNNAMED_PIPELINE,
                    make_finding)

_STEP_METHODS = {
    "add_filter": "Filter",
    "add_async_filter": "Filter",
    "insert_filter_after": "Filter",
    "add_tap": "Tap",
    "add_async_tap": "Tap",
    "add_pipeline": "Nested pipeline",
    "add_parallel": "Parallel filter",
}
_VALVE_ROLES = ["Valve inner filter", "Valve predicate"]
_VALVE_KEYWORDS = {"inner": "Valve inner filter", "predicate": "Valve predicate"}

# A binding: (kind, name, owner, node). Kinds: lambda, local_def, local_class,
# local_instance, plain_pipeline, module_def, module_class, other. ``name`` is
# the class of a local_instance; ``owner`` the function a local definition is in.
Binding = Tuple[str, str, Optional[str], object]
_OTHER: Binding = ("other", "", None, None)
_FUNCS = (ast.FunctionDef, ast.AsyncFunctionDef)


def _is_plain_pipeline_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call) or node.args or node.keywords:
        return False
    func = node.func
    return (isinstance(func, ast.Name) and func.id == "Pipeline") or (
        isinstance(func, ast.Attribute) and func.attr == "Pipeline")


def _is_main_guard(node: ast.AST) -> bool:
    if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
        return False
    test = node.test
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    sides = [test.left, test.comparators[0]]
    names = [s for s in sides if isinstance(s, ast.Name) and s.id == "__name__"]
    consts = [s for s in sides if isinstance(s, ast.Constant) and s.value == "__main__"]
    return bool(names) and bool(consts)


def _own_nodes(body: List[ast.stmt]):
    """Every node in ``body``, not descending into nested functions, classes or lambdas."""
    stack = list(reversed(body))
    while stack:
        node = stack.pop()
        yield node
        for child in reversed(list(ast.iter_child_nodes(node))):
            if isinstance(child, _FUNCS + (ast.ClassDef, ast.Lambda)):
                yield child  # the definition itself binds a name; its body is its own scope
                continue
            stack.append(child)


def _target_names(target: ast.AST):
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            for name in _target_names(element):
                yield name
    elif isinstance(target, ast.Starred):
        for name in _target_names(target.value):
            yield name


class PythonStepVisitor:
    """Collects Findings for one module (see the module docstring)."""

    def __init__(self, path: str, tree: ast.Module):
        self._path = path
        self._tree = tree
        self._chains: Dict[int, List[Dict[str, Binding]]] = {}  # id(function node) -> scope chain
        self._findings: List[Finding] = []
        self._seen: Set[Tuple[int, int, str]] = set()
        self._module_scope = self._scope(tree.body, None, is_module=True)
        self._main_functions: Set[str] = set()
        self._main_block: Optional[ast.If] = None
        for stmt in tree.body:
            if _is_main_guard(stmt):
                self._main_block = stmt
        if self._main_block is not None:
            self._main_functions = self._reached_from_main()

    # -- scopes ---------------------------------------------------------

    def _scope(self, body: List[ast.stmt], owner: Optional[str], is_module: bool,
               args: Optional[ast.arguments] = None) -> Dict[str, Binding]:
        seen: Dict[str, List[Binding]] = {}

        def bind(name: str, binding: Binding) -> None:
            seen.setdefault(name, []).append(binding)

        if args is not None:
            for arg in args.posonlyargs + args.args + args.kwonlyargs:
                bind(arg.arg, _OTHER)
            for arg in (args.vararg, args.kwarg):
                if arg is not None:
                    bind(arg.arg, _OTHER)
        nodes = list(_own_nodes(body))
        local_classes = set()
        for node in nodes:
            if isinstance(node, _FUNCS):
                bind(node.name, ("module_def" if is_module else "local_def", node.name, owner, node))
            elif isinstance(node, ast.ClassDef):
                bind(node.name, ("module_class" if is_module else "local_class", node.name, owner, node))
                if not is_module:
                    local_classes.add(node.name)
        for node in nodes:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                binding = self._value_binding(node.value, local_classes, owner)
                for target in targets:
                    names = list(_target_names(target))
                    for name in names:
                        bind(name, binding if isinstance(target, ast.Name) else _OTHER)
            elif isinstance(node, (ast.AugAssign, ast.For, ast.AsyncFor, ast.comprehension, ast.NamedExpr)):
                for name in _target_names(node.target):
                    bind(name, _OTHER)
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    if item.optional_vars is not None:
                        for name in _target_names(item.optional_vars):
                            bind(name, _OTHER)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    bind((alias.asname or alias.name).split(".")[0], _OTHER)
            elif isinstance(node, ast.ExceptHandler) and node.name:
                bind(node.name, _OTHER)
            elif isinstance(node, (ast.Global, ast.Nonlocal)):
                for name in node.names:
                    bind(name, _OTHER)
        scope = {}
        for name, bindings in seen.items():
            first = bindings[0]
            same = all(b[0] == first[0] and b[1] == first[1] for b in bindings)
            scope[name] = first if same else _OTHER
        return scope

    @staticmethod
    def _value_binding(value: Optional[ast.AST], local_classes: Set[str], owner: Optional[str]) -> Binding:
        if isinstance(value, ast.Lambda):
            return ("lambda", "", owner, value)
        if _is_plain_pipeline_call(value):
            return ("plain_pipeline", "", owner, value)
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id in local_classes:
            return ("local_instance", value.func.id, owner, value)
        return _OTHER

    def _chain_for(self, node: ast.AST, parent_chain: List[Dict[str, Binding]]) -> List[Dict[str, Binding]]:
        chain = self._chains.get(id(node))
        if chain is None:
            scope = self._scope(node.body, node.name, is_module=False, args=node.args)
            chain = [scope] + parent_chain
            self._chains[id(node)] = chain
        return chain

    @staticmethod
    def _resolve(name: str, chain: List[Dict[str, Binding]]) -> Binding:
        for scope in chain:
            if name in scope:
                return scope[name]
        return _OTHER

    # -- __main__ -------------------------------------------------------

    def _reached_from_main(self) -> Set[str]:
        defs = {s.name: s for s in self._tree.body if isinstance(s, _FUNCS)}
        reached: Set[str] = set()
        frontier = [self._main_block]
        while frontier:
            node = frontier.pop()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                    name = sub.func.id
                    if name in defs and name not in reached:
                        reached.add(name)
                        frontier.append(defs[name])
        return reached

    # -- classification -------------------------------------------------

    def _classify(self, expr: ast.AST, chain: List[Dict[str, Binding]], in_main: bool,
                  visiting: Set[int]) -> Optional[Tuple[str, str]]:
        """(rule, what) when ``expr`` is an anonymous step, else None. ``what`` starts with a verb."""
        got = self._describe(expr, chain, in_main, visiting)
        if got is None:
            return None
        rule, subject, noun = got
        return rule, ("`%s` is %s" % (subject, noun)) if subject else ("is " + noun)

    def _describe(self, expr: ast.AST, chain: List[Dict[str, Binding]], in_main: bool,
                  visiting: Set[int]) -> Optional[Tuple[str, Optional[str], str]]:
        """(rule, subject name or None, noun phrase)."""
        if isinstance(expr, ast.Lambda):
            return LAMBDA, None, "a lambda"
        if isinstance(expr, ast.Name):
            got = self._describe_binding(self._resolve(expr.id, chain), in_main)
            return None if got is None else (got[0], expr.id, got[1])
        if _is_plain_pipeline_call(expr):
            return UNNAMED_PIPELINE, None, "a plain Pipeline()"
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name):
            name = expr.func.id
            binding = self._resolve(name, chain)
            kind = binding[0]
            if kind == "local_class":
                return LOCAL_TYPE, None, "an instance of %s, a class defined inside %s()" % (name, binding[2])
            if kind == "module_class" and in_main:
                return ENTRY_SCRIPT, None, "an instance of %s, defined in the entry script" % name
            if kind in ("local_def", "module_def"):
                parent = chain if kind == "local_def" else [self._module_scope]
                returned = self._returned(binding[3], parent, visiting)
                if returned is not None:
                    rule, subject, noun = returned
                    shown = ("`%s`, %s" % (subject, noun)) if subject else noun
                    return rule, None, "the result of %s(), which returns %s" % (name, shown)
        return None

    @staticmethod
    def _describe_binding(binding: Binding, in_main: bool) -> Optional[Tuple[str, str]]:
        kind, name, owner = binding[0], binding[1], binding[2]
        if kind == "lambda":
            return LAMBDA, "a lambda"
        if kind == "local_def":
            return LOCAL_FUNCTION, "a function defined inside %s()" % owner
        if kind == "local_class":
            return LOCAL_TYPE, "a class defined inside %s()" % owner
        if kind == "local_instance":
            return LOCAL_TYPE, "an instance of %s, a class defined inside %s()" % (name, owner)
        if kind == "plain_pipeline":
            return UNNAMED_PIPELINE, "a plain Pipeline()"
        if kind == "module_def" and in_main:
            return ENTRY_SCRIPT, "a function defined in the entry script"
        if kind == "module_class" and in_main:
            return ENTRY_SCRIPT, "a class defined in the entry script"
        return None

    def _returned(self, func: ast.AST, parent_chain: List[Dict[str, Binding]],
                  visiting: Set[int]) -> Optional[Tuple[str, Optional[str], str]]:
        """What a closure factory returns, when a return we can see is anonymous."""
        if id(func) in visiting:
            return None
        visiting = visiting | {id(func)}
        chain = self._chain_for(func, parent_chain)
        for node in _own_nodes(func.body):
            if isinstance(node, ast.Return) and node.value is not None:
                got = self._describe(node.value, chain, False, visiting)
                if got is not None:
                    return got
        return None

    # -- walk -----------------------------------------------------------

    def findings(self) -> List[Finding]:
        self._walk(self._tree, [self._module_scope], False)
        return self._findings

    def _walk(self, node: ast.AST, chain: List[Dict[str, Binding]], in_main: bool) -> None:
        for child in ast.iter_child_nodes(node):
            child_main = in_main
            if child is self._main_block:
                child_main = True
            if isinstance(child, _FUNCS):
                if chain[0] is self._module_scope and child.name in self._main_functions:
                    child_main = True
                self._walk(child, self._chain_for(child, chain), child_main)
                continue
            if isinstance(child, ast.Call):
                self._check_call(child, chain, child_main)
            self._walk(child, chain, child_main)

    def _check_call(self, call: ast.Call, chain: List[Dict[str, Binding]], in_main: bool) -> None:
        func = call.func
        if isinstance(func, ast.Attribute) and func.attr in _STEP_METHODS:
            role = _STEP_METHODS[func.attr]
            for arg in list(call.args) + [k.value for k in call.keywords]:
                elements = arg.elts if isinstance(arg, (ast.List, ast.Tuple, ast.Set)) else [arg]
                for element in elements:
                    self._report(element, role, call, chain, in_main)
        elif (isinstance(func, ast.Name) and func.id == "Valve") or (
                isinstance(func, ast.Attribute) and func.attr == "Valve"):
            for index, arg in enumerate(call.args):
                self._report(arg, _VALVE_ROLES[min(index, 1)], call, chain, in_main)
            for keyword in call.keywords:
                if keyword.arg in _VALVE_KEYWORDS:
                    self._report(keyword.value, _VALVE_KEYWORDS[keyword.arg], call, chain, in_main)

    def _report(self, expr: ast.AST, role: str, call: ast.Call, chain: List[Dict[str, Binding]],
                in_main: bool) -> None:
        got = self._classify(expr, chain, in_main, set())
        if got is None and role == "Valve predicate" and isinstance(expr, ast.Name) \
                and self._resolve(expr.id, chain)[0] == "module_def":
            got = FUNCTION_PREDICATE, "`%s` is a function, not a predicate object" % expr.id
        if got is None:
            return
        rule, what = got
        key = (expr.lineno, expr.col_offset, rule)
        if key in self._seen:
            return
        self._seen.add(key)
        self._findings.append(make_finding("python", self._path, expr.lineno, expr.col_offset + 1, rule,
                                           role, what, call.lineno))
