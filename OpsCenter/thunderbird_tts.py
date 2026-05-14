import os
from google.cloud import texttospeech
from pathlib import Path

# Initialize client
client = texttospeech.TextToSpeechClient()

def synthesize_speech(text: str, output_path: str, voice_name="en-US-Journey-F"):
    """
    Synthesize text to speech using Google Cloud TTS.
    
    Voices: en-US-Journey-F (Female), en-US-Journey-D (Male)
    """
    synthesis_input = texttospeech.SynthesisInput(text=text)

    # Build the voice request
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name=voice_name
    )

    # Select the type of audio file you want returned
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.OGG_OPUS # OGG format is native to Telegram
    )

    # Perform the text-to-speech request
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    # The response's audio_content is binary.
    with open(output_path, "wb") as out:
        out.write(response.audio_content)
        print(f'Audio content written to file "{output_path}"')
        return output_path
