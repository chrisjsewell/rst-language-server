import ctypes
import errno
import os


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
