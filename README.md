## ⚙️ Requirements

### 1️⃣ Python

- Python **3.9 or higher**

---

### 2️⃣ Python Dependencies

Install dependencies using:

```bash
pip install -r requirements.txt
```
3️⃣ System Dependencies (IMPORTANT)
🔹 Tesseract OCR

OCR is required for scanned PDFs and images inside documents.

Windows

Download from:
https://github.com/UB-Mannheim/tesseract/wiki

Default install path:
```bash
C:\Program Files\Tesseract-OCR\tesseract.exe
```

Make sure this path is correctly set in the code.

▶️ Running the AI Service

Start the FastAPI server:

```bash
uvicorn app.extract:app --reload
```

The service will be available at:

```bash
http://localhost:8000
```