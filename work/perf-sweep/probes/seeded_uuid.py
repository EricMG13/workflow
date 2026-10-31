"""pytest plugin for byte-identity runs only: replace uuid.uuid4 with a counter.

Loaded before collection (`PYTHONPATH=<this dir> PYTEST_ADDOPTS="-p seeded_uuid"`, with
PYTHONHASHSEED=0), so every `from uuid import uuid4` binds the counter. uuid4 is the code's only
randomness (no clocks); two runs of the same code then write byte-identical stores.
"""

import itertools
import uuid

_ids = itertools.count(1)
uuid.uuid4 = lambda: uuid.UUID(int=next(_ids), version=4)
