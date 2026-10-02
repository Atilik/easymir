"""Entry point for `python -m mireasy <audio_file_or_folder>`."""
import sys

from .mireasy import main

sys.exit(main())
