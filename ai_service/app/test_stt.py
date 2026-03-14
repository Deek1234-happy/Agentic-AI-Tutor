from app.audio.stt import transcribe_audio

audio_path = "/home/aya/Downloads/WhatsApp Ptt 2026-02-24 at 10.55.41 AM.ogg"  # put a small audio file here

text, confidence = transcribe_audio(audio_path)

print("Transcript:", text)
print("Confidence:", confidence)