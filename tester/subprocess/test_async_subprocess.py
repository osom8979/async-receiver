# -*- coding: utf-8 -*-

from collections import deque
from functools import partial
from sys import executable, version_info
from typing import List
from unittest import IsolatedAsyncioTestCase, main

from async_receiver.subprocess.async_subprocess import start_async_subprocess


class AsyncSubprocessTestCase(IsolatedAsyncioTestCase):
    async def run_python_version(self, callback) -> str:
        stdout_deque: List[str] = list()
        stderr_deque: List[str] = list()
        proc = await start_async_subprocess(
            executable,
            "--version",
            stdout_callback=partial(callback, stdout_deque),
            stderr_callback=partial(callback, stderr_deque),
        )
        self.assertEqual(0, await proc.wait())
        self.assertTrue(proc.done_stdout())
        self.assertTrue(proc.done_stderr())
        self.assertEqual(1, len(stdout_deque))
        self.assertEqual(0, len(stderr_deque))
        return stdout_deque[0]

    async def test_sync_callback(self):
        version_text = f"{version_info[0]}.{version_info[1]}.{version_info[2]}"
        expected_python_version = f"Python {version_text}"

        def sync_reader(buffer: deque, data: bytes) -> None:
            line = str(data, encoding="utf-8").strip()
            if line:
                buffer.append(line)

        result = await self.run_python_version(sync_reader)
        self.assertEqual(expected_python_version, result)

    async def test_async_callback(self):
        version_text = f"{version_info[0]}.{version_info[1]}.{version_info[2]}"
        expected_python_version = f"Python {version_text}"

        async def async_reader(buffer: deque, data: bytes) -> None:
            line = str(data, encoding="utf-8").strip()
            if line:
                buffer.append(line)

        result = await self.run_python_version(async_reader)
        self.assertEqual(expected_python_version, result)


if __name__ == "__main__":
    main()
