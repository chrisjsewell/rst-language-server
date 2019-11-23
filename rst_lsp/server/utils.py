import ctypes
import errno
import logging
import os
from typing import List

__all__ = ("is_process_alive", "find_parents")

logger = logging.getLogger(__name__)


def is_process_alive(pid: int) -> bool:
    """Check whether the process with the given pid is still alive.

    Notes
    -----
    Running `os.kill()` on Windows always exits the process,
    so it can't be used to check for an alive process.
    see: https://docs.python.org/3/library/os.html?highlight=os%20kill#os.kill
    Hence ctypes is used to check for the process directly,
    via windows API avoiding any other 3rd-party dependency.

    """
    if os.name == "nt":
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_INFROMATION = 0x1000
        process = kernel32.OpenProcess(PROCESS_QUERY_INFROMATION, 0, pid)
        if process != 0:
            kernel32.CloseHandle(process)
            return True
        return False
    else:
        if pid < 0:
            return False
        try:
            os.kill(pid, 0)
        except OSError as e:
            return e.errno == errno.EPERM
        else:
            return True


def find_parents(root: str, path: str, names: List[str]):
    """Find files matching the given names relative to the given path.

    The path MUST be within the root!

    Parameters
    ----------
    root: str
        The directory at which to stop recursing upwards.
    path: str
        The file path to start searching up from.
    names: list
        The file/directory names to look for.

    """
    if not root:
        return []

    if not os.path.commonprefix((root, path)):
        logger.warning("Path %s not in %s", path, root)
        return []

    # Split the relative by directory, generate all the parent directories,
    # then check each of them.
    # This avoids running a loop that has different base-cases for unix/windows
    # e.g. /a/b and /a/b/c/d/e.py -> ['/a/b', 'c', 'd']
    dirs = [root] + os.path.relpath(os.path.dirname(path), root).split(os.path.sep)

    # Search each of /a/b/c, /a/b, /a
    while dirs:
        search_dir = os.path.join(*dirs)
        existing = list(
            filter(os.path.exists, [os.path.join(search_dir, n) for n in names])
        )
        if existing:
            return existing
        dirs.pop()

    # Otherwise nothing
    return []
