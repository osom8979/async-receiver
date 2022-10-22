# -*- coding: utf-8 -*-

import os
import sys
from functools import lru_cache
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase, main

from async_receiver.subprocess.async_virtual_environment import AsyncVirtualEnvironment


@lru_cache
def detect_pydevd() -> bool:
    return "PYDEVD_LOAD_VALUES_ASYNC" in os.environ


@lru_cache
def get_isolate_ensure_pip_flag() -> bool:
    """
    .. warning::
        If pydevd is connected,
        the ``python -Im ensure_pip`` command does not work properly.
    """
    return not detect_pydevd()


def is_executable_file(path: str) -> bool:
    if not os.path.isfile(path):
        return False
    if not os.access(path, os.X_OK):
        return False
    return True


class AsyncVirtualEnvironmentTestCase(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = TemporaryDirectory()
        self.venv = AsyncVirtualEnvironment(
            self.temp_dir.name,
            isolate_ensure_pip=get_isolate_ensure_pip_flag(),
        )
        await self.venv.create_if_not_exists()

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def test_default(self):
        self.assertTrue(self.venv.context)
        self.assertTrue(self.venv.bin_name)
        self.assertTrue(self.venv.bin_path)
        self.assertTrue(self.venv.env_dir)
        self.assertTrue(self.venv.env_exe)
        self.assertTrue(self.venv.env_name)
        self.assertTrue(self.venv.executable)
        self.assertTrue(self.venv.inc_path)
        self.assertTrue(self.venv.prompt)
        self.assertTrue(self.venv.python_dir)
        self.assertTrue(self.venv.python_exe)
        self.assertTrue(self.venv.pip_exe)
        self.assertTrue(self.venv.site_packages_dir)

        print("context", self.venv.context)
        print("bin_name", self.venv.bin_name)
        print("bin_path", self.venv.bin_path)
        print("env_dir", self.venv.env_dir)
        print("env_exe", self.venv.env_exe)
        print("env_name", self.venv.env_name)
        print("executable", self.venv.executable)
        print("inc_path", self.venv.inc_path)
        print("prompt", self.venv.prompt)
        print("python_dir", self.venv.python_dir)
        print("python_exe", self.venv.python_exe)
        print("pip_exe", self.venv.pip_exe)
        print("site_packages_dir", self.venv.site_packages_dir)

    async def test_version_tuple(self):
        python = self.venv.create_python_subprocess()
        version = await python.version_tuple()
        self.assertEqual(sys.version_info[:3], version)

    async def test_executables(self):
        self.assertTrue(is_executable_file(self.venv.env_exe))
        self.assertTrue(is_executable_file(self.venv.pip_exe))

    async def test_pip_list(self):
        python = self.venv.create_python_subprocess()
        packages = await python.list()
        package_names = set(map(lambda x: x.name, packages))
        self.assertSetEqual({"pip", "setuptools"}, package_names)


if __name__ == "__main__":
    main()
