"""البث الصوتي — يدعم PyTgCalls اختياريًا."""

try:
    from pytgcalls import PyTgCalls  # noqa: F401

    HAS_STREAMING = True
except ImportError:
    HAS_STREAMING = False
