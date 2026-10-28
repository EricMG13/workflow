"""The binding maps that ship with the product; ``render`` builds the Front Page from these."""

from deploy_vii.bindings import BindingMap
from deploy_vii.bindings.cp0 import CP0
from deploy_vii.bindings.cp1 import CP1
from deploy_vii.bindings.cp1a import CP1A
from deploy_vii.bindings.cp1b import CP1B
from deploy_vii.bindings.cp2 import CP2
from deploy_vii.bindings.cp2e import CP2E
from deploy_vii.bindings.cp3 import CP3
from deploy_vii.bindings.cp3d import CP3D
from deploy_vii.bindings.cp4 import CP4
from deploy_vii.bindings.cp5 import CP5
from deploy_vii.bindings.cp6 import CP6
from deploy_vii.bindings.cp8 import CP8
from deploy_vii.bindings.cp_model import CP_MODEL
from deploy_vii.bindings.cpdr import CPDR

# Task 8.6: CP-2, CP-4, CP-3 and CP-5 in registry order after CP-1A; task 8.7: CP-6 after CP-5;
# CP-3D (owner-only, docs/CP3D-OWNER-LEASE.md) directly after CP-3.
# CP-DR (lease D-C) is appended last: rails only, no Front Page block.
# Stage 2: CP-2E (rails only, no block) appends at the end.
# CP-8 (owner core, Stage 2) is appended last.
SHIPPED_MAPS: tuple[BindingMap, ...] = (
    CP0,
    CP1,
    CP1B,
    CP_MODEL,
    CP1A,
    CP2,
    CP4,
    CP3,
    CP3D,
    CP5,
    CP6,
    CPDR,
    CP2E,
    CP8,
)
