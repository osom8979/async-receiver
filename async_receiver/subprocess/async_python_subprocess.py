# -*- coding: utf-8 -*-

import sys
from dataclasses import dataclass
from functools import reduce
from json import loads
from typing import Dict, List, Mapping, Optional, Tuple

from async_receiver.subprocess.async_subprocess import (
    AsyncSubprocess,
    ReaderCallable,
    ReaderMethod,
    SubprocessMethod,
    start_async_subprocess,
)

PROGRESS_BAR_STYLE_OFF = "off"
PROGRESS_BAR_STYLE_ASCII = "ascii"
"""
.. deprecated:: pip 22.1
    Custom progress bar styles are deprecated pip 22.1
    will enforce this behaviour change.
"""

DEFAULT_PROGRESS_BAR_STYLE = PROGRESS_BAR_STYLE_OFF
PROGRESS_BAR_STYLE_FLAG = f"--progress-bar={DEFAULT_PROGRESS_BAR_STYLE}"


class Package(object):

    __slots__ = ("name", "version")

    name: str
    version: str

    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version

    def __str__(self) -> str:
        return f"{self.name}=={self.version}"

    def __repr__(self) -> str:
        return f"Package<name={self.name},version={self.version}>"


@dataclass
class PackageInfo:
    name: str
    version: str
    summary: str
    homepage: str
    author: str
    author_email: str
    license: str
    location: str
    requires: List[str]
    required_by: List[str]


class AsyncPythonSubprocess:
    def __init__(
        self,
        executable=sys.executable,
        pip_timeout=0.0,
        env: Optional[Mapping[str, str]] = None,
        method=SubprocessMethod.Exec,
    ):
        self.executable = executable
        self.pip_timeout = pip_timeout
        self.env = env
        self.method = method

    async def start_python(
        self,
        *subcommands,
        cwd: Optional[str] = None,
        writable=False,
        stdout_callback: Optional[ReaderCallable] = None,
        stderr_callback: Optional[ReaderCallable] = None,
        stdout_reader_method=ReaderMethod.ReadLine,
        stderr_reader_method=ReaderMethod.ReadLine,
        stdout_chunk_size=-1,
        stderr_chunk_size=-1,
        stdout_separator=b"\n",
        stderr_separator=b"\n",
    ) -> AsyncSubprocess:
        if not subcommands:
            ValueError("Empty subcommands arguments")

        total_commands = [self.executable, *subcommands]
        proc = await start_async_subprocess(
            *total_commands,
            cwd=cwd,
            env=self.env,
            writable=writable,
            method=self.method,
            stdout_callback=stdout_callback,
            stderr_callback=stderr_callback,
            stdout_reader_method=stdout_reader_method,
            stderr_reader_method=stderr_reader_method,
            stdout_chunk_size=stdout_chunk_size,
            stderr_chunk_size=stderr_chunk_size,
            stdout_separator=stdout_separator,
            stderr_separator=stderr_separator,
        )
        return proc

    def make_pip_subcommands(self, *subcommands) -> List[str]:
        result = [
            "-m",
            "pip",
            "--no-color",
            "--no-input",
            "--disable-pip-version-check",
            "--no-python-version-warning",
        ]
        if self.pip_timeout > 0.0:
            result.append("--timeout={self.pip_timeout}")
        if subcommands:
            result += subcommands
        return result

    async def start_pip(
        self,
        *subcommands,
        stdout_callback: Optional[ReaderCallable] = None,
        stderr_callback: Optional[ReaderCallable] = None,
        cwd: Optional[str] = None,
        writable=False,
    ) -> AsyncSubprocess:
        return await self.start_python(
            *self.make_pip_subcommands(*subcommands),
            cwd=cwd,
            writable=writable,
            stdout_callback=stdout_callback,
            stderr_callback=stderr_callback,
        )

    async def start_python_simply(self, *subcommands) -> Tuple[List[str], List[str]]:
        stdout_lines: List[str] = list()
        stderr_lines: List[str] = list()

        def _stdout_callback(data: bytes) -> None:
            line = str(data, encoding="utf-8").strip()
            if line:
                stdout_lines.append(line)

        def _stderr_callback(data: bytes) -> None:
            line = str(data, encoding="utf-8").strip()
            if line:
                stderr_lines.append(line)

        proc = await self.start_python(
            *subcommands,
            cwd=None,
            writable=False,
            stdout_callback=_stdout_callback,
            stderr_callback=_stderr_callback,
        )
        exit_code = await proc.wait()

        if exit_code != 0:
            params_msg = f"code={exit_code}"
            if stdout_lines:
                stdout_text = reduce(lambda x, y: f"{x} {y}", stdout_lines)
                params_msg += f",stdout={stdout_text}"
            if stderr_lines:
                stderr_text = reduce(lambda x, y: f"{x} {y}", stderr_lines)
                params_msg += f",stderr={stderr_text}"
            error_msg = f"python {subcommands[0]} error: {params_msg}"
            raise RuntimeError(error_msg)

        return stdout_lines, stderr_lines

    async def start_pip_simply(self, *subcommands) -> Tuple[List[str], List[str]]:
        return await self.start_python_simply(*self.make_pip_subcommands(*subcommands))

    # noinspection SpellCheckingInspection
    async def ensure_pip(self, isolate=True) -> Tuple[List[str], List[str]]:
        """
        Run ``ensure_pip`` module.

        :param isolate:
            If pydevd is connected, the ``python -Im ensure_pip`` command does not work
            properly. In this case, it is temporarily resolved by using the ``isolate``
            flag as ``False``. If possible, use only for debugging and testing purposes.
        """

        return await self.start_python_simply(
            "-Im" if isolate else "-m",
            "ensurepip",
            "--upgrade",
            "--default-pip",
        )

    async def recc_version(self) -> str:
        stdout_lines, _ = await self.start_python_simply("-m", "recc", "--version")
        assert len(stdout_lines) == 1
        return stdout_lines[0].strip()

    async def version(self) -> str:
        stdout_lines, _ = await self.start_python_simply("--version")
        assert len(stdout_lines) == 1
        prefix, version = stdout_lines[0].split(" ", 1)
        assert prefix == "Python"
        return version

    async def version_tuple(self) -> Tuple[int, int, int]:
        versions = [int(i) for i in (await self.version()).split(".")]
        assert len(versions) == 3
        return versions[0], versions[1], versions[2]

    async def download(
        self,
        package: str,
        destination: str,
        stdout_callback: Optional[ReaderCallable] = None,
        stderr_callback: Optional[ReaderCallable] = None,
    ) -> int:
        proc = await self.start_pip(
            "download",
            "--dest",
            destination,
            PROGRESS_BAR_STYLE_FLAG,
            package,
            stdout_callback=stdout_callback,
            stderr_callback=stderr_callback,
        )
        return await proc.wait()

    async def install(
        self,
        package: str,
        stdout_callback: Optional[ReaderCallable] = None,
        stderr_callback: Optional[ReaderCallable] = None,
    ) -> int:
        proc = await self.start_pip(
            "install",
            PROGRESS_BAR_STYLE_FLAG,
            package,
            stdout_callback=stdout_callback,
            stderr_callback=stderr_callback,
        )
        return await proc.wait()

    async def upgrade(
        self,
        package: str,
        stdout_callback: Optional[ReaderCallable] = None,
        stderr_callback: Optional[ReaderCallable] = None,
    ) -> int:
        proc = await self.start_pip(
            "install",
            PROGRESS_BAR_STYLE_FLAG,
            "--upgrade",
            package,
            stdout_callback=stdout_callback,
            stderr_callback=stderr_callback,
        )
        return await proc.wait()

    async def uninstall(
        self,
        package: str,
        stdout_callback: Optional[ReaderCallable] = None,
        stderr_callback: Optional[ReaderCallable] = None,
    ) -> int:
        proc = await self.start_pip(
            "uninstall",
            "--yes",
            package,
            stdout_callback=stdout_callback,
            stderr_callback=stderr_callback,
        )
        return await proc.wait()

    async def list(self) -> List[Package]:
        stdout_lines, _ = await self.start_pip_simply("list", "--format=json")
        json_text = reduce(lambda x, y: f"{x}{y}", stdout_lines)
        packages = loads(json_text)
        return [Package(p["name"], p["version"]) for p in packages]

    async def show(self, package: str) -> Dict[str, str]:
        stdout_lines, _ = await self.start_pip_simply("show", package)
        result = dict()
        for header_line in stdout_lines:
            # The output is in RFC-compliant mail header format.
            items = header_line.split(":", maxsplit=1)
            assert len(items) == 2
            key = items[0].strip()
            val = items[1].strip()
            result[key] = val
        return result

    async def show_as_info(self, package: str) -> PackageInfo:
        info = await self.show(package)

        def _split_packages(text: str) -> List[str]:
            return list(
                filter(
                    lambda x: bool(x),
                    map(
                        lambda x: x.strip(),
                        text.split(","),
                    ),
                )
            )

        name = info.get("Name", "").strip()
        version = info.get("Version", "").strip()
        summary = info.get("Summary", "").strip()
        homepage = info.get("Home-page", "").strip()
        author = info.get("Author", "").strip()
        author_email = info.get("Author-email", "").strip()
        license_ = info.get("License", "").strip()  # Shadows built-in name 'license'
        location = info.get("Location", "").strip()
        requires = _split_packages(info.get("Requires", ""))
        required_by = _split_packages(info.get("Required-by", ""))

        return PackageInfo(
            name,
            version,
            summary,
            homepage,
            author,
            author_email,
            license_,
            location,
            requires,
            required_by,
        )
