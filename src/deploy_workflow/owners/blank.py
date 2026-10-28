"""The one blank-text predicate for analyst text (LEAD round 12 B10).

The predicate itself is `deploy_vii.prose.is_blank`; this module keeps its public name for the
owner cores (`from deploy_workflow.owners.blank import is_blank`).
"""

from deploy_vii.prose import is_blank

__all__ = ["is_blank"]
