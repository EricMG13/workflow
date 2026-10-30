# Task 2 review: 67e0c51..4af08ce (mx-precise; returned as text, saved by the controller)

Spec ✅ · Task quality: Approved · High none · Medium none

- Change `execution.py:543-551`, `:622`: `_canonical_result` under `@lru_cache(maxsize=4)` with the
  old `result` body unchanged; `result` = `_canonical_result(sha256, self._load(sha256))`;
  comment `:540-544` covers in-process, `_load` per call, exceptions not cached, ponytail ceiling.
- `probes/task2_equivalence.py` exit 0: old body vs new, 3 calls each, on good, non-canonical,
  invalid JSON, non-Module JSON, missing, malformed hash, uppercase hash, tamper-after-hit — same
  exception type+message or byte-identical dump every call; maxsize == 4.
- Hit safety: key (sha256, raw) after `_load` verification; Contract frozen, no dict/list/set fields.
- `probes/task2_red_on_old.py` exit 0: old 2 parses, new 1.
- `pytest tests/test_execution_result_cache.py tests/test_host_h1.py`: 41 passed in 7.3 s.
- Low `execution.py:543-544`: ponytail ceiling omits key bytes (≈42 MiB raw per CP-1 entry kept
  alive by the key) → worst case ≈1.1 GiB not ≈1 GiB; keying on sha256 only (as host.py) avoids it.
- Info `execution.py:622`: key hash + byte compare per call, linear in blob size, small vs 0.7 s parse.

Not verified (reviewer): memory/speed on a real CP-1 blob; heavy earnings tests; full suite;
threaded concurrent `result` (lru_cache may parse twice in a race); ruff/mypy (relied on report).
