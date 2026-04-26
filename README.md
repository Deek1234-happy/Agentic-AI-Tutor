# Agentic AI Tutor - Quiz Processing Service

This repository contains a FastAPI service that processes uploaded learning documents into high-quality semantic chunks for quiz and MCQ generation workflows.

The pipeline supports multiple file formats, optional OCR, semantic chunking, deduplication, and optional metadata extraction using Groq.

## Project Structure

```text
Quiz/
  app/
    main.py                         # FastAPI app entrypoint
    quiz.py                         # Upload + processing API endpoint
    processor.py                    # End-to-end processing pipeline
    router.py                       # File type routing and validation
    parsers.py                      # PDF/DOCX/PPTX/TXT/CSV text extraction
    quiz_engine.py                  # Cleaning, chunking, validation, postprocess
    quiz_config.py                  # Chunking and cleaning config dataclasses
    metadata_extraction.py          # S3 metadata generation via Groq
    reprocess_failed_metadata.py    # Retry/fix failed metadata outputs
    requirements.txt
  data/
    uploads/                        # Temporary uploaded files
    chunks/                         # Per-file JSONL chunks
    global_chunks/                  # Rolling global chunk archives
    metadata/                       # Groq metadata output (usable/not_usable)
    metadata_fixed/                 # Reprocessed metadata output
```

## What The Service Does

1. Accepts an uploaded file through the API.
2. Extracts raw text using a parser based on file extension.
3. Optionally runs OCR for embedded/scanned image content.
4. Cleans noisy text.
5. Splits text into semantic chunks.
6. Validates and filters chunks (quality, size, coherence).
7. Post-processes chunks (deduplicate, micro-headers, context fields).
8. Saves results to JSONL files.

## Supported File Types

- `pdf`
- `docx`
- `pptx`
- `txt`
- `csv`

## Tech Stack

- FastAPI + Uvicorn
- PyMuPDF, python-docx, python-pptx
- Tesseract OCR + Pillow + pdf2image
- sentence-transformers + torch + numpy
- Groq API (metadata extraction stage)

## Prerequisites

- Python 3.10+
- Tesseract OCR installed (if using `use_ocr=true`)

Important: `app/parsers.py` sets a Windows-specific default path:

```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Update this path if Tesseract is installed elsewhere.

## Installation

From repository root:

```bash
cd Quiz/app
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run The API

From `Quiz` directory:

```bash
cd Quiz
uvicorn app.main:app --reload
```

Once running:

- Swagger UI: `http://127.0.0.1:8000/docs`
- Base route prefix: `/quiz`

## API Endpoint

### `POST /quiz/process`

Processes one uploaded file and returns chunk output information.

Query parameters:

- `use_bart` (bool, default `false`): use BART for micro-header generation (slower)
- `use_ocr` (bool, default `false`): run OCR on image content
- `force_reprocess` (bool, default `true`): ignore cached output and process again

Multipart form data:

- `file`: file upload (required)

Example curl:

```bash
curl -X POST "http://127.0.0.1:8000/quiz/process?use_ocr=false&use_bart=false&force_reprocess=true" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample.pdf"
```

Example success response:

```json
{
  "message": "Processed successfully",
  "chunks_created": 24,
  "output_file": "data/chunks/sample.jsonl",
  "ocr_used": false,
  "bart_headers_used": false
}
```

## Output Format (Chunk JSONL)

Each line in `data/chunks/<file_id>.jsonl` is a JSON object similar to:

```json
{
  "file_id": "sample",
  "chunk_id": "sample_1",
  "concept_heading": "Gradient Descent Basics",
  "text": "...",
  "context_fringe": {
    "prev_sentence": "...",
    "next_sentence": "..."
  },
  "word_count": 132,
  "token_count": 168,
  "semantic_score": 0.82,
  "quality_score": 0.77,
  "micro_header": "...",
  "text_with_context": "[...]"
}
```

Note: `micro_header` and `text_with_context` are added during post-processing.

## Metadata Extraction Workflow

After chunk generation, you can enrich chunks with MCQ-focused metadata.

Create `Quiz/app/.env` with your Groq key (example format):

```dotenv
GROQ_API_KEY=""
```

Then set the real value:

```dotenv
GROQ_API_KEY="your_groq_api_key_here"
```

### 1) Extract metadata with Groq

From `Quiz` directory:

```bash
set GROQ_API_KEY=your_api_key_here
python app/metadata_extraction.py --input data/global_chunks --output data/metadata
```

This creates:

- `data/metadata/usable/*.jsonl`
- `data/metadata/not_usable/*.jsonl`

### 2) Reprocess failed metadata (optional fix pass)

```bash
set GROQ_API_KEY=your_api_key_here
python app/reprocess_failed_metadata.py --metadata-dir data/metadata --chunks-dir data/global_chunks --output data/metadata_fixed
```
