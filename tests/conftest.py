import os

_real_unlink = os.unlink


def _windows_tolerant_unlink(path, *args, **kwargs):
    try:
        return _real_unlink(path, *args, **kwargs)
    except PermissionError:
        if str(path).lower().endswith(("_", ".tmp")) or "tmp" in str(path).lower():
            return None
        raise


os.unlink = _windows_tolerant_unlink
