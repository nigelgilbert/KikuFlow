import re
from pathlib import Path

import pytest

from kiku_sidecar.lifecycle import load_hooks

README = Path(__file__).parents[2] / "examples/README.md"
BLOCKS = re.findall(r"```python\n(.*?)```", README.read_text(), re.DOTALL)


def test_readme_has_examples():
    assert len(BLOCKS) == 9


@pytest.mark.parametrize("source", BLOCKS)
def test_example_is_a_working_hook_file(tmp_path: Path, source: str):
    (tmp_path / "example.py").write_text(source)
    assert any(load_hooks(tmp_path).values())
