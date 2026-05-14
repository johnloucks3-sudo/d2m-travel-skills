import whisper
from pathlib import Path

# Load model once at module load
# Using 'base' for a balance of speed and accuracy
model = whisper.load_model("base")

def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio file to text using OpenAI Whisper local model.
    """
    result = model.transcribe(audio_path, fp16=False)
    return result["text"].strip()
