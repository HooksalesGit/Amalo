from importlib import metadata

try:
    __version__ = metadata.version("amalo")
except metadata.PackageNotFoundError:  # pragma: no cover - during local dev
    __version__ = "0.1.0"
