import json
import os
import socket
import sys
import time
from threading import Thread
from typing import Optional

MAGIC = "2kd94ba0"
PORT = 32160
TIMEOUT = 0.2
DEBUG = True


class Logger:
    def log(self, msg: str) -> None:
        if DEBUG:
            print(f'REMOTE - {self.__class__.__name__:12} - {msg}')


class Advertiser(Thread, Logger):
    def __init__(self, s: 'Server'):
        super().__init__()
        self.log('Init')
        self.server = s
        self._enabled = True

    def enable(self) -> None:
        self.log('Enabled')
        self._enabled = True

    def disable(self) -> None:
        self.log('Disabled')
        self._enabled = False

    def run(self) -> None:
        self.log('Start')
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        while not self.server.quit:
            if self._enabled:
                data = f'{MAGIC}{socket.gethostname()}'
                s.sendto(data.encode(), ('<broadcast>', PORT))
            time.sleep(1)
        self.log('Done')


def osd_message(message: str) -> str:
    data = {
        'command': ['show-text', message]
    }
    return json.dumps(data) + '\n'


def playback_time() -> str:
    data = {
        'command': ["get_property", "playback-time"]
    }
    return json.dumps(data) + '\n'


def chapter_metadata() -> str:
    data = {
        'command': ["get_property", "chapters"]
    }
    return json.dumps(data) + '\n'


class Receiver(Thread, Logger):
    def __init__(self, s: 'Server'):
        super().__init__()
        self.log('Init')
        self.server = s

    def run(self) -> None:
        self.log('Start')
        while not self.server.quit:
            try:
                data = self.server.connection.recv(4096)
                if not data:
                    self.log('Connection to remote closed')
                    self.server.connection.close()
                    return
                message = osd_message(data.decode())
            except socket.timeout:
                if self.server.ipc_socket.fileno() == -1:
                    self.log('ipc_socket closed')
                    # self.server.quit = True
                    return
                continue
            except socket.error:
                self.log('Connection to remote closed')
                self.server.connection.close()
                return
            try:
                self.server.ipc_socket.send(message.encode())
            except socket.error:
                self.log('ipc_socket closed')
                self.server.ipc_socket.close()
                # self.server.quit = True
                return


class Sender(Thread, Logger):
    def __init__(self, s: 'Server'):
        super().__init__()
        self.log('Init')
        self.server = s

    def run(self) -> None:
        self.log('Start')
        while not self.server.quit:
            try:
                data = self.server.ipc_socket.recv(4096)
                if not data:
                    self.log('ipc socket closed')
                    self.server.ipc_socket.close()
                    # self.server.quit = True
                    return
                self.log(data.decode())
            except socket.timeout:
                if self.server.connection.fileno() == -1:
                    self.log('Connection to remote closed')
                    return
                continue
            except socket.error:
                self.log('ipc_socket closed')
                self.server.ipc_socket.close()
                # self.server.quit = True
                return

            try:
                self.server.connection.send(data)
            except socket.error:
                self.log('Connection to remote closed')
                self.server.connection.close()
                return


class Server(Logger):
    def __init__(self, ipc_socket_path: str):
        self.log('Init')
        self.ipc_socket_path = ipc_socket_path
        self.ipc_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.ipc_socket.connect(ipc_socket_path)
        self.ipc_socket.settimeout(TIMEOUT)

        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(('', PORT))
        self.listener.settimeout(TIMEOUT)

        self.connection = None  # type: Optional[socket.socket]
        self.address = None

        self.advertiser = Advertiser(self)
        self.sender = None
        self.receiver = None

        self.quit = False

    def run(self):
        self.log('Start')
        self.advertiser.start()

        while not self.quit:
            self.log('Start listening')
            self.advertiser.enable()
            self.listener.listen()

            while True:
                try:
                    self.connection, self.address = self.listener.accept()
                    break
                except socket.timeout:
                    pass
                try:
                    data = self.ipc_socket.recv(4096)
                    if not data:
                        self.log('ipc_socket closed')
                        self.quit = True
                        break
                except socket.timeout:
                    pass
                except socket.error:
                    self.log('ipc_socket closed')
                    self.quit = True
                    break
            if self.quit:
                break
                
            self.advertiser.disable()
            self.connection.settimeout(TIMEOUT)
            self.log(f'Connected to {self.address}')

            self.sender = Sender(self)
            self.sender.start()

            self.receiver = Receiver(self)
            self.receiver.start()

            self.sender.join()
            self.receiver.join()
            self.connection.close()

            if self.ipc_socket.fileno() == -1:
                self.log('ipc_socket closed')
                self.quit = True
                break

        self.advertiser.join()
        self.listener.close()

        if os.path.exists(self.ipc_socket_path):
            os.remove(self.ipc_socket_path)
            self.log('Manually deleted ipc socket file')

        self.log('Server closed, goodbye :)')


if __name__ == '__main__':
    server = Server(sys.argv[1])
    server.run()
