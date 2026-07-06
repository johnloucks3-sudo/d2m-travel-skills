from pathlib import Path

_model = None


def _get_model():
    """Lazy-load Whisper on first real transcription call, not at import time.

    ELON PROPOSAL-20260613: eager module-scope load caused whisper's c10::Error
    abort() crash under memory pressure at gateway startup. Loading on first use
    means a broken/OOM'd whisper never takes the gateway down with it.
    """
    global _model
    if _model is None:
        import whisper
        _model = whisper.load_model("base")
    return _model


def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio file to text using OpenAI Whisper local model.
    """
    result = _get_model().transcribe(audio_path, fp16=False)
    return result["text"].strip()
