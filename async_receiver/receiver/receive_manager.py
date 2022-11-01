# -*- coding: utf-8 -*-

# import os
# from asyncio import QueueFull
# from copy import deepcopy
# from datetime import datetime
# from random import randint
# from typing import Dict, Final, List, Optional
#
# from async_receiver.subprocess.async_python_subprocess import AsyncPythonSubprocess
#
#
# class ReceiveManager:
#     def __init__(
#         self,
#         dummy=False,
#         rs232=False,
#         bluetooth=False,
#         tcp=False,
#         udp=False,
#         sctp=False,
#         http=False,
#         ws=False,
#         grpc=False,
#     ):
#         self._dummy = dummy
#         self._rs232 = rs232
#         self._bluetooth = bluetooth
#         self._tcp = tcp
#         self._udp = udp
#         self._sctp = sctp
#         self._http = http
#         self._ws = ws
#         self._grpc = grpc
#
#         self._modules: Dict[str, ReceiveModule] = dict()
#
#     @staticmethod
#     def discover_dummy() -> List[ReceiveModule]:
#         return []
#
#     @staticmethod
#     def discover_rs232() -> List[ReceiveModule]:
#         return []
#
#     @staticmethod
#     def discover_bluetooth() -> List[ReceiveModule]:
#         return []
#
#     @staticmethod
#     def discover_tcp() -> List[ReceiveModule]:
#         return []
#
#     @staticmethod
#     def discover_udp() -> List[ReceiveModule]:
#         return []
#
#     @staticmethod
#     def discover_sctp() -> List[ReceiveModule]:
#         return []
#
#     @staticmethod
#     def discover_http() -> List[ReceiveModule]:
#         return []
#
#     @staticmethod
#     def discover_ws() -> List[ReceiveModule]:
#         return []
#
#     @staticmethod
#     def discover_grpc() -> List[ReceiveModule]:
#         return []
#
#     def discover(self, dry_run=False) -> List[ReceiveModule]:
#         result = list()
#         if self._dummy:
#             result += ReceiveManager.discover_dummy()
#         if self._rs232:
#             result += ReceiveManager.discover_rs232()
#         if self._bluetooth:
#             result += ReceiveManager.discover_bluetooth()
#         if self._tcp:
#             result += ReceiveManager.discover_tcp()
#         if self._udp:
#             result += ReceiveManager.discover_udp()
#         if self._sctp:
#             result += ReceiveManager.discover_sctp()
#         if self._http:
#             result += ReceiveManager.discover_http()
#         if self._ws:
#             result += ReceiveManager.discover_ws()
#         if self._grpc:
#             result += ReceiveManager.discover_grpc()
#
#         if not dry_run:
#             self._serial_infos = deepcopy(result)
#
#         return result
#
#     async def bluetooth_stdout(self, data: bytes) -> None:
#         # print(f"bluetooth_stdout ~~~~~~~~~~~~~~~~~~~~-> {data}")
#         raws = filter(lambda x: x, data.decode("Latin1").split("\n"))
#         for raw in raws:
#             if raw[0] != "E":  # spec
#                 continue
#             if raw[1:].isdecimal():
#                 value = int(raw[1:])
#             else:
#                 value = -1
#             elem = Vibration(datetime.now().astimezone(), value)
#             try:
#                 self._bluetooth_queue.put_nowait(elem)
#             except QueueFull:
#                 self._bluetooth_queue.get_nowait()
#                 self._bluetooth_queue.put_nowait(elem)
#
#     async def bluetooth_stderr(self, data: bytes) -> None:
#         # print(f"bluetooth_stderr ~~~~~~~~~~~~~~~~~~~~-> {data}")
#         pass
#
#     async def start_bluetooth(self) -> None:
#         # print("start_bluetooth !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
#         info = SerialManager.discover_bluetooth()[0]
#         assert info.name == "HC-06"
#         assert info.port is not None
#         assert self._process is None
#
#         script = os.path.abspath(bluetooth_recv.__file__)
#         python = AsyncPythonSubprocess()
#
#         self._process = await python.start_python(
#             script,
#             info.addr,
#             str(info.port),
#             stdout_callback=self.bluetooth_stdout,
#             stderr_callback=self.bluetooth_stderr,
#         )
#
#     async def close(self) -> None:
#         if self._process is not None:
#             self._process.interrupt()
#             await self._process.wait()
#             self._process = None
#
#     async def latest(self) -> List[State]:
#         vibrations = list()
#         while not self._bluetooth_queue.empty():
#             vibrations.append(self._bluetooth_queue.get_nowait())
#
#         if vibrations:
#             maxvalue = max(map(lambda x: x.value, vibrations))
#         else:
#             maxvalue = 0
#
#         now = datetime.now().astimezone()
#         v0 = Vibration(now, randint(0, 100))
#         v1 = Vibration(now, maxvalue)
#
#         info0 = self.discover_fake()[0]
#         info1 = self.discover_bluetooth()[0]
#
#         return [
#             State(info0.name, "demo", "", [v0]),
#             State(info1.name, "demo", "", [v1]),
#         ]
