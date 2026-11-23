import re
from pathlib import Path

import pytest

from kiku_sidecar.lifecycle import load_plugins

README = Path(__file__).parents[2] / "docs/hooks.md"
BLOCKS = re.findall(r"```python\n(.*?)```", README.read_text(), re.DOTALL)


def test_readme_has_examples():
    assert len(BLOCKS) == 10


@pytest.mark.parametrize("source", BLOCKS)
def test_example_is_a_hook_file_with_a_plugin(tmp_path: Path, source: str):
    (tmp_path / "example.py").write_text(source)
    assert load_plugins(tmp_path)
