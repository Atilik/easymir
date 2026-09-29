"""
easymir — an interactive music information retrieval (MIR) toolbox.

Library use (run Python from the repo folder):

    from easymir import Stimulus, Session, Participant

Interactive shell:

    python -m easymir <audio_file_or_folder>
"""

__all__ = ["Stimulus", "Session", "Participant"]


def __getattr__(name):
    # Lazy exports: `import easymir.dsp` (and the tests) stays lightweight —
    # the full ML stack (torch, TensorFlow, ...) loads only when one of these
    # classes is first used.
    if name in __all__:
        import importlib
        core = importlib.import_module(".easymir", __name__)
        return getattr(core, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(list(globals()) + __all__)
