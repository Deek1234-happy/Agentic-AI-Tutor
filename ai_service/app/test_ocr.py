from PIL import Image
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

img = Image.open("C://Users//HP//My-Github//Agentic-AI-Tutor//test_files//arabic_test.png")
print(pytesseract.image_to_string(img))

