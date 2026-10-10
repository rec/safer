"""Static caller examples. Checked by ty, not executed as tests."""

import io
import socket
from collections.abc import Callable

import safer


def contracts(destination: socket.socket) -> None:
    with safer.open('text', 'w') as text:
        count: int = text.write('text')
        text_value: str = text.read()
        assert count == len(text_value)
        text.safer_failed = True
    with safer.open('binary', 'wb') as binary:
        binary_value: bytes = binary.read()
        binary.write(b'bytes')
    with safer.writer(io.BytesIO()) as binary:
        binary_value = binary.read()
        assert binary_value == b''
    values: list[str] = []
    with safer.writer(values.append) as text:
        text_value = text.read()
        assert text_value == ''
    with safer.writer(destination) as buffered_socket:
        buffered_socket.send(b'bytes')
        buffered_socket.safer_failed = True
    callback = values.append
    native: Callable[[str], None] = safer.writer(callback, enabled=False)
    native('text')
