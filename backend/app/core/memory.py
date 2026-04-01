from __future__ import annotations

import ctypes
import ctypes.util
import sys
from typing import Callable

_malloc_trim: Callable[[int], int] | None = None

if sys.platform.startswith("linux"):
    libc_path = ctypes.util.find_library("c")
    if libc_path is not None:
        try:
            libc = ctypes.CDLL(libc_path)
        except OSError:
            libc = None
        if libc is not None:
            trim = getattr(libc, "malloc_trim", None)
            if trim is not None:
                trim.argtypes = [ctypes.c_size_t]
                trim.restype = ctypes.c_int
                _malloc_trim = trim


def trim_process_heap() -> bool:
    """Return freed glibc heap pages to the OS when supported."""
    if _malloc_trim is None:
        return False
    return bool(_malloc_trim(0))
