"""The binding maps that ship with the product; ``render`` builds the Front Page from these."""

from deploy_vii.bindings import BindingMap
from deploy_vii.bindings.cp0 import CP0
from deploy_vii.bindings.cp1 import CP1
from deploy_vii.bindings.cp1a import CP1A
from deploy_vii.bindings.cp1b import CP1B
from deploy_vii.bindings.cp1c import CP1C
from deploy_vii.bindings.cp1d import CP1D
from deploy_vii.bindings.cp2 import CP2
from deploy_vii.bindings.cp2a import CP2A
from deploy_vii.bindings.cp2d import CP2D
from deploy_vii.bindings.cp2e import CP2E
from deploy_vii.bindings.cp2g import CP2G
from deploy_vii.bindings.cp2h import CP2H
from deploy_vii.bindings.cp3 import CP3
from deploy_vii.bindings.cp3c import CP3C
from deploy_vii.bindings.cp3d import CP3D
from deploy_vii.bindings.cp4 import CP4
from deploy_vii.bindings.cp5 import CP5
from deploy_vii.bindings.cp6 import CP6
from deploy_vii.bindings.cp8 import CP8
from deploy_vii.bindings.cp_model import CP_MODEL
from deploy_vii.bindings.cpdr import CPDR
from deploy_vii.bindings.cpl10 import CPL10

# Task 8.6: CP-2, CP-4, CP-3 and CP-5 in registry order after CP-1A; task 8.7: CP-6 after CP-5;
# CP-3D (owner-only, docs/CP3D-OWNER-LEASE.md) directly after CP-3.
# CP-DR (lease D-C) is appended last: rails only, no Front Page block.
# Stage 2: CP-2E (rails only, no block) appends at the end.
# CP-8 (owner core, Stage 2) is appended last.
# Stage 2: CP-2A appended last (CP2A lease: SHIPPED_MAPS += CP2A).
# CP-2D directly after CP-2 (docs/CP2D-OWNER-LEASE.md).
# CP-L10 appended last (docs/CPL10-OWNER-LEASE.md).
# CP-1D appended last (docs/CP1D-OWNER-LEASE.md names no position).
# CP-2G appended last (docs/CP2G-OWNER-LEASE.md: SHIPPED_MAPS += CP2G).
# CP-1C appended last (docs/CP1C-OWNER-LEASE.md names no position).
# CP-3C directly after CP-2D, whose head it consumes (docs/CP3C-OWNER-LEASE.md).
# CP-2H appended last (docs/CP2H-OWNER-LEASE.md: SHIPPED_MAPS += CP2H).
SHIPPED_MAPS: tuple[BindingMap, ...] = (
    CP0,
    CP1,
    CP1B,
    CP_MODEL,
    CP1A,
    CP2,
    CP2D,
    CP3C,
    CP4,
    CP3,
    CP3D,
    CP5,
    CP6,
    CPDR,
    CP2E,
    CP8,
    CP2A,
    CPL10,
    CP1D,
    CP2G,
    CP1C,
    CP2H,
)
