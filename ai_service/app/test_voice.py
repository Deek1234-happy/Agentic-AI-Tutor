import requests

url = "http://127.0.0.1:8000/voice/voice-chat"

files = {
    "audio": open("test.wav", "rb")
}


response = requests.post(url, files=files)

print("Status:", response.status_code)

with open("response.wav", "wb") as f:
    f.write(response.content)

print("Audio saved as response.wav")