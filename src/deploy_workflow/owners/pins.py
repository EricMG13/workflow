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
from collections.abc import Callable, Mapping, Sequence
from decimal import Context, Decimal
from typing import Any

from pydantic import JsonValue

from deploy_vii.execution import clipped
from deploy_vii.preparation import PreparedPack
from deploy_workflow.context import (
    NUM,
    Cp2aPins,
    Cp2aScenario,
    Cp2dPins,
    Cp2ePins,
    Cp3cPins,
    Cp3dPins,
    Cp4cPins,
    RunContext,
    context_facts,
)

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
    """``value`` as plain digits, no exponent, no trailing zeros: ``100``, ``10.5``, ``0``.

    Exact at any precision and under any caller ``localcontext``: ``format(value, "f")`` and a
    text strip never round (``normalize()`` would, at the context precision).
    """
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def _fraction(percent: str) -> Decimal:
    return _PERCENT.divide(Decimal(percent), _HUNDRED)


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


# The module's slice of ``assumptions`` and its context path root, once per call.
def _slice_of(module_id: str, ctx: RunContext) -> tuple[Any, str] | None:
    name = _slice_name(module_id)
    piece = getattr(ctx.assumptions, name)
    return None if piece is None else (piece, f"assumptions.{name}")


# -- the pins ------------------------------------------------------------------------------


def _pins_cp2a(piece: Cp2aPins, root: str) -> dict[str, Pin]:
    return {
        f"{root}.scenarios": tuple(
            (_fraction(s.ebitda_decline_pct), _fraction(s.interest_increase_pct))
            for s in piece.scenarios
        )
    }


def _pins_cp2d(piece: Cp2dPins, root: str) -> dict[str, Pin]:
    return {
        f"{root}.horizon_months": Decimal(piece.horizon_months),
        f"{root}.minimum_cash_m": Decimal(piece.minimum_cash_m),
    }


def _pins_cp2e(piece: Cp2ePins, root: str) -> dict[str, Pin]:
    pins: dict[str, Pin] = {
        f"{root}.rate_shocks_bps": tuple(Decimal(x) for x in piece.rate_shocks_bps),
        f"{root}.fx_shocks_pct": tuple(Decimal(x) for x in piece.fx_shocks_pct),
    }
    if piece.hedge_ratio_pct != "":
        pins[f"{root}.hedge_ratio_pct"] = Decimal(piece.hedge_ratio_pct)
    return pins


def _pins_cp3c(piece: Cp3cPins, root: str) -> dict[str, Pin]:
    return {f"{root}.repricing_bps": Decimal(piece.repricing_bps)}


def _pins_cp3d(piece: Cp3dPins, root: str) -> dict[str, Pin]:
    return {f"{root}.recovery_pct": Decimal(piece.recovery_pct)}


def _pins_cp4c(piece: Cp4cPins, root: str) -> dict[str, Pin]:
    return {f"{root}.ev_multiple": Decimal(piece.ev_multiple)}


_PINNERS: dict[str, Callable[[Any, str], dict[str, Pin]]] = {
    "CP-2A": _pins_cp2a,
    "CP-2D": _pins_cp2d,
    "CP-2E": _pins_cp2e,
    "CP-3C": _pins_cp3c,
    "CP-3D": _pins_cp3d,
    "CP-4C": _pins_cp4c,
}


def pins_from_context(module_id: str, ctx: RunContext) -> Mapping[str, Pin] | None:
    """The module's pins keyed by context path; ``None`` when the module has no pin slice.

    CP-2A scenarios are ``(decline, interest)`` fraction pairs (the submission's units); a blank
    CP-2E hedge ratio has no key. Every other value is the typed number, unchanged.
    """
    found = _slice_of(module_id, ctx)
    return None if found is None else _PINNERS[module_id](*found)


def pins_of(module_id: str, pack: PreparedPack) -> Mapping[str, Pin] | None:
    """The module's pins from the pack's frozen context.

    ``None`` when the pack carries no context or the module has no pin. A context that differs
    from the run raises ``ContextRefused`` (from ``context_facts``); it is not caught here.
    """
    _slice_name(module_id)
    ctx = context_facts(pack)
    return None if ctx is None else pins_from_context(module_id, ctx)


# -- the submission form ---------------------------------------------------------------------


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


def _form_cp2a(pins: Mapping[str, Pin], root: str) -> dict[str, JsonValue]:
    scenarios = pins[f"{root}.scenarios"]
    if not isinstance(scenarios, tuple):
        raise TypeError(f"{root}.scenarios is not a list")
    return {
        "scenarios": [
            {"ebitda_decline": _plain(pair[0]), "interest_increase": _plain(pair[1])}
            for pair in scenarios
            if isinstance(pair, tuple)
        ]
    }


def _form_cp2d(pins: Mapping[str, Pin], root: str) -> dict[str, JsonValue]:
    return {
        "horizon_months": _scalar(pins, f"{root}.horizon_months"),
        "minimum_cash.amount": _scalar(pins, f"{root}.minimum_cash_m"),
    }


def _form_cp2e(pins: Mapping[str, Pin], root: str) -> dict[str, JsonValue]:
    form: dict[str, JsonValue] = {
        "rate_shocks_bp": _series(pins, f"{root}.rate_shocks_bps"),
        "fx_shocks_percent": _series(pins, f"{root}.fx_shocks_pct"),
    }
    if f"{root}.hedge_ratio_pct" in pins:
        form["hedge_ratio.percent_text"] = _scalar(pins, f"{root}.hedge_ratio_pct")
    return form


def _form_cp3c(pins: Mapping[str, Pin], root: str) -> dict[str, JsonValue]:
    return {"repricing.bps": _scalar(pins, f"{root}.repricing_bps")}


def _form_cp3d(pins: Mapping[str, Pin], root: str) -> dict[str, JsonValue]:
    return {"recovery.percent_text": _scalar(pins, f"{root}.recovery_pct")}


def _form_cp4c(pins: Mapping[str, Pin], root: str) -> dict[str, JsonValue]:
    return {"valuation[*].multiple": _scalar(pins, f"{root}.ev_multiple")}


_FORMS: dict[str, Callable[[Mapping[str, Pin], str], dict[str, JsonValue]]] = {
    "CP-2A": _form_cp2a,
    "CP-2D": _form_cp2d,
    "CP-2E": _form_cp2e,
    "CP-3C": _form_cp3c,
    "CP-3D": _form_cp3d,
    "CP-4C": _form_cp4c,
}


def form_from_context(module_id: str, ctx: RunContext) -> Mapping[str, JsonValue] | None:
    """What a submission that honours the pins carries, keyed by submission path.

    Values are normalised strings (``_plain``); nothing is rounded. ``None`` when not pinned.
    """
    found = _slice_of(module_id, ctx)
    if found is None:
        return None
    pins = pins_from_context(module_id, ctx)
    assert pins is not None
    return _FORMS[module_id](pins, found[1])


def submission_form(module_id: str, pack: PreparedPack) -> Mapping[str, JsonValue] | None:
    """``form_from_context`` for the pack's frozen context; ``None`` when there is no pin."""
    _slice_name(module_id)
    ctx = context_facts(pack)
    return None if ctx is None else form_from_context(module_id, ctx)


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


def _pin_decimal(pins: Mapping[str, Pin], path: str) -> Decimal:
    pin = pins[path]
    if not isinstance(pin, Decimal):
        raise TypeError(f"{path} is not a single number")
    return pin


def _scalar_lines(
    submitted: Mapping[str, Submitted], pins: Mapping[str, Pin], path: str, key: str, typed: str
) -> list[str]:
    sent = _text(submitted.get(key), key)
    return [] if _same(_pin_decimal(pins, path), sent) else [mismatch(path, typed, sent)]


def _series_lines(
    submitted: Mapping[str, Submitted],
    pins: Mapping[str, Pin],
    path: str,
    key: str,
    typed: tuple[str, ...],
) -> list[str]:
    sent = _texts(submitted.get(key), key)
    pin = pins[path]
    if not isinstance(pin, tuple):
        raise TypeError(f"{path} is not a list of numbers")
    numbers = tuple(p for p in pin if isinstance(p, Decimal))
    if _same_list(numbers, sent):
        return []
    return [mismatch(path, ", ".join(typed), _joined(sent))]


def _rows(raw: Submitted) -> list[Mapping[str, str | None]]:
    if raw is None:
        return []
    if isinstance(raw, str):
        raise TypeError("scenarios must be a list")
    rows: list[Mapping[str, str | None]] = []
    for row in raw:
        if not isinstance(row, Mapping):
            raise TypeError("scenarios must be a list of objects")
        rows.append(row)
    return rows


def _scenario_lines(
    root: str, i: int, row: Mapping[str, str | None], typed: Cp2aScenario, pair: object
) -> list[str]:
    if not isinstance(pair, tuple):
        raise TypeError(f"{root}.scenarios[{i}] is not a pair")
    fields = (
        ("ebitda_decline_pct", "ebitda_decline", typed.ebitda_decline_pct, pair[0]),
        ("interest_increase_pct", "interest_increase", typed.interest_increase_pct, pair[1]),
    )
    lines: list[str] = []
    for field, key, pin_text, pin in fields:
        sent = _text(row.get(key), f"scenarios[{i}].{key}")
        if not _same(pin, sent):
            shown = f"{_plain(pin)} ({pin_text}%)"
            lines.append(mismatch(f"{root}.scenarios[{i}].{field}", shown, sent))
    return lines


def _issues_cp2a(
    piece: Cp2aPins, pins: Mapping[str, Pin], root: str, submitted: Mapping[str, Submitted]
) -> list[str]:
    rows = _rows(submitted.get("scenarios"))
    count = len(piece.scenarios)
    if len(rows) != count:
        return [mismatch(f"{root}.scenarios", _plural(count, "scenario"), str(len(rows)))]
    pairs = pins[f"{root}.scenarios"]
    if not isinstance(pairs, tuple):
        raise TypeError(f"{root}.scenarios is not a list")
    lines: list[str] = []
    for i, (row, typed, pair) in enumerate(zip(rows, piece.scenarios, pairs, strict=True)):
        lines.extend(_scenario_lines(root, i, row, typed, pair))
    return lines


def _issues_cp2d(
    piece: Cp2dPins, pins: Mapping[str, Pin], root: str, submitted: Mapping[str, Submitted]
) -> list[str]:
    horizon, cash = f"{root}.horizon_months", f"{root}.minimum_cash_m"
    return [
        *_scalar_lines(submitted, pins, horizon, "horizon_months", piece.horizon_months),
        *_scalar_lines(submitted, pins, cash, "minimum_cash.amount", piece.minimum_cash_m),
    ]


def _issues_cp2e(
    piece: Cp2ePins, pins: Mapping[str, Pin], root: str, submitted: Mapping[str, Submitted]
) -> list[str]:
    lines = [
        *_series_lines(
            submitted, pins, f"{root}.rate_shocks_bps", "rate_shocks_bp", piece.rate_shocks_bps
        ),
        *_series_lines(
            submitted, pins, f"{root}.fx_shocks_pct", "fx_shocks_percent", piece.fx_shocks_pct
        ),
    ]
    hedge = f"{root}.hedge_ratio_pct"
    if hedge in pins:
        key = "hedge_ratio.percent_text"
        lines.extend(_scalar_lines(submitted, pins, hedge, key, piece.hedge_ratio_pct))
    return lines


def _issues_cp3c(
    piece: Cp3cPins, pins: Mapping[str, Pin], root: str, submitted: Mapping[str, Submitted]
) -> list[str]:
    path = f"{root}.repricing_bps"
    return _scalar_lines(submitted, pins, path, "repricing.bps", piece.repricing_bps)


def _issues_cp3d(
    piece: Cp3dPins, pins: Mapping[str, Pin], root: str, submitted: Mapping[str, Submitted]
) -> list[str]:
    path = f"{root}.recovery_pct"
    return _scalar_lines(submitted, pins, path, "recovery.percent_text", piece.recovery_pct)


def _issues_cp4c(
    piece: Cp4cPins, pins: Mapping[str, Pin], root: str, submitted: Mapping[str, Submitted]
) -> list[str]:
    """One line per submitted multiple that differs; one absence line when none is submitted."""
    path = f"{root}.ev_multiple"
    pin = _pin_decimal(pins, path)
    key = "valuation[*].multiple"
    sent = _texts(submitted.get(key), key)
    if not sent:
        return [mismatch(path, piece.ev_multiple, None)]
    return [
        mismatch(path, piece.ev_multiple, text, at=f"valuation[{i}].multiple")
        for i, text in enumerate(sent)
        if not _same(pin, text)
    ]


_CHECKS: dict[str, Callable[[Any, Mapping[str, Pin], str, Mapping[str, Submitted]], list[str]]] = {
    "CP-2A": _issues_cp2a,
    "CP-2D": _issues_cp2d,
    "CP-2E": _issues_cp2e,
    "CP-3C": _issues_cp3c,
    "CP-3D": _issues_cp3d,
    "CP-4C": _issues_cp4c,
}


def pin_issues_from_context(
    module_id: str, ctx: RunContext | None, submitted: Mapping[str, Submitted]
) -> tuple[str, ...]:
    """One line per figure in ``submitted`` that differs from the pin, in context order.

    ``submitted`` is keyed like ``form_from_context``; CP-4C's ``valuation[*].multiple`` is the
    list of the submitted multiples, one per valuation case, in case order. A missing key is
    absence (CP-4C: one absence line when no multiple is submitted at all). Nothing is returned
    when ``ctx`` is ``None`` or the module is not pinned.
    """
    _slice_name(module_id)
    if ctx is None:
        return ()
    found = _slice_of(module_id, ctx)
    if found is None:
        return ()
    piece, root = found
    pins = _PINNERS[module_id](piece, root)
    return tuple(_CHECKS[module_id](piece, pins, root, submitted))


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
