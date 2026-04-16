import importlib.util
import os
import sys


def load_local_module(file_name: str, alias: str):
    """Load a sibling Python file (with arbitrary filename) as a module alias."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, file_name)

    if alias in sys.modules:
        return sys.modules[alias]

    spec = importlib.util.spec_from_file_location(alias, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {file_name}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module
