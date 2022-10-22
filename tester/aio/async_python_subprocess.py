# -*- coding: utf-8 -*-

import os
from sys import executable, version_info
from unittest import IsolatedAsyncioTestCase, main

from async_receiver.aio.async_python_subprocess import AsyncPythonSubprocess


class AsyncPythonSubprocessTestCase(IsolatedAsyncioTestCase):
    async def test_version_tuple(self):
        python = AsyncPythonSubprocess(executable)
        version = await python.version_tuple()
        self.assertEqual(version_info[:3], version)

    async def test_list(self):
        print("test_list cwd: ", os.getcwd())
        python = AsyncPythonSubprocess(executable)
        packages = await python.list()
        self.assertLess(0, len(packages))

    async def test_show(self):
        python = AsyncPythonSubprocess(executable)
        show = await python.show("setuptools")
        self.assertLess(0, len(show))
        self.assertEqual("setuptools", show["Name"])

    async def test_show_as_info(self):
        python = AsyncPythonSubprocess(executable)
        show = await python.show_as_info("setuptools")
        self.assertEqual("setuptools", show.name)


if __name__ == "__main__":
    main()
