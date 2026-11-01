"""Pinned assumptions: read from the frozen context file and compared with a submission.

A user may pin an assumption (shock sizes, a horizon, a recovery rate ...) in the context file.
The six owner modules then refuse a submission whose figure differs from the pin and label the
assumption user-supplied. This module is the one reader and comparator they share:

* ``pins_of`` / ``pins_from_context``: the pins as ``Decimal``, keyed by context path.
* ``submission_form`` / ``form_from_context``: what a conforming submission carries, keyed by
  submission path, as normalised strings (the body of the O6 pin block).
* ``pin_issues`` / ``pin_issues_from_context``: one ``mismatch`` line per differing figure.
* ``pinned_line``: the limitation sentence stating the figure is user-supplied.

Python owns the arithmetic: only ``Decimal`` is used. A submitted string is converted only after a
whole-string ASCII ``NUM`` match; anything else is reported as typed and never equals a pin.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from decimal import Context, Decimal

from pydantic import JsonValue

from deploy_vii.execution import clipped
from deploy_vii.preparation import PreparedPack
from deploy_workflow.context import NUM, RunContext, context_facts

Pin = Decimal | tuple[Decimal, ...] | tuple[tuple[Decimal, Decimal], ...]
Submitted = str | None | Sequence[str | None] | Sequence[Mapping[str, str | None]]

_SLICES = {
    "CP-2A": "cp2a",
    "CP-2D": "cp2d",
    "CP-2E": "cp2e",
    "CP-3C": "cp3c",
    "CP-3D": "cp3d",
    "CP-4C": "cp4c",
}
_PERCENT = Context(prec=60)
_HUNDRED = Decimal(100)

_PINNED = (
    "are user-supplied assumptions pinned in the context file; the submission equals the pins."
)
_PINNED_ONE = (
    "is a user-supplied assumption pinned in the context file; the submission equals the pin."
)
_SUBJECT = {
    "CP-2A": f"Scenario shock sizes {_PINNED}",
    "CP-2D": f"The horizon and minimum cash {_PINNED}",
    "CP-2E": f"The shock sizes {_PINNED}",
    "CP-3C": f"The margin step-up {_PINNED_ONE}",
    "CP-3D": f"The recovery rate {_PINNED_ONE}",
    "CP-4C": f"The EV multiple {_PINNED_ONE}",
}
_CP2E_WITH_HEDGE = f"The shock sizes and hedge ratio {_PINNED}"


def _slice_name(module_id: str) -> str:
    try:
        return _SLICES[module_id]
    except KeyError:
        raise KeyError(f"unknown pinned-assumption module: {module_id}") from None


def _plain(value: Decimal) -> str:
    """``value`` without exponent or trailing zeros: ``100`` stays ``100``, ``10.50`` is ``10.5``."""
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _fraction(percent: str) -> Decimal:
    return _PERCENT.divide(Decimal(percent), _HUNDRED)


# -- the pins ------------------------------------------------------------------------------


def pins_from_context(module_id: str, ctx: RunContext) -> Mapping[str, Pin] | None:
    """The module's pins keyed by context path; ``None`` when the module has no pin slice.

    CP-2A scenarios are ``(decline, interest)`` fraction pairs (the submission's units); a blank
    CP-2E hedge ratio has no key. Every other value is the typed number, unchanged.
    """
    name = _slice_name(module_id)
    a = ctx.assumptions
    root = f"assumptions.{name}"
    if module_id == "CP-2A":
        if a.cp2a is None:
            return None
        return {
            f"{root}.scenarios": tuple(
                (_fraction(s.ebitda_decline_pct), _fraction(s.interest_increase_pct))
                for s in a.cp2a.scenarios
            )
        }
    if module_id == "CP-2D":
        if a.cp2d is None:
            return None
        return {
            f"{root}.horizon_months": Decimal(a.cp2d.horizon_months),
            f"{root}.minimum_cash_m": Decimal(a.cp2d.minimum_cash_m),
        }
    if module_id == "CP-2E":
        if a.cp2e is None:
            return None
        pins: dict[str, Pin] = {
            f"{root}.rate_shocks_bps": tuple(Decimal(x) for x in a.cp2e.rate_shocks_bps),
            f"{root}.fx_shocks_pct": tuple(Decimal(x) for x in a.cp2e.fx_shocks_pct),
        }
        if a.cp2e.hedge_ratio_pct != "":
            pins[f"{root}.hedge_ratio_pct"] = Decimal(a.cp2e.hedge_ratio_pct)
        return pins
    if module_id == "CP-3C":
        return None if a.cp3c is None else {f"{root}.repricing_bps": Decimal(a.cp3c.repricing_bps)}
    if module_id == "CP-3D":
        return None if a.cp3d is None else {f"{root}.recovery_pct": Decimal(a.cp3d.recovery_pct)}
    return None if a.cp4c is None else {f"{root}.ev_multiple": Decimal(a.cp4c.ev_multiple)}


def pins_of(module_id: str, pack: PreparedPack) -> Mapping[str, Pin] | None:
    """The module's pins from the pack's frozen context.

    ``None`` when the pack carries no context or the module has no pin. A context that differs
    from the run raises ``ContextRefused`` (from ``context_facts``); it is not caught here.
    """
    _slice_name(module_id)
    ctx = context_facts(pack)
    return None if ctx is None else pins_from_context(module_id, ctx)


# -- the submission form ---------------------------------------------------------------------


def form_from_context(module_id: str, ctx: RunContext) -> Mapping[str, JsonValue] | None:
    """What a submission that honours the pins carries, keyed by submission path.

    Values are normalised strings (``_plain``); nothing is rounded. ``None`` when not pinned.
    """
    pins = pins_from_context(module_id, ctx)
    if pins is None:
        return None
    root = f"assumptions.{_SLICES[module_id]}"
    if module_id == "CP-2A":
        scenarios = pins[f"{root}.scenarios"]
        assert isinstance(scenarios, tuple)
        return {
            "scenarios": [
                {"ebitda_decline": _plain(pair[0]), "interest_increase": _plain(pair[1])}
                for pair in scenarios
                if isinstance(pair, tuple)
            ]
        }
    if module_id == "CP-2D":
        return {
            "horizon_months": _scalar(pins, f"{root}.horizon_months"),
            "minimum_cash.amount": _scalar(pins, f"{root}.minimum_cash_m"),
        }
    if module_id == "CP-2E":
        form: dict[str, JsonValue] = {
            "rate_shocks_bp": _series(pins, f"{root}.rate_shocks_bps"),
            "fx_shocks_percent": _series(pins, f"{root}.fx_shocks_pct"),
        }
        if f"{root}.hedge_ratio_pct" in pins:
            form["hedge_ratio.percent_text"] = _scalar(pins, f"{root}.hedge_ratio_pct")
        return form
    if module_id == "CP-3C":
        return {"repricing.bps": _scalar(pins, f"{root}.repricing_bps")}
    if module_id == "CP-3D":
        return {"recovery.percent_text": _scalar(pins, f"{root}.recovery_pct")}
    return {"valuation[*].multiple": _scalar(pins, f"{root}.ev_multiple")}


def submission_form(module_id: str, pack: PreparedPack) -> Mapping[str, JsonValue] | None:
    """``form_from_context`` for the pack's frozen context; ``None`` when there is no pin."""
    _slice_name(module_id)
    ctx = context_facts(pack)
    return None if ctx is None else form_from_context(module_id, ctx)


def _scalar(pins: Mapping[str, Pin], key: str) -> str:
    value = pins[key]
    if not isinstance(value, Decimal):
        raise TypeError(f"{key} is not a single number")
    return _plain(value)


def _series(pins: Mapping[str, Pin], key: str) -> list[JsonValue]:
    value = pins[key]
    if not isinstance(value, tuple):
        raise TypeError(f"{key} is not a list of numbers")
    return [_plain(x) for x in value if isinstance(x, Decimal)]


# -- the comparison --------------------------------------------------------------------------


def mismatch(path: str, pinned_as_typed: str, submitted: str | None, *, at: str = "") -> str:
    """``<path>[ (<at>)]: pinned <pin>; submitted <value|absence>``, the submitted text clipped."""
    where = f" ({at})" if at else ""
    return clipped(
        (
            path,
            where,
            ": pinned ",
            pinned_as_typed,
            "; submitted ",
            "absence" if submitted is None else submitted,
        )
    )


def _same(pin: Decimal, text: str | None) -> bool:
    """True when ``text`` is a plain number equal to ``pin``; junk equals nothing."""
    return (
        text is not None and re.fullmatch(NUM, text, re.ASCII) is not None and Decimal(text) == pin
    )


def _same_list(pins: tuple[Decimal, ...], items: Sequence[str | None]) -> bool:
    return len(items) == len(pins) and all(_same(p, t) for p, t in zip(pins, items, strict=True))


def _text(value: Submitted, key: str) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise TypeError(f"{key} must be a string or absent")


def _texts(value: Submitted, key: str) -> list[str | None]:
    if value is None:
        return []
    if isinstance(value, str):
        raise TypeError(f"{key} must be a list")
    items: list[str | None] = []
    for item in value:
        if item is not None and not isinstance(item, str):
            raise TypeError(f"{key} must be a list of strings")
        items.append(item)
    return items


def _joined(items: Sequence[str | None]) -> str | None:
    """The shown form of a submitted list: ``a, b``; ``None`` (absence) when it has no items."""
    if not items:
        return None
    return ", ".join("absence" if item is None else item for item in items)


def pin_issues_from_context(
    module_id: str, ctx: RunContext | None, submitted: Mapping[str, Submitted]
) -> tuple[str, ...]:
    """One line per figure in ``submitted`` that differs from the pin, in context order.

    ``submitted`` is keyed like ``form_from_context``; CP-4C's ``valuation[*].multiple`` is the
    list of the submitted multiples, one per valuation case, in case order. A missing key is
    absence. Nothing is returned when ``ctx`` is ``None`` or the module is not pinned.
    """
    _slice_name(module_id)
    if ctx is None:
        return ()
    pins = pins_from_context(module_id, ctx)
    if pins is None:
        return ()
    root = f"assumptions.{_SLICES[module_id]}"
    a = ctx.assumptions
    lines: list[str] = []

    def scalar(path: str, key: str, typed: str) -> None:
        sent = _text(submitted.get(key), key)
        pin = pins[path]
        assert isinstance(pin, Decimal)
        if not _same(pin, sent):
            lines.append(mismatch(path, typed, sent))

    def series(path: str, key: str, typed: tuple[str, ...]) -> None:
        sent = _texts(submitted.get(key), key)
        pin = pins[path]
        assert isinstance(pin, tuple)
        if not _same_list(tuple(p for p in pin if isinstance(p, Decimal)), sent):
            lines.append(mismatch(path, ", ".join(typed), _joined(sent)))

    if module_id == "CP-2A":
        assert a.cp2a is not None
        raw = submitted.get("scenarios")
        if raw is None:
            rows: list[Mapping[str, str | None]] = []
        elif isinstance(raw, str):
            raise TypeError("scenarios must be a list")
        else:
            rows = []
            for row in raw:
                if not isinstance(row, Mapping):
                    raise TypeError("scenarios must be a list of objects")
                rows.append(row)
        typed_rows = a.cp2a.scenarios
        if len(rows) != len(typed_rows):
            lines.append(
                mismatch(f"{root}.scenarios", f"{len(typed_rows)} scenarios", str(len(rows)))
            )
        else:
            pairs = pins[f"{root}.scenarios"]
            assert isinstance(pairs, tuple)
            for i, (row, typed, pair) in enumerate(zip(rows, typed_rows, pairs, strict=True)):
                assert isinstance(pair, tuple)
                for field, key, pin_text, pin in (
                    ("ebitda_decline_pct", "ebitda_decline", typed.ebitda_decline_pct, pair[0]),
                    (
                        "interest_increase_pct",
                        "interest_increase",
                        typed.interest_increase_pct,
                        pair[1],
                    ),
                ):
                    sent = _text(row.get(key), f"scenarios[{i}].{key}")
                    assert isinstance(pin, Decimal)
                    if not _same(pin, sent):
                        lines.append(
                            mismatch(
                                f"{root}.scenarios[{i}].{field}",
                                f"{_plain(pin)} ({pin_text}%)",
                                sent,
                            )
                        )
    elif module_id == "CP-2D":
        assert a.cp2d is not None
        scalar(f"{root}.horizon_months", "horizon_months", a.cp2d.horizon_months)
        scalar(f"{root}.minimum_cash_m", "minimum_cash.amount", a.cp2d.minimum_cash_m)
    elif module_id == "CP-2E":
        assert a.cp2e is not None
        series(f"{root}.rate_shocks_bps", "rate_shocks_bp", a.cp2e.rate_shocks_bps)
        series(f"{root}.fx_shocks_pct", "fx_shocks_percent", a.cp2e.fx_shocks_pct)
        if f"{root}.hedge_ratio_pct" in pins:
            scalar(f"{root}.hedge_ratio_pct", "hedge_ratio.percent_text", a.cp2e.hedge_ratio_pct)
    elif module_id == "CP-3C":
        assert a.cp3c is not None
        scalar(f"{root}.repricing_bps", "repricing.bps", a.cp3c.repricing_bps)
    elif module_id == "CP-3D":
        assert a.cp3d is not None
        scalar(f"{root}.recovery_pct", "recovery.percent_text", a.cp3d.recovery_pct)
    else:
        assert a.cp4c is not None
        pin = pins[f"{root}.ev_multiple"]
        assert isinstance(pin, Decimal)
        key = "valuation[*].multiple"
        for i, sent in enumerate(_texts(submitted.get(key), key)):
            if not _same(pin, sent):
                lines.append(
                    mismatch(
                        f"{root}.ev_multiple",
                        a.cp4c.ev_multiple,
                        sent,
                        at=f"valuation[{i}].multiple",
                    )
                )
    return tuple(lines)


def pin_issues(
    module_id: str, pack: PreparedPack, submitted: Mapping[str, Submitted]
) -> tuple[str, ...]:
    """``pin_issues_from_context`` for the pack's frozen context.

    A context that differs from the run raises ``ContextRefused`` (``context_facts``); the owner
    turns it into the single issue ``Context refused: <message>``.
    """
    _slice_name(module_id)
    return pin_issues_from_context(module_id, context_facts(pack), submitted)


def pinned_line(module_id: str, *, hedge_pinned: bool = False) -> str:
    """The one-sentence limitation that states the module's figures are user-supplied pins."""
    _slice_name(module_id)
    if module_id == "CP-2E" and hedge_pinned:
        return _CP2E_WITH_HEDGE
    return _SUBJECT[module_id]
