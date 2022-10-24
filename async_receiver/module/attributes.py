# -*- coding: utf-8 -*-

import os
from types import ModuleType


def module_directory(module: ModuleType) -> str:
    module_path = getattr(module, "__path__", None)
    if module_path:
        assert isinstance(module_path, list)
        return module_path[0]

    module_file = getattr(module, "__file__", None)
    if module_file:
        assert isinstance(module_file, str)
        return os.path.dirname(module_file)

    module_name = getattr(module, "__name__", "<unknown>")
    raise RuntimeError(f"The '{module_name}' module path is unknown")
