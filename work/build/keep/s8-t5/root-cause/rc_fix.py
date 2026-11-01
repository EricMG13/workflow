"""T5 root-cause: the proposed SourceSession.invoke check order (host.py only), as a
patchable function for the rc probes. Not a test double: it is the exact code proposed."""
from uuid import uuid4
from deploy_vii.live.prompts import PromptError
from deploy_workflow.host import _json_arguments
from deploy_workflow.tools.source import SourceError


def proposed_invoke(self, tool_name, arguments):
    with self._records_lock:
        self._sequence += 1
        sequence = self._sequence
    call_id = str(uuid4())
    # 1. name representable: exact str, UTF-8 encodable; no caller-object method runs.
    if type(tool_name) is not str:
        return self._receipt(sequence, call_id, "", {}, "refused", None, "not_permitted")
    try:
        tool_name.encode("utf-8")
    except UnicodeEncodeError:
        return self._receipt(sequence, call_id, "", {}, "refused", None, "not_permitted")
    name = tool_name
    # 2. arguments; the code is the one stage gives for (name, {}).
    try:
        copied = _json_arguments(arguments)
    except (ValueError, TypeError, RecursionError):
        code = "bad_arguments" if name in self._tools._names else "not_permitted"
        return self._receipt(sequence, call_id, name, {}, "refused", None, code)
    if not self._operation.acquire(blocking=False):
        return self._receipt(sequence, call_id, name, copied, "refused", None, "not_permitted")
    try:
        self._assert_current()
        body, staged = self._tools.stage(name, copied)
        self._assert_current()
        self._tools.commit(staged)
        return self._receipt(sequence, call_id, name, copied, "ok", body, None)
    except SourceError as error:
        return self._receipt(sequence, call_id, name, copied, "refused", None, error.code)
    except PromptError:
        return self._receipt(sequence, call_id, name, copied, "refused", None, "render_refused")
    except Exception:
        return self._receipt(sequence, call_id, name, copied, "error", None, "internal_error")
    finally:
        self._operation.release()
