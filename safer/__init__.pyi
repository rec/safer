"""Public contracts for safer's dynamically wrapped IO objects."""

import io
import os
from pathlib import Path
from types import ModuleType, TracebackType
from typing import (
    Callable,
    ContextManager,
    Iterable,
    Literal,
    Protocol,
    TypeVar,
    overload,
)

T = TypeVar('T', str, bytes)
D = TypeVar('D')

class Destination(Protocol[T]):
    def write(self, value: T, /) -> object: ...

class Socket(Protocol):
    def send(self, value: bytes, /) -> int: ...
    def recv(self, size: int, /) -> bytes: ...
    def close(self) -> None: ...

class _IO(Protocol[T]):
    @property
    def closed(self) -> bool: ...
    def write(self, value: T, /) -> int: ...
    def writelines(self, values: Iterable[T], /) -> None: ...
    def read(self, size: int = -1, /) -> T: ...
    def readline(self, size: int = -1, /) -> T: ...
    def seek(self, offset: int, whence: int = 0, /) -> int: ...
    def tell(self) -> int: ...
    def truncate(self, size: int | None = None, /) -> int: ...
    def flush(self) -> None: ...
    def close(self) -> None: ...
    def __enter__(self) -> _IO[T]: ...
    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None: ...

class SafeIO(_IO[T], Protocol[T]):
    safer_failed: bool
    def __enter__(self) -> SafeIO[T]: ...

class SafeSocketIO(SafeIO[bytes], Protocol):
    def send(self, value: bytes, /) -> int: ...
    def __enter__(self) -> SafeSocketIO: ...

@overload
def writer(
    stream: str | os.PathLike[str],
    is_binary: bool | None = ...,
    close_on_exit: bool = ...,
    temp_file: bool | str | Path = ...,
    chunk_size: int = ...,
    delete_failures: bool = ...,
    dry_run: bool | Callable[[str | bytes], object] = ...,
    *,
    enabled: Literal[False],
) -> ContextManager[Destination[str] | Destination[bytes]]: ...
@overload
def writer(
    stream: D,
    is_binary: bool | None = ...,
    close_on_exit: bool = ...,
    temp_file: bool | str | Path = ...,
    chunk_size: int = ...,
    delete_failures: bool = ...,
    dry_run: bool | Callable[[str | bytes], object] = ...,
    *,
    enabled: Literal[False],
) -> D: ...
@overload
def writer(
    stream: Socket,
    is_binary: Literal[True] | None = ...,
    close_on_exit: bool = ...,
    temp_file: bool | str | Path = ...,
    chunk_size: int = ...,
    delete_failures: bool = ...,
    dry_run: bool | Callable[[bytes], object] = ...,
    enabled: Literal[True] = ...,
) -> SafeSocketIO: ...
@overload
def writer(
    stream: Destination[bytes]
    | Callable[[bytes], object]
    | str
    | os.PathLike[str]
    | None = ...,
    *,
    is_binary: Literal[True],
    close_on_exit: bool = ...,
    temp_file: bool | str | Path = ...,
    chunk_size: int = ...,
    delete_failures: bool = ...,
    dry_run: bool | Callable[[bytes], object] = ...,
    enabled: Literal[True] = ...,
) -> SafeIO[bytes]: ...
@overload
def writer(
    stream: io.BufferedIOBase | io.RawIOBase,
    is_binary: Literal[True] | None = ...,
    close_on_exit: bool = ...,
    temp_file: bool | str | Path = ...,
    chunk_size: int = ...,
    delete_failures: bool = ...,
    dry_run: bool | Callable[[bytes], object] = ...,
    enabled: Literal[True] = ...,
) -> SafeIO[bytes]: ...
@overload
def writer(
    stream: Destination[str]
    | Callable[[str], object]
    | str
    | os.PathLike[str]
    | None = ...,
    is_binary: Literal[False] | None = ...,
    close_on_exit: bool = ...,
    temp_file: bool | str | Path = ...,
    chunk_size: int = ...,
    delete_failures: bool = ...,
    dry_run: bool | Callable[[str], object] = ...,
    enabled: Literal[True] = ...,
) -> SafeIO[str]: ...

BinaryMode = Literal[
    'rb',
    'wb',
    'ab',
    'xb',
    'rb+',
    'wb+',
    'ab+',
    'xb+',
    'r+b',
    'w+b',
    'a+b',
    'x+b',
    'br',
    'bw',
    'ba',
    'bx',
]
TextMode = Literal[
    'r',
    'w',
    'a',
    'x',
    'rt',
    'wt',
    'at',
    'xt',
    'r+',
    'w+',
    'a+',
    'x+',
    'rt+',
    'wt+',
    'at+',
    'xt+',
    'r+t',
    'w+t',
    'a+t',
    'x+t',
]

@overload
def open(
    name: str | os.PathLike[str],
    mode: Literal['r', 'rt'] = ...,
    buffering: int = ...,
    encoding: str | None = ...,
    errors: str | None = ...,
    newline: str | None = ...,
    closefd: bool = ...,
    opener: Callable[[str, int], int] | None = ...,
    make_parents: bool = ...,
    delete_failures: bool = ...,
    temp_file: bool | str | Path = ...,
    dry_run: bool | Callable[[str], object] = ...,
    enabled: bool = ...,
) -> _IO[str]: ...
@overload
def open(
    name: str | os.PathLike[str],
    mode: Literal['rb', 'br'],
    buffering: int = ...,
    encoding: None = ...,
    errors: None = ...,
    newline: None = ...,
    closefd: bool = ...,
    opener: Callable[[str, int], int] | None = ...,
    make_parents: bool = ...,
    delete_failures: bool = ...,
    temp_file: bool | str | Path = ...,
    dry_run: bool | Callable[[bytes], object] = ...,
    enabled: bool = ...,
) -> _IO[bytes]: ...
@overload
def open(
    name: str | os.PathLike[str],
    mode: BinaryMode,
    buffering: int = ...,
    encoding: None = ...,
    errors: None = ...,
    newline: None = ...,
    closefd: bool = ...,
    opener: Callable[[str, int], int] | None = ...,
    make_parents: bool = ...,
    delete_failures: bool = ...,
    temp_file: bool | str | Path = ...,
    dry_run: bool | Callable[[bytes], object] = ...,
    enabled: Literal[True] = ...,
) -> SafeIO[bytes]: ...
@overload
def open(
    name: str | os.PathLike[str],
    mode: TextMode = ...,
    buffering: int = ...,
    encoding: str | None = ...,
    errors: str | None = ...,
    newline: str | None = ...,
    closefd: bool = ...,
    opener: Callable[[str, int], int] | None = ...,
    make_parents: bool = ...,
    delete_failures: bool = ...,
    temp_file: bool | str | Path = ...,
    dry_run: bool | Callable[[str], object] = ...,
    enabled: Literal[True] = ...,
) -> SafeIO[str]: ...
@overload
def open(
    name: str | os.PathLike[str],
    mode: str = ...,
    buffering: int = ...,
    encoding: str | None = ...,
    errors: str | None = ...,
    newline: str | None = ...,
    closefd: bool = ...,
    opener: Callable[[str, int], int] | None = ...,
    make_parents: bool = ...,
    delete_failures: bool = ...,
    temp_file: bool | str | Path = ...,
    dry_run: bool | Callable[[str | bytes], object] = ...,
    enabled: bool = ...,
) -> _IO[str] | _IO[bytes]: ...
@overload
def closer(
    stream: Socket,
    is_binary: Literal[True] | None = ...,
    close_on_exit: bool = ...,
    *,
    temp_file: bool | str | Path = ...,
    chunk_size: int = ...,
    delete_failures: bool = ...,
    dry_run: bool | Callable[[bytes], object] = ...,
    enabled: Literal[True] = ...,
) -> SafeSocketIO: ...
@overload
def closer(
    stream: Destination[bytes] | Callable[[bytes], object],
    is_binary: Literal[True] | None = ...,
    close_on_exit: bool = ...,
    *,
    temp_file: bool | str | Path = ...,
    chunk_size: int = ...,
    delete_failures: bool = ...,
    dry_run: bool | Callable[[bytes], object] = ...,
    enabled: Literal[True] = ...,
) -> SafeIO[bytes]: ...
@overload
def closer(
    stream: Destination[str] | Callable[[str], object],
    is_binary: Literal[False] | None = ...,
    close_on_exit: bool = ...,
    *,
    temp_file: bool | str | Path = ...,
    chunk_size: int = ...,
    delete_failures: bool = ...,
    dry_run: bool | Callable[[str], object] = ...,
    enabled: Literal[True] = ...,
) -> SafeIO[str]: ...
def dump(
    obj: object,
    stream: Destination[str]
    | Destination[bytes]
    | Socket
    | Callable[[str], object]
    | str
    | os.PathLike[str]
    | None = ...,
    dump: str | ModuleType | Callable[..., object] | None = ...,
    encoding: str = ...,
    **kwargs: object,
) -> object: ...
def printer(
    name: str | os.PathLike[str],
    mode: str = ...,
    buffering: int = ...,
    encoding: str | None = ...,
    errors: str | None = ...,
    newline: str | None = ...,
    closefd: bool = ...,
    opener: Callable[[str, int], int] | None = ...,
    *,
    make_parents: bool = ...,
    delete_failures: bool = ...,
    temp_file: bool | str | Path = ...,
    dry_run: bool | Callable[[str], object] = ...,
    enabled: bool = ...,
) -> ContextManager[Callable[..., None]]: ...
