from functools import lru_cache
import os
import pathlib
import platform
import shutil


@lru_cache(maxsize=1)
def _get_default_cache_path():
    """The path where the cache is stored.

    Adapted from https://github.com/davidhalter/parso/blob/master/parso/cache.py

    Use environment variable ``$RST_LSP_CACHE_DIR``, if set, else:

    - On Linux, if environment variable ``$XDG_CACHE_HOME`` is set,
      ``$XDG_CACHE_HOME/rst_lsp`` is used, else use ``~/.cache/rst_lsp/``.
    - On OS X use ``~/Library/Caches/Rst_lsp/``.
    - On Windows use ``%LOCALAPPDATA%\\rst_lsp\\rst_lsp\\``.
    """
    if os.getenv("RST_LSP_CACHE_DIR", None) is not None:
        dir_ = os.getenv("RST_LSP_CACHE_DIR")
    elif platform.system().lower() == "windows":
        dir_ = os.path.join(os.getenv("LOCALAPPDATA") or "~", "rst_lsp", "rst_lsp")
    elif platform.system().lower() == "darwin":
        dir_ = os.path.join("~", "Library", "Caches", "rst_lsp")
    else:
        dir_ = os.path.join(os.getenv("XDG_CACHE_HOME") or "~/.cache", "rst_lsp")
    return os.path.expanduser(dir_)


def get_default_cache_path(*subfolders) -> pathlib.Path:
    path = _get_default_cache_path()
    if subfolders:
        path = os.path.join(path, *subfolders)
    return pathlib.Path(path)


def create_default_cache_path(*subfolders, exist_ok: bool = True) -> pathlib.Path:
    path = get_default_cache_path(*subfolders)
    path.mkdir(parents=True, exist_ok=exist_ok)
    return path


def remove_default_cache_path(*subfolders, ignore_errors: bool = False):
    path = get_default_cache_path(*subfolders)
    if path.exists():
        shutil.rmtree(str(path), ignore_errors=ignore_errors)
