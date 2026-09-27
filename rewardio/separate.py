import numpy as np
import librosa
from demucs.pretrained import get_model
from demucs.apply import apply_model
import torch

# Force single-threaded execution to prevent segfaults in loops
torch.set_num_threads(1)



# Global cache for the model
_MODEL = None


def _load_audio(file, samplerate, channels):
    """
    Load an audio file as a float32 tensor (channels, samples) at the model's
    sample rate. Demucs must see audio at its training rate (44.1 kHz for
    htdemucs) — a 48 kHz file fed as-is degrades the separation. librosa
    also decodes .m4a (via ffmpeg), which torchaudio cannot in this env.
    """
    y, _ = librosa.load(file, sr=samplerate, mono=False)
    if y.ndim == 1:
        y = y[np.newaxis, :]
    if y.shape[0] != channels:
        # Mono -> stereo, or >2 channels -> downmix; htdemucs wants stereo
        # (mono input would crash its first conv layer)
        y = np.repeat(y.mean(axis=0, keepdims=True), channels, axis=0)
    return torch.from_numpy(np.ascontiguousarray(y, dtype=np.float32))


def separate(file, target_source="drums", gpu=None):
    """
    Run Demucs source separation on an audio file to isolate stems.

    Parameters
    ----------
    file :  str
            Path to the mixture audio file to separate.
            
    target_source : str
            target source to separate. (optional, default = Drums)
    
    gpu : bool, str, or torch.device
          Compute device. None/False = CPU, True = CUDA if available
          (falls back to CPU with a warning), or an explicit device
          (e.g. "cuda:0", "mps", torch.device("cuda")).
          
    Returns
    -------
    target_source : np.ndarray
            Isolated target stem (e.g. drums), converted to mono.
    
    accompaniments : np.ndarray
                    Isolated and combined signal, converted to mono.
                    
    sr : int
         Sample rate of the returned signals (the model's rate, 44.1 kHz)
    """
    global _MODEL

    # Validate inputs up front — before any audio or model loading
    SOURCE = ['vocals', 'drums', 'bass', 'other']
    if target_source not in SOURCE:
        raise ValueError(f"Unknown target source '{target_source}'. Choose from: {SOURCE}")

    # Supported formats: WAV, MP3, FLAC, AIFF, OGG, M4A
    supported_ext = ('.wav', '.mp3', '.flac', '.aiff', '.ogg', '.m4a')
    if not file.lower().endswith(supported_ext):
        raise ValueError(f"Unsupported audio format: {file}. Supported: {supported_ext}")

    if _MODEL is None:
        # print("Loading Demucs model (this happens only once)...")
        _MODEL = get_model(name="htdemucs")
        _MODEL.eval()

    # Resolve the compute device on every call (the cached model is moved as
    # needed, so a later gpu= argument is not silently ignored).
    if gpu is None or gpu is False:
        device = torch.device("cpu")
    elif gpu is True:
        if torch.cuda.is_available():
            device = torch.device("cuda")
        else:
            print("CUDA not available — falling back to CPU.")
            device = torch.device("cpu")
    else:
        device = torch.device(gpu)

    model = _MODEL.to(device)

    # Load at the model's own sample rate and channel count
    waveform = _load_audio(file, model.samplerate, model.audio_channels)
    sr = model.samplerate

    # Apply separation
    waveform = waveform.unsqueeze(0)
    sources = apply_model(model, waveform, split=True, overlap=0.25, progress=True, device=device)[0]

    # Map sources to names
    sources_dict = dict(zip(model.sources, sources))

    # Everything that isn't the target is accompaniment (exact match, not substring)
    accompaniment = [s for s in SOURCE if s != target_source]

    # Sum the accompaniment stems and grab the target stem
    accompaniments = sum(sources_dict[s] for s in accompaniment)
    target = sources_dict[target_source]
    
    # Convert from Tensor to Numpy
    target = target.detach().cpu().numpy().T
    accompaniments = accompaniments.detach().cpu().numpy().T
    
    # Convert to mono
    if len(target.shape) != 1:
        target = np.mean(target, axis=1)
    
    if len(accompaniments.shape) != 1:
        accompaniments = np.mean(accompaniments, axis=1)
    
    return target, accompaniments, sr
