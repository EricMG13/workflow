"""``python -m deploy_workflow.model_testing {pilot|repair|comparison|score|report} ...``"""

from __future__ import annotations

import sys

from deploy_workflow.model_testing.run import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
