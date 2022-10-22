# -*- coding: utf-8 -*-

from collections import deque
from sys import executable, version_info
from unittest import IsolatedAsyncioTestCase, main

from async_receiver.aio.async_subprocess import start_async_subprocess


class AsyncSubprocessTestCase(IsolatedAsyncioTestCase):
    async def test_default(self):
        stdout_deque = deque()
        stderr_deque = deque()

        def _stdout(data: bytes) -> None:
            line = str(data, encoding="utf-8").strip()
            if line:
                stdout_deque.append(line)

        def _stderr(data: bytes) -> None:
            line = str(data, encoding="utf-8").strip()
            if line:
                stderr_deque.append(line)

        proc = await start_async_subprocess(
            executable,
            "--version",
            stdout_callback=_stdout,
            stderr_callback=_stderr,
        )
        version_text = f"{version_info[0]}.{version_info[1]}.{version_info[2]}"
        self.assertEqual(0, await proc.wait())
        self.assertEqual(1, len(stdout_deque))
        self.assertEqual(f"Python {version_text}", stdout_deque.popleft())
        self.assertEqual(0, len(stderr_deque))


if __name__ == "__main__":
    main()
