import socket

__author__ = 'apostol3'


class TcpStream:
    def __init__(self, host_ip, host_port, buffer_size):
        self.host_ip = host_ip
        self.host_port = host_port
        self.buffer_size = buffer_size

        self.sock = None
        self._is_connected = False

    @property
    def is_connected(self):
        return self._is_connected

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host_ip, self.host_port))
        self._is_connected = True

    def send(self, buf):
        while len(buf) > self.buffer_size:
            part = buf[:self.buffer_size]
            buf = buf[self.buffer_size:]
            self.sock.send(part)

        self.sock.send(buf)

    def receive(self):
        buf_tmp, _ = self.sock.recvfrom(self.buffer_size)
        sz = len(buf_tmp)
        arr = [buf_tmp]
        sz_all = sz
        while sz >= self.buffer_size:
            buf_tmp, _ = self.sock.recvfrom(self.buffer_size)
            sz = len(buf_tmp)
            arr.append(buf_tmp)
            sz_all += sz

        buf = bytes()
        for i in arr:
            buf += i

        return buf

    def disconnect(self):
        self._is_connected = False
        self.sock.close()

    def create(self):
        raise NotImplementedError()

    def wait(self):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()
