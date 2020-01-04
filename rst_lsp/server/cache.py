from functools import lru_cache
import os
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


def get_default_cache_path(subfolder=None):
    path = _get_default_cache_path()
    if subfolder is not None:
        path = os.path.join(path, subfolder)
    return path


def create_default_cache_path(subfolder=None, exist_ok=True):
    path = get_default_cache_path(subfolder=subfolder)
    os.makedirs(path, exist_ok=True)


def remove_default_cache_path(subfolder=None, ignore_errors=False):
    path = get_default_cache_path(subfolder=subfolder)
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=ignore_errors)
