"""Scoped source operations staged until the host accepts the complete result."""

from collections.abc import Mapping, Sequence
from copy import copy
from typing import Any

from deploy_vii.live.tools import EXTRACT, READ, SEARCH, PackTools, ToolError
from deploy_vii.preparation import PreparedPack


class SourceError(ValueError):
    """Stable, sanitized refusal; never retains a raw source/exception message."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class SourceTools:
    """Trusted Python selects the explicit source IDs and extraction capability."""

    def __init__(self, pack: PreparedPack, sources: Sequence[str], *, extraction: bool) -> None:
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
        return body, staged

    def commit(self, staged: PackTools) -> None:
        self._tools = staged
