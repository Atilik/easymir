# easymir: Music Analysis Toolbox

A simple, interactive command-line Python tool for music information retrieval (MIR). `easymir` provides an intuitive interactive shell to load, analyze, and visualize audio files—either individually, by session (folder of songs), or by participant (folder of sessions).

## Features

- **Rhythm & Syncopation**: Beat and downbeat tracking using BEAT THIS! (or madmom), tempo estimation (BPM), and Toussaint syncopation scoring.
- **Stem Separation**: Drum separation using Demucs.
- **Timbre & Dynamics**: LUFS loudness, RMS energy, spectral irregularity, and fluctuation strength.
- **Harmony & Pitch**: Key and scale extraction (Essentia), and frame-level pitch tracking (CREPE).
- **Genre & Mood**: Pre-trained deep learning classifiers for genre, danceability, mood, and voice/instrumental detection (Essentia).
- **Interactive Player**: A built-in GUI player (`play()`) to view waveforms, spectrograms (linear/log/mel), and pitch contours, while sonifying detected beats and onsets over the audio.
- **Batch Processing**: Automatic process and save everything as CSV (`process_and_save()`).

---

## 🛠️ How to Setup easymir

> ### 🖱️ Never used a terminal? Start here → **[INSTALLATION.md](INSTALLATION.md)**
> A click-through guide that assumes zero experience: install one program,
> download the ZIP, double-click `install.command`, and wait for the ✓.
> Afterwards, analyze music by double-clicking `run_easymir.command` and
> dragging your audio folder in.

**Supported platforms:** Apple Silicon Macs (M1 or newer) on macOS 15+.
Intel Macs are not supported. Linux is expected to work but is untested — for
audio playback, install PortAudio (`sudo apt install libportaudio2`). Windows
is not supported natively (use WSL2).

**Quickstart for terminal users** (needs [conda](https://docs.conda.io/en/latest/miniconda.html),
git, and the Xcode command-line tools — `xcode-select --install`):

```bash
git clone https://github.com/Atilik/easymir.git
cd easymir
conda env create -f environment.yml
conda activate easymir
python download_models.py     # optional: enables genre/mood/pitch features
python run_tests.py           # should finish with "… passed" and no failures
python -m easymir /path/to/audio/
```

**Notes**
- Reinstalling? `conda env remove -n easymir` first — `conda env create` won't
  overwrite an existing environment. Or simply double-click `install.command`,
  which handles repairs automatically.
- On first analysis run, the beat tracker (BEAT THIS!) and Demucs download
  their own checkpoints automatically (~100 MB, one time) — so the first song
  takes longer and needs an internet connection.

---

## 🚀 Getting Started

Open a terminal, activate the environment, and go to the repo folder (the one containing
this `README.md`). Then launch the tool with the path to an audio file, a session folder,
or a participant folder:

```bash
conda activate easymir
cd /path/to/easymir           # the repo folder

# Load a single song:
python -m easymir /path/to/song.wav

# Load a session (folder of audio files):
python -m easymir /path/to/session_folder/

# Load a participant (folder containing session folders):
python -m easymir /path/to/participant_folder/
```

This drops you into an interactive Python shell pre-loaded with your data. Leave it with `exit()` or Ctrl-D.

Prefer scripts or notebooks? See [DOCUMENTATION.md](DOCUMENTATION.md) — `from easymir import Stimulus, Session, Participant`.

---

## 📖 The Hierarchy

`easymir` structures your data into three levels depending on the folder you pass:

1. **Participant**: A folder containing multiple *Session* folders.
2. **Session**: A folder containing multiple *Stimulus* audio files.
3. **Stimulus**: A single audio file (e.g., a `.wav` or `.mp3`).

When you load a folder, `easymir` automatically gives you variables (`participant`, `session`, `stimulus`) to interact with your data immediately.

---

## 💻 Using the Interactive Shell

Type the following commands directly into the terminal once `easymir` is launched:

### Navigating Data
- `participant(1)` — Focus on the 1st session. Updates the `session` and `stimulus` variables.
- `participant("baseline")` — Focus on a session containing "baseline" in its folder name.
- `session(3)` — Focus on the 3rd song in the current session. Updates the `stimulus` variable.
- `session("beatles")` — Focus on a song containing "beatles" in its filename.

### Viewing Info
- `stimulus.help()` — List all available attributes and methods for the current song.
- `session.help()` — List all available methods for the session.
- `participant.help()` — List all available methods for the participant.
- `stimulus.print()` — Print a summary of the current song (loudness, BPM, syncopation, key, etc.).
- `session.print()` — List the songs in the current session.
- `participant.print()` — List the sessions loaded for this participant.

### Interactive Player & Viz
- **`stimulus.play()`**
  Launch the interactive unified player. You can switch between Waveform, Mel, Log, Linear, and Pitch views. Click **Beats** or **Onsets** to visualize and sonify rhythm markers directly over the audio playback.
- `stimulus.plot()` — Spectrogram window (`scale='mel'` by default, or `'linear'` / `'log'`).
- `session.boxplot()` — Boxplots of BPM, LUFS, and syncopation across the session.

### Getting Metrics
Access properties on-the-fly. If a metric hasn't been computed yet, `easymir` computes it on first access (model-based metrics take a few seconds).
```python
>>> stimulus.bpm
120.5
>>> stimulus.key
'C#'
>>> stimulus.scale
'minor'
>>> stimulus.syncopation_score()   # 0–100; separates the drums first if needed
31
```

### Exporting Data
- `stimulus.process_and_save("output_folder")`
  Computes ALL available metrics (beats, syncopation, loudness, genre, mood, key, etc.) for the specific song and saves them to a CSV file.
- `session.process_and_save("output_folder")`
  Computes ALL available metrics for every song in the session and saves them to a CSV file.
- `participant.process_and_save("output_folder")`
  Does the same, but loops through every session folder, adding a `session` column to the final CSV.
- `stimulus.partial_process_save(rhythm=True, pitch=True)`
  Computes only the selected feature groups (`rhythm`, `syncopation`, `genre`, `pitch`, `key`, `spectral`) instead of everything. `rhythm` is beats/BPM only (fast); `syncopation` runs Demucs separation + scoring (slow). Available on `session` and `participant` too.

Results are written to `output_folder/Analysis_DD-MM-YYYY/easymir_HH-MM-SS.csv` (the exact path is printed after saving).

### Aggregate Metrics
- `session.average_fluctuation` / `session.average_irregularity` — Mean fluctuation / spectral irregularity across the session's songs.
- `participant.average_fluctuation` / `participant.average_irregularity` — Same, across every song in every session.

---

## 🛠 Advanced Features

### Separation & Syncopation
Syncopation requires isolating the drums with Demucs. The first time you ask for a syncopation score, `easymir` asks for confirmation (`Proceed? [Y/n]`) — on a CPU, separation takes roughly as long as the song itself.
```python
>>> stimulus.syncopation_score()
```

### Pitch Tracking
The pitch view mode in `stimulus.play()` runs CREPE pitch detection.
```python
>>> stimulus.pitch_time
>>> stimulus.pitch_freq
```

---

## 🧪 Running Tests

```bash
# Fast suite — synthetic audio only (~15 s with classifier models installed)
python run_tests.py

# Also run the slow model tests (madmom beat detection, Demucs separation
# if the htdemucs checkpoint is already cached)
EASYMIR_RUN_SLOW=1 python run_tests.py
```

Tests that need the Essentia classifier models (`easymir/models/*.pb`)
skip automatically while those files are absent — run `python download_models.py`
to activate them.
