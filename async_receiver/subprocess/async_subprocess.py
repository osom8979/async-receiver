# -*- coding: utf-8 -*-

from asyncio import (
    Task,
    create_subprocess_exec,
    create_subprocess_shell,
    create_task,
    gather,
    subprocess,
)
from asyncio.streams import StreamReader, StreamWriter
from dataclasses import dataclass
from enum import Enum, unique
from functools import reduce
from inspect import iscoroutinefunction
from io import BytesIO
from signal import SIGINT
from typing import Awaitable, Callable, Dict, Final, Mapping, Optional, Tuple, Union

import psutil

ReaderCallable = Callable[[bytes], Union[Awaitable[None], None]]


@unique
class SubprocessMethod(Enum):
    Exec = 0
    Shell = 1


@unique
class ReaderMethod(Enum):
    Read = 0
    ReadLine = 1
    ReadUntil = 2
    ReadExactly = 3


@unique
class ProcessStatus(Enum):
    Running = 0
    Sleeping = 1
    DiskSleep = 2
    Stopped = 3
    TracingStop = 4
    Zombie = 5
    Dead = 6
    WakeKill = 7
    Waking = 8
    Parked = 9
    Idle = 10
    Locked = 11
    Waiting = 12
    Suspended = 13


STATUS_RUNNING: Final[str] = "running"
STATUS_SLEEPING: Final[str] = "sleeping"
STATUS_DISK_SLEEP: Final[str] = "disk-sleep"
STATUS_STOPPED: Final[str] = "stopped"
STATUS_TRACING_STOP: Final[str] = "tracing-stop"
STATUS_ZOMBIE: Final[str] = "zombie"
STATUS_DEAD: Final[str] = "dead"
STATUS_WAKE_KILL: Final[str] = "wake-kill"
STATUS_WAKING: Final[str] = "waking"
STATUS_IDLE: Final[str] = "idle"  # Linux, macOS, FreeBSD
STATUS_LOCKED: Final[str] = "locked"  # FreeBSD
STATUS_WAITING: Final[str] = "waiting"  # FreeBSD
STATUS_SUSPENDED: Final[str] = "suspended"  # NetBSD
STATUS_PARKED: Final[str] = "parked"  # Linux

PROCESS_STATUS_MAP: Final[Dict[str, ProcessStatus]] = {
    STATUS_RUNNING: ProcessStatus.Running,
    STATUS_SLEEPING: ProcessStatus.Sleeping,
    STATUS_DISK_SLEEP: ProcessStatus.DiskSleep,
    STATUS_STOPPED: ProcessStatus.Stopped,
    STATUS_TRACING_STOP: ProcessStatus.TracingStop,
    STATUS_ZOMBIE: ProcessStatus.Zombie,
    STATUS_DEAD: ProcessStatus.Dead,
    STATUS_WAKE_KILL: ProcessStatus.WakeKill,
    STATUS_WAKING: ProcessStatus.Waking,
    STATUS_PARKED: ProcessStatus.Parked,
    STATUS_IDLE: ProcessStatus.Idle,
    STATUS_LOCKED: ProcessStatus.Locked,
    STATUS_WAITING: ProcessStatus.Waiting,
    STATUS_SUSPENDED: ProcessStatus.Suspended,
}


@dataclass
class ReaderConfig:
    callback: Optional[ReaderCallable] = None
    reader_method: ReaderMethod = ReaderMethod.ReadLine
    chunk_size: int = -1
    separator: bytes = b"\n"


class AsyncSubprocess:
    def __init__(
        self,
        *commands,
        cwd: Optional[str] = None,
        env: Optional[Mapping[str, str]] = None,
        writable=False,
        method=SubprocessMethod.Exec,
        stdout_callback: Optional[ReaderCallable] = None,
        stderr_callback: Optional[ReaderCallable] = None,
        stdout_reader_method=ReaderMethod.ReadLine,
        stderr_reader_method=ReaderMethod.ReadLine,
        stdout_chunk_size=-1,
        stderr_chunk_size=-1,
        stdout_separator=b"\n",
        stderr_separator=b"\n",
    ):
        self._commands = commands
        self._cwd = cwd
        self._env = env
        self._writable = writable
        self._method = method

        self._stdout_config = ReaderConfig(
            callback=stdout_callback,
            reader_method=stdout_reader_method,
            chunk_size=stdout_chunk_size,
            separator=stdout_separator,
        )
        self._stderr_config = ReaderConfig(
            callback=stderr_callback,
            reader_method=stderr_reader_method,
            chunk_size=stderr_chunk_size,
            separator=stderr_separator,
        )

        self._process: Optional[subprocess.Process] = None
        self._stdout_task: Optional[Task] = None
        self._stderr_task: Optional[Task] = None

    @staticmethod
    async def _reader(reader: StreamReader, config: ReaderConfig) -> None:
        assert config.callback is not None
        while not reader.at_eof():
            if config.reader_method == ReaderMethod.Read:
                data = await reader.read(config.chunk_size)
            elif config.reader_method == ReaderMethod.ReadLine:
                data = await reader.readline()
            elif config.reader_method == ReaderMethod.ReadUntil:
                data = await reader.readuntil(config.separator)
            elif config.reader_method == ReaderMethod.ReadExactly:
                data = await reader.readexactly(config.chunk_size)
            else:
                assert False, "Inaccessible section"

            if iscoroutinefunction(config.callback):
                await config.callback(data)
            else:
                config.callback(data)

    @property
    def started(self) -> bool:
        return self._process is not None

    @property
    def stdin_flag(self) -> Optional[int]:
        return subprocess.PIPE if self._writable else None

    @property
    def stdout_flag(self) -> Optional[int]:
        return subprocess.PIPE if self._stdout_config.callback else None

    @property
    def stderr_flag(self) -> Optional[int]:
        return subprocess.PIPE if self._stderr_config.callback else None

    async def _create_subprocess_exec(self):
        """
        DeprecationWarning:
        The `loop` argument is deprecated since Python 3.8
        and scheduled for removal in Python 3.10
        """
        return await create_subprocess_exec(
            self._commands[0],
            *self._commands[1:],
            stdin=self.stdin_flag,
            stdout=self.stdout_flag,
            stderr=self.stderr_flag,
            executable=None,
            cwd=self._cwd,
            env=self._env,
        )

    async def _create_subprocess_shell(self) -> subprocess.Process:
        total_commands = [f"'{str(c).strip()}'" for c in self._commands]
        merged_commands = reduce(lambda x, y: f"{x} {y}", total_commands[1:])

        """
        DeprecationWarning:
        The `loop` argument is deprecated since Python 3.8
        and scheduled for removal in Python 3.10
        """
        return await create_subprocess_shell(
            merged_commands,
            stdin=self.stdin_flag,
            stdout=self.stdout_flag,
            stderr=self.stderr_flag,
            executable=None,
            cwd=self._cwd,
            env=self._env,
        )

    async def create_subprocess(self) -> subprocess.Process:
        if self._method == SubprocessMethod.Exec:
            return await self._create_subprocess_exec()
        elif self._method == SubprocessMethod.Shell:
            return await self._create_subprocess_shell()
        else:
            raise NotImplementedError

    async def start(self) -> None:
        if self._process is not None:
            raise RuntimeError("Already started process")

        self._process = await self.create_subprocess()

        if self.stdout_flag:
            assert self._process.stdout is not None
            assert self._stdout_config.callback is not None
            self._stdout_task = create_task(
                self._reader(self._process.stdout, self._stdout_config)
            )

        if self.stderr_flag:
            assert self._process.stderr is not None
            assert self._stderr_config.callback is not None
            self._stderr_task = create_task(
                self._reader(self._process.stderr, self._stderr_config)
            )

    @property
    def process(self) -> subprocess.Process:
        if not self._process:
            raise RuntimeError("Process is not started")
        return self._process

    @property
    def pid(self) -> int:
        return self.process.pid

    @property
    def stdin(self) -> StreamWriter:
        if not self._writable:
            raise RuntimeError("The writable flag is disabled")
        assert self.process.stdin
        return self.process.stdin

    def write(self, data: bytes) -> None:
        self.stdin.write(data)

    def writelines(self, data) -> None:
        self.stdin.writelines(data)

    def write_eof(self) -> None:
        self.stdin.write_eof()

    def can_write_eof(self) -> bool:
        return self.stdin.can_write_eof()

    def close_stdin(self) -> None:
        self.stdin.close()

    def is_closing_stdin(self) -> bool:
        return self.stdin.is_closing()

    def done_stdout(self) -> bool:
        assert self._stdout_task
        return self._stdout_task.done()

    def done_stderr(self) -> bool:
        assert self._stderr_task
        return self._stderr_task.done()

    async def wait_closed_stdin(self) -> None:
        await self.stdin.wait_closed()

    async def drain_stdin(self) -> None:
        await self.stdin.drain()

    async def wait_process(self) -> int:
        return await self.process.wait()

    async def wait_callbacks(self) -> None:
        futures = list()
        if self._stdout_task:
            futures.append(self._stdout_task)
        if self._stderr_task:
            futures.append(self._stderr_task)
        if futures:
            await gather(*futures)

    async def wait(self) -> int:
        exit_code = await self.wait_process()
        await self.wait_callbacks()
        return exit_code

    def send_signal(self, signal) -> None:
        self.process.send_signal(signal)

    def interrupt(self) -> None:
        self.send_signal(SIGINT)

    def terminate(self) -> None:
        self.process.terminate()

    def kill(self) -> None:
        self.process.kill()

    @property
    def status_text(self) -> str:
        return psutil.Process(self.process.pid).status()

    @property
    def status(self) -> ProcessStatus:
        return PROCESS_STATUS_MAP[self.status_text]


async def start_async_subprocess(
    *commands,
    cwd: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    writable=False,
    method=SubprocessMethod.Exec,
    stdout_callback: Optional[ReaderCallable] = None,
    stderr_callback: Optional[ReaderCallable] = None,
    stdout_reader_method=ReaderMethod.ReadLine,
    stderr_reader_method=ReaderMethod.ReadLine,
    stdout_chunk_size=-1,
    stderr_chunk_size=-1,
    stdout_separator=b"\n",
    stderr_separator=b"\n",
) -> AsyncSubprocess:
    proc = AsyncSubprocess(
        *commands,
        cwd=cwd,
        env=env,
        writable=writable,
        method=method,
        stdout_callback=stdout_callback,
        stderr_callback=stderr_callback,
        stdout_reader_method=stdout_reader_method,
        stderr_reader_method=stderr_reader_method,
        stdout_chunk_size=stdout_chunk_size,
        stderr_chunk_size=stderr_chunk_size,
        stdout_separator=stdout_separator,
        stderr_separator=stderr_separator,
    )
    await proc.start()
    return proc


async def start_async_subprocess_simply(
    *commands,
    cwd: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    method=SubprocessMethod.Exec,
) -> Tuple[int, bytes, bytes]:
    stdout = BytesIO()
    stderr = BytesIO()

    def _stdout_callback(data: bytes) -> None:
        stdout.write(data)

    def _stderr_callback(data: bytes) -> None:
        stderr.write(data)

    proc = await start_async_subprocess(
        *commands,
        cwd=cwd,
        env=env,
        writable=False,
        method=method,
        stdout_callback=_stdout_callback,
        stderr_callback=_stderr_callback,
        stdout_reader_method=ReaderMethod.ReadLine,
        stderr_reader_method=ReaderMethod.ReadLine,
    )
    exit_code = await proc.wait()
    return exit_code, stdout.getvalue(), stderr.getvalue()
