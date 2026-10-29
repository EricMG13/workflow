"""Round 3 item 2 and round 5 item 10 for CP-1's first step (`source_context`), on its own file so
each shared file stays under about 60 s. Real `OwnerWorkflow` over a real `Execution`."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import defect_classes as dc
import s1a_runs

from deploy_workflow.owner_workflow import OWNER_SPECS, OwnerWorkflow

# CP-1 `source_context` verbatim paths and their sinks. Each is a plain `Text` / `Text | None`
# field of `SourceContextReport` (`SourceRegisterRow.assessment`, `EntityRegisterRow.entity`,
# `limitations`), rendered into canonical table cells (`str`) and `canonical_gaps` labels
# (`Text`). None is built as `RunText` or `Claim.text`: the claims of CP-1 are built from the
# narrative step's findings, not from this step's text.
CP1_CONTEXT_VERBATIM: Mapping[tuple[str | int, ...], str] = {
    ("entities", "*", "name"): "EntityContext.name (Text | None)",
    ("entities", "*", "fiscal_year_end"): "EntityContext.fiscal_year_end (Text | None)",
    ("entities", "*", "limitations", "*"): "EntityContext.limitations (Text)",
    ("limitations", "*"): "SourceContextReport.limitations (Text)",
    ("sources", "*", "document_type"): "SourceContext.document_type (Text | None)",
    ("sources", "*", "evidence_rationale"): "SourceContext.evidence_rationale (Text)",
    ("sources", "*", "analytical_use"): "SourceContext.analytical_use (Text)",
    ("sources", "*", "event_scan_explanation"): "SourceContext.event_scan_explanation (Text)",
    ("sources", "*", "limitations", "*"): "SourceContext.limitations (Text)",
    ("sources", "*", "scopes", "*", "period_label"): "ReportingScope.period_label (Text)",
    ("sources", "*", "scopes", "*", "limitations", "*"): "ReportingScope.limitations (Text)",
}


class _Cp1ContextRun:
    """CP-1's first step over a real store, after a valid CP-0: each submit repeats the reads and
    the two searches the literal `source_context` needs."""

    def __init__(self, workflow: OwnerWorkflow, positive: str) -> None:
        self._workflow = workflow
        self._positive = positive

    def submit_review(self, payload: str) -> Mapping[str, Any]:
        s1a_runs.read_cited(self._workflow, self._positive)
        s1a_runs.search(self._workflow, "financial", "subsequent")
        s1a_runs.search(self._workflow, "business", "acquisition")
        outcome: Mapping[str, Any] = self._workflow.submit_review(payload)
        return outcome


def test_cp1_source_context_model_text_is_journaled_except_on_its_verbatim_paths(
    tmp_path: Path,
) -> None:
    pack = s1a_runs.make_pack("positive")
    positive = s1a_runs.literal("positive", "cp1_source_context", pack)
    schema = OWNER_SPECS["CP-1"].steps[0].schema
    assert dc.free_text_paths(positive, schema), "source_context has free-text fields"
    # One workflow with CP-0 settled and CP-1 untouched; each case forks it (before any call).
    template, _ = s1a_runs.start("positive", tmp_path / "template")
    s1a_runs.drive_cp0(template, pack, "positive")
    counter = iter(range(10_000))

    def fresh() -> dc.ReviewRun:
        fork = s1a_runs.clone_workflow(template, tmp_path / str(next(counter)))
        return _Cp1ContextRun(fork, positive)

    failures = dc.model_text_failures(
        schema,
        positive,
        fresh,
        verbatim=frozenset(CP1_CONTEXT_VERBATIM),
        fill_absent=True,  # round 5 item 10 L2: events and scopes the positive leaves null
    )
    assert failures == []
