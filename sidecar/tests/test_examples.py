import re
from pathlib import Path

import pytest

from kiku import Plugin
from kiku_sidecar.lifecycle import load_plugins

README = Path(__file__).parents[2] / "docs/hooks.md"
BLOCKS = re.findall(r"```python\n(.*?)```", README.read_text(), re.DOTALL)
HOOKS = ("on_transcribed", "on_cleaned", "on_sent", "on_done", "on_error")


def overrides_a_hook(plugin: Plugin) -> bool:
    """Return whether the class of `plugin` overrides any of the five hooks."""
    plugin_class = type(plugin)
    return any(getattr(plugin_class, hook) is not getattr(Plugin, hook) for hook in HOOKS)


def test_readme_has_examples():
    assert len(BLOCKS) == 10


@pytest.mark.parametrize("source", BLOCKS)
def test_example_is_a_hook_file_with_a_plugin(tmp_path: Path, source: str):
    (tmp_path / "example.py").write_text(source)
    plugins = load_plugins(tmp_path)
    assert any(overrides_a_hook(plugin) for _, plugin in plugins)
