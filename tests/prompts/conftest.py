from pathlib import Path

import pytest
from prompt_support import make_pack

from deploy_vii.preparation import PreparedPack


@pytest.fixture(scope="session")
def pack(tmp_path_factory: pytest.TempPathFactory) -> PreparedPack:
    return make_pack(tmp_path_factory.mktemp("o6-pack"))


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path
