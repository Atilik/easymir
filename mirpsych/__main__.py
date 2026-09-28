"""Entry point for `python -m mirpsych <audio_file_or_folder>`."""
import sys

from .mirpsych import main

sys.exit(main())
