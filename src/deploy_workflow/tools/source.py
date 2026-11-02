"""Scoped source operations staged until the host accepts the complete result."""

import re
from collections.abc import Mapping, Sequence
from copy import copy
from typing import Any

from deploy_vii.live.tools import EXTRACT, READ, SEARCH, PackTools, ToolError
from deploy_vii.preparation import PreparedPack
from deploy_workflow.prompts.fence import FenceError, UntrustedItem, untrusted_evidence_block

# A SOURCE block as PackTools writes it (`block("SOURCE", id, sha256, "locator=<loc> ... ")`). A
# source body cannot hold `<<<END>>>` or `<<<SOURCE` (block() refuses both), so the first closing
# line ends the block and no body can forge a second one. The body is lazy, so a match ends at the
# first `<<<END>>>` and never runs on into the next block.
_RESEARCH_BLOCK = re.compile(
    r"<<<SOURCE id=(ev-\S+) sha256=([0-9a-f]{64})>>>\n(locator=(\S+).*?)\n<<<END>>>",
    re.DOTALL,
)
_RESEARCH_HEADER = "<<<SOURCE id=ev-"


class SourceError(ValueError):
    """Stable, sanitized refusal; never retains a raw source/exception message."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class SourceTools:
    """Trusted Python selects the explicit source IDs and extraction capability."""

    def __init__(
        self,
        pack: PreparedPack,
        sources: Sequence[str],
        *,
        extraction: bool,
        retrieved: Mapping[str, str] | None = None,
    ) -> None:
        # `retrieved` maps each `ev-*` research source to the time its item was retrieved (the
        # caller's record; never made up here). It is written into the untrusted-evidence header.
        self._retrieved = dict(retrieved or {})
        self._tools = PackTools(pack, sources=tuple(sources))
        self._names = {SEARCH: PackTools.search_pack, READ: PackTools.read_pages}
        if extraction:
            self._names[EXTRACT] = PackTools.extract_statements

    def evidence(self) -> dict[str, Any]:
        tools = self._tools
        return {
            "read": [list(pair) for pair in sorted(tools.read)],
            "extracted": [list(pair) for pair in sorted(tools.extracted)],
            "surfaced": [list(pair) for pair in sorted(tools.surfaced)],
            "searched": list(tools.searched),
        }

    def offers(self, name: str) -> bool:
        return name in self._names

    def stage(self, name: str, arguments: Mapping[str, Any]) -> tuple[str, PackTools]:
        if name not in self._names:
            raise SourceError("not_permitted")
        source_id = arguments.get("source_id")
        if "source_id" in arguments and not (
            isinstance(source_id, str) or (name == SEARCH and source_id is None)
        ):
            raise SourceError("bad_arguments")
        if isinstance(source_id, str):
            if source_id not in self._tools.ids:
                raise SourceError("not_permitted")
            if source_id not in self._tools.ready:
                raise SourceError("unavailable")
        # Frozen pack objects/maps can be shared. Evidence sets/lists cannot: even a late
        # snapshot rejection must leave earlier successful invocations unchanged.
        staged = copy(self._tools)
        staged.read = set(self._tools.read)
        staged.extracted = set(self._tools.extracted)
        staged.surfaced = set(self._tools.surfaced)
        staged.searched = list(self._tools.searched)
        try:
            body = self._names[name](staged, arguments)
        except ToolError:
            raise SourceError("bad_arguments") from None
        return self._fenced(body), staged

    def _fenced(self, body: str) -> str:
        """Research (`ev-*`) hits and pages enter the model only as UNTRUSTED_EVIDENCE blocks.

        Fails closed: an `ev-*` source with no recorded retrieval time refuses the whole call
        (`unavailable`; the host refuses such a session at construction, O7-R8), and a span the
        fence cannot hold raises its `FenceError` (a `PromptError`, which the host receipts as
        `render_refused`); nothing is staged, truncated or rewritten.
        """

        def fence(found: re.Match[str]) -> str:
            source_id = found.group(1)
            retrieved = self._retrieved.get(source_id)
            if retrieved is None:
                raise SourceError("unavailable")
            item = UntrustedItem(
                source_id, found.group(2), found.group(4), retrieved, found.group(3)
            )
            return untrusted_evidence_block([item])

        fenced = _RESEARCH_BLOCK.sub(fence, body)
        if _RESEARCH_HEADER in fenced:  # a header the match did not recognise stays unfenced
            raise FenceError("a research block was left outside the fence")
        return fenced

    def commit(self, staged: PackTools) -> None:
        self._tools = staged
