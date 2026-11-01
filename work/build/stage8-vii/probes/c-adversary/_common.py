"""Shared probe helpers: load item 82's absent_input_limitation from branch claude/s7-absent-input-2."""
import importlib.util
import pathlib

HERE = pathlib.Path(__file__).parent


def item82():
    spec = importlib.util.spec_from_file_location("ca82", HERE / "ca82.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
