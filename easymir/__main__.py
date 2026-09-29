"""Entry point for `python -m easymir <audio_file_or_folder>`."""
import sys

from .easymir import main

sys.exit(main())
