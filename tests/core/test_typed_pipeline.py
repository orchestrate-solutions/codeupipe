"""Tests for codeupipe.core.typed — the typed pipeline API."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from codeupipe.core.typed import (
    TypedFilter,
    TypedHook,
    TypedPipeline,
    TypedTap,
    TypedValve,
)


# ---------- shared Ctx ----------

@dataclass
class Ctx:
    n: int
    flag: bool = False


# ---------- fixtures ----------

class Increment(TypedFilter[Ctx]):
    def call(self, ctx: Ctx) -> Ctx:
        return Ctx(n=ctx.n + 1, flag=ctx.flag)


class Doubler(TypedFilter[Ctx]):
    def call(self, ctx: Ctx) -> Ctx:
        return Ctx(n=ctx.n * 2, flag=ctx.flag)


class Exploder(TypedFilter[Ctx]):
    def call(self, ctx: Ctx) -> Ctx:
        raise RuntimeError("boom")


# ---------- primitive tests ----------

def test_empty_pipeline_passes_ctx_through():
    pipe: TypedPipeline[Ctx] = TypedPipeline()
    out = pipe.run(Ctx(n=42))
    assert out.n == 42


def test_single_filter_transforms():
    pipe = TypedPipeline[Ctx]().add_filter(Increment(), "inc")
    assert pipe.run(Ctx(n=0)).n == 1


def test_chained_filters_apply_in_order():
    pipe = TypedPipeline[Ctx]().add_filter(Increment(), "inc").add_filter(Doubler(), "dbl")
    # (3 + 1) * 2 = 8
    assert pipe.run(Ctx(n=3)).n == 8


def test_tap_observes_without_mutating():
    seen: list[int] = []

    class Peek(TypedTap[Ctx]):
        def observe(self, ctx: Ctx) -> None:
            seen.append(ctx.n)

    pipe = (
        TypedPipeline[Ctx]()
        .add_filter(Increment(), "inc")
        .add_tap(Peek(), "peek")
    )
    out = pipe.run(Ctx(n=10))
    assert out.n == 11
    assert seen == [11]


def test_disabled_tap_marks_skipped():
    seen: list[int] = []

    class Peek(TypedTap[Ctx]):
        def observe(self, ctx: Ctx) -> None:
            seen.append(ctx.n)

    pipe = (
        TypedPipeline[Ctx]()
        .add_tap(Peek(), "peek")
        .disable_taps("peek")
    )
    pipe.run(Ctx(n=5))
    assert seen == []
    assert "peek" in pipe.state.skipped


def test_valve_runs_when_predicate_true():
    valve = TypedValve(Increment(), lambda c: c.flag)
    pipe = TypedPipeline[Ctx]().add_filter(valve, "gated")
    out = pipe.run(Ctx(n=5, flag=True))
    assert out.n == 6


def test_valve_skips_when_predicate_false():
    valve = TypedValve(Increment(), lambda c: c.flag)
    pipe = TypedPipeline[Ctx]().add_filter(valve, "gated")
    out = pipe.run(Ctx(n=5, flag=False))
    assert out.n == 5
    assert "gated" in pipe.state.skipped


def test_hooks_fire_for_each_filter_step():
    events: list[str] = []

    class Recorder(TypedHook[Ctx]):
        def before(self, step_name, ctx):
            if step_name is not None:
                events.append(f"before:{step_name}")

        def after(self, step_name, ctx):
            if step_name is not None:
                events.append(f"after:{step_name}")

    pipe = (
        TypedPipeline[Ctx]()
        .add_filter(Increment(), "inc")
        .add_filter(Doubler(), "dbl")
        .use_hook(Recorder())
    )
    pipe.run(Ctx(n=1))
    assert events == [
        "before:inc",
        "after:inc",
        "before:dbl",
        "after:dbl",
    ]


def test_error_hook_fires_and_reraises():
    caught: list[tuple] = []

    class ErrHook(TypedHook[Ctx]):
        def on_error(self, step_name, err):
            caught.append((step_name, type(err).__name__, str(err)))

    pipe = (
        TypedPipeline[Ctx]()
        .add_filter(Exploder(), "boom")
        .use_hook(ErrHook())
    )
    with pytest.raises(RuntimeError, match="boom"):
        pipe.run(Ctx(n=0))
    assert caught == [("boom", "RuntimeError", "boom")]


# ---------- manifesto invariants ----------

def test_removing_taps_yields_identical_output():
    """Invariant #1: Removing every Tap must yield identical output."""

    class Peek(TypedTap[Ctx]):
        def observe(self, ctx: Ctx) -> None:
            pass

    with_tap = (
        TypedPipeline[Ctx]()
        .add_filter(Increment(), "inc")
        .add_tap(Peek(), "peek")
        .add_filter(Doubler(), "dbl")
    )
    without_tap = (
        TypedPipeline[Ctx]()
        .add_filter(Increment(), "inc")
        .add_filter(Doubler(), "dbl")
    )
    a = with_tap.run(Ctx(n=3))
    b = without_tap.run(Ctx(n=3))
    assert a == b


def test_same_ctx_same_pipe_same_output():
    """Invariant #2: Determinism."""
    def build() -> TypedPipeline[Ctx]:
        return (
            TypedPipeline[Ctx]()
            .add_filter(Increment(), "inc")
            .add_filter(Doubler(), "dbl")
        )

    a = build().run(Ctx(n=7))
    b = build().run(Ctx(n=7))
    assert a == b


# ---------- fast-path ----------

def test_fast_path_when_no_hooks_or_taps():
    pipe = TypedPipeline[Ctx]().add_filter(Increment(), "inc").add_filter(Doubler(), "dbl")
    assert pipe._can_run_fast()
    assert pipe.run(Ctx(n=0)).n == 2


def test_fast_path_disabled_by_tap():
    class Peek(TypedTap[Ctx]):
        def observe(self, ctx: Ctx) -> None:
            pass

    pipe = TypedPipeline[Ctx]().add_filter(Increment(), "inc").add_tap(Peek(), "peek")
    assert not pipe._can_run_fast()


def test_fast_path_disabled_by_hook():
    class NoOp(TypedHook[Ctx]):
        pass

    pipe = TypedPipeline[Ctx]().add_filter(Increment(), "inc").use_hook(NoOp())
    assert not pipe._can_run_fast()


# ---------- dynamic escape hatch ----------

def test_dict_as_ctx_works_as_escape_hatch():
    """You can use dict as Ctx if you need a dynamic bag of keys."""

    class DictInc(TypedFilter[dict]):
        def call(self, ctx: dict) -> dict:
            return {**ctx, "n": ctx.get("n", 0) + 1}

    pipe: TypedPipeline[dict] = TypedPipeline().add_filter(DictInc(), "inc")
    out = pipe.run({"n": 10})
    assert out == {"n": 11}
