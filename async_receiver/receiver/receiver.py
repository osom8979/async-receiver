# -*- coding: utf-8 -*-

import os
from asyncio import Queue
from typing import Awaitable, Callable, List, Mapping, Optional, Union

from async_receiver.subprocess.async_subprocess import (
    AsyncSubprocess,
    ReaderMethod,
    SubprocessMethod,
)

ReceiverCallable = Callable[["Receiver", bytes], Union[Awaitable[None], None]]


class Receiver:

    _queue: Optional[Queue[bytes]]
    _process: Optional[AsyncSubprocess]

    def __init__(
        self,
        category: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        address: Optional[str] = None,
        port: Optional[int] = None,
        discover_script: Optional[str] = None,
        receiver_script: Optional[str] = None,
        venv_root: Optional[str] = None,
        venv_requirements: Optional[List[str]] = None,
        venv_requirements_file: Optional[str] = None,
        venv_pip_timeout: Optional[float] = None,
        cwd: Optional[str] = None,
        env: Optional[Mapping[str, str]] = None,
        method=SubprocessMethod.Exec,
        stdout_reader_method=ReaderMethod.ReadLine,
        stderr_reader_method=ReaderMethod.ReadLine,
        stdout_chunk_size=-1,
        stderr_chunk_size=-1,
        stdout_separator=b"\n",
        stderr_separator=b"\n",
        receive_byte=1024,
        receive_duration=1.0,
        data_callback: Optional[ReceiverCallable] = None,
        error_callback: Optional[ReceiverCallable] = None,
        queue_maxsize=1024,
    ):
        if venv_requirements and venv_requirements_file:
            raise ValueError(
                "Arguments 'venv_requirements' and "
                "'venv_requirements_file' cannot coexist"
            )

        self._category = category
        self._name = name
        self._description = description
        self._address = address
        self._port = port
        self._discover_script = discover_script
        self._receiver_script = receiver_script

        self._venv_root = venv_root
        self._venv_requirements = venv_requirements
        self._venv_requirements_file = venv_requirements_file
        self._venv_pip_timeout = venv_pip_timeout

        self._cwd = cwd
        self._env = env
        self._method = method
        self._stdout_reader_method = stdout_reader_method
        self._stderr_reader_method = stderr_reader_method
        self._stdout_chunk_size = stdout_chunk_size
        self._stderr_chunk_size = stderr_chunk_size
        self._stdout_separator = stdout_separator
        self._stderr_separator = stderr_separator

        self._receive_byte = receive_byte
        self._receive_duration = receive_duration

        self._data_callback = data_callback
        self._error_callback = error_callback

        self._queue = Queue(maxsize=queue_maxsize) if queue_maxsize >= 1 else None
        self._process = None

    async def _receiver_stdout(self, data: bytes) -> None:
        if self._queue:
            if self._queue.full():
                self._queue.get_nowait()
            self._queue.put_nowait(data)

        if self._data_callback:
            self._data_callback(self, data)

    async def _receiver_stderr(self, data: bytes) -> None:
        if self._error_callback:
            self._error_callback(self, data)

    async def open(self) -> None:
        if not self._receiver_script:
            raise ValueError("")

        if not os.path.isfile(self._receiver_script):
            raise FileNotFoundError()

        assert isinstance(self._receive_byte, int)
        assert isinstance(self._receive_duration, float)
        assert self._receive_byte >= 1
        assert self._receive_duration >= 0.0

        # python = AsyncPythonSubprocess(
        #     executable=sys.executable,
        #     pip_timeout=self.venv_pip_timeout,
        #     env=env,
        #     method=method,
        # )
        #
        # self._process = await self._python.start_python(
        #     self.receiver_script,
        #     self.address,
        #     str(self.port),
        #     str(self.receive_byte),
        #     str(self.receive_duration),
        #     stdout_callback=self.receiver_stdout,
        #     stderr_callback=self.receiver_stderr,
        #     stdout_reader_method=self.
        # )

    async def close(self, timeout: Optional[float] = None) -> int:
        if timeout is not None and timeout <= 0:
            raise ValueError("The 'timeout' argument must be None or greater than 0")
        if self._process is None:
            raise RuntimeError("Not ready process")
        return await self._process.force_quit(timeout)

    @property
    def queue(self) -> Queue[bytes]:
        if self._queue is None:
            raise RuntimeError("Not ready queue")
        return self._queue

    def is_full(self) -> bool:
        return self.queue.full()

    def is_empty(self) -> bool:
        return self.queue.empty()

    def clear(self) -> None:
        while not self.queue.empty():
            self.queue.get_nowait()

    def pop_nowait(self) -> bytes:
        return self.queue.get_nowait()

    def pop_all_nowait(self) -> List[bytes]:
        result = list()
        while not self.queue.empty():
            result.append(self.queue.get_nowait())
        return result
