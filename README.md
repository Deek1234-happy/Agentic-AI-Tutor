# Agentic AI Tutor — Quiz Generation & Fine-tuning Pipeline

An end-to-end, offline pipeline for producing high-quality Multiple Choice
Questions (MCQs) and fine-tuning an open-source **Qwen** model to generate them
autonomously. The system ingests raw educational documents, enriches them with
structured metadata, generates MCQs with a strong *Teacher Model*, validates
every question through a 7-stage automated quality gate, and then distills the
Teacher's capability into a smaller, specialized student model.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Repository Structure](#repository-structure)
3. [Pipeline Stages](#pipeline-stages)
4. [Validation Layer (Stage 5)](#validation-layer-stage-5)
5. [Getting Started](#getting-started)
6. [Configuration](#configuration)
7. [Results & Evaluation](#results--evaluation)
8. [Related Repository](#related-repository)
9. [Tech Stack](#tech-stack)
---

## Architecture Overview

The project is organized as a sequential 9-stage offline pipeline. Each stage
produces a structured artifact that becomes the input of the next.

```text
 ┌──────────────────────────┐     ┌──────────────────────────┐     ┌──────────────────────────┐
 │  S1–S3                   │     │  S4                      │     │  S5                      │
 │  Content Preparation     │ ──▶ │  MCQ Generation          │ ──▶│  5-Check Validation      │
 │  (FastAPI service)       │     │  (Teacher Model: Gemini) │     │                          │
 └──────────────────────────┘     └──────────────────────────┘     └─────────────┬────────────┘
                                                                                 │
                                                                                 ▼
                                          ┌──────────────────────────────────────────────────┐
                                          │  S6–S9                                           │
                                          │  Dataset → Classifier → Qwen Fine-tune → Eval    │
                                          └──────────────────────────────────────────────────┘
```

---

## Repository Structure

```text
Quiz/
├── stage1_3_content_preparation/      # FastAPI service for ingestion, chunking, metadata
│   ├── app/
│   │   ├── main.py                    # FastAPI entrypoint
│   │   ├── router.py                  # File-type routing (pdf/docx/pptx/txt/csv)
│   │   ├── parsers.py                 # Format-specific parsers (with OCR support)
│   │   ├── processor.py               # Cleaning + normalization pipeline
│   │   ├── quiz_engine.py             # Semantic chunking
│   │   ├── metadata_extraction.py     # Bloom level, concepts, keywords via Gemini/Groq
│   │   ├── reprocess_failed_metadata.py
│   │   └── quiz_config.py
│   └── requirements.txt
│
├── stage4_mcq_generation/
│   └── S4_MCQ_Pipeline (Teacher-Model).ipynb   # Gemini-based MCQ generation
│
├── stage5_validation/                 # Modular validation pipeline (CLI)
│   ├── run_validation.py              # CLI entry point
│   ├── mcq_validator.py               # Orchestrator
│   ├── validators/
│   │   ├── format_validator.py
│   │   ├── relevance_validator.py
│   │   ├── distractor_validator.py
│   │   ├── entailment_validator.py    # NLI CrossEncoder
│   │   ├── dedup_validator.py
│   │   └── llm_judge_validator.py     # Groq / Anthropic / OpenAI / Ollama
│   ├── utils/                         # embeddings, logger
│   ├── config/settings.py             # All thresholds & model names
│   └── requirements.txt
│
└── stage6_9_model_training_evaluation/
    ├── quiz-ft-v8.ipynb               # Qwen fine-tuning + evaluation
    └── Plots/                         # Training curves, KL, perplexity, Bloom breakdowns…
```

---

## Pipeline Stages

### Stage 1 — Document Processing
Implemented in `app/processor.py`, `app/parsers.py`, `app/router.py`.
Supported formats: **PDF, DOCX, PPTX, TXT, CSV**. PDFs and image-heavy
documents are passed through OCR (`pytesseract` + `pdf2image`) when needed.
Text is cleaned, normalized (`ftfy`), and language-detected (`langdetect`).

### Stage 2 — Semantic Chunking
Implemented in `app/quiz_engine.py`. Long documents are split into
semantically coherent passages using `sentence-transformers` embeddings,
preserving local context for downstream question generation.

### Stage 3 — Metadata Extraction
Implemented in `app/metadata_extraction.py`. Each chunk is annotated with:
- **Usability flag** (whether the chunk can yield MCQs at all)
- **Bloom's Taxonomy level**
- **Chunk type** (definition, process, example, comparison, …)
- **Key concepts** and **keywords**

The extractor calls **Groq**.
Failed chunks are retried via `reprocess_failed_metadata.py`.

### Stage 4 — MCQ Generation (Teacher Model)
`S4_MCQ_Pipeline (Teacher-Model).ipynb`. The semantic chunks plus their
metadata are sent to a high-capability *Teacher Model* (Gemini) using
metadata-aware prompts that target the chunk's Bloom level and type.

### Stage 5 — Validation Layer
See the [Validation Layer](#validation-layer-stage-5) section below.

### Stage 6 — Dataset Construction
Validated MCQs are consolidated into a structured instruction-tuning dataset
(JSONL) carrying the question, options, answer, explanation, source chunk,
and metadata fields.

### Stage 7 — Metadata Classifier

### Stage 8 — Qwen Fine-tuning
`quiz-ft-v8.ipynb`. The Qwen base model is fine-tuned on the Stage-6 dataset,
distilling the Teacher Model's behavior into an efficient open-source model.

### Stage 9 — Evaluation
Quantitative and qualitative evaluation of the fine-tuned model: training /
eval loss, perplexity, KL divergence between distributions, semantic
similarity, CMQS, Bloom-level coverage and per-dimension quality breakdowns.
Plots are stored in `stage6_9_model_training_evaluation/Plots/`.

---

## Validation Layer (Stage 5)

The validation pipeline (`run_validation.py`) runs each MCQ through 7
sequential checks. Questions are processed **stage-by-stage** so failures are
filtered cheaply before expensive checks run.

| # | Validator              | What it enforces                                                              |
|---|------------------------|-------------------------------------------------------------------------------|
| 1 | **Format**             | Required options A–D, length bounds, explanation present, valid answer key   |
| 2 | **Relevance**          | Question is semantically grounded in its source chunk (cosine ≥ threshold)    |
| 3 | **Distractor**         | Wrong options are plausible, not paraphrases of the correct answer (NLI gate) |
| 4 | **Entailment**         | NLI CrossEncoder confirms the chunk *entails* the correct answer              |
| 5 | **Deduplication**      | Near-duplicate questions are removed (global or per-document scope)           |
| 6 | **LLM Judge**          | LLM scores pedagogical quality (Groq / Anthropic / OpenAI / Ollama)           |
| 7 | **Relevance (final)**  | Final topic-alignment pass before acceptance                                  |

Default models (configurable in `config/settings.py`):

- Embeddings & relevance: `bge-large-en-v1.5`
- NLI / entailment: `nli-deberta-v3-large`
- LLM Judge: `llama-3.3-70b-versatile` on **Groq** by default

A fallback chain automatically switches providers/models on 429 rate limits
(Groq → OpenRouter, multiple Llama and GPT-OSS variants).

### Running the validator

```bash
cd stage5_validation
pip install -r requirements.txt

# Basic run
python run_validation.py --input mcqs.jsonl

# Choose provider, resume from checkpoints, gzip debug artifacts
python run_validation.py \
  --input mcqs.jsonl \
  --provider groq --groq-model llama-3.3-70b \
  --stage-output-dir stage_outputs \
  --compress

# Run a subset of stages
python run_validation.py --input mcqs.jsonl --start-stage 3 --end-stage 5
```

Key CLI flags: `--provider`, `--groq-model`, `--relevance-threshold`,
`--dedup-threshold`, `--device {cuda|mps|cpu}`, `--no-stage-by-stage`,
`--use-fallback-chain`, `--no-resume`, `--debug-dir`.

---

## Getting Started

### Prerequisites
- Python **3.10+**
- (Optional) NVIDIA GPU with CUDA 12.1 or Apple Silicon (MPS) for embeddings / NLI
- API keys (as needed): `GEMINI_API_KEY`, `GROQ_API_KEY`,
  `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`

### 1. Content Preparation service (Stages 1–3)

```bash
cd stage1_3_content_preparation
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The FastAPI service mounts the quiz-chunking router at `/quiz` and exposes
endpoints for uploading documents and retrieving cleaned, chunked, and
metadata-annotated output.

### 2. MCQ Generation (Stage 4)

Open `stage4_mcq_generation/S4_MCQ_Pipeline (Teacher-Model).ipynb` in
Jupyter/Colab, configure your Gemini key, and run the notebook against the
Stage-3 output.

### 3. Validation (Stage 5)

```bash
cd stage5_validation
pip install -r requirements.txt
python run_validation.py --input ../stage4_mcq_generation/mcqs.jsonl
```

For GPU PyTorch:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

### 4. Fine-tuning & Evaluation (Stages 6–9)

Open `stage6_9_model_training_evaluation/quiz-ft-v8.ipynb` and follow the
notebook to build the instruction dataset, fine-tune Qwen, and run the
evaluation suite.

---

## Configuration

All Stage-5 thresholds and model names live in
`stage5_validation/config/settings.py` and can be tuned without touching
validator logic. Highlights:

| Setting                                       | Default                     |
|-----------------------------------------------|-----------------------------|
| `RelevanceConfig.threshold`                   | `0.50`                      |
| `DistractorConfig.max_similarity_to_answer`   | `0.90`                      |
| `DistractorConfig.nli_duplicate_entailment`   | `0.78`                      |
| `DeduplicationConfig.similarity_threshold`    | `0.92`                      |
| `LLMJudgeConfig.provider` / `model`           | `groq` / `llama-3.3-70b`    |

---

## Results & Evaluation

Generated evaluation artifacts (in
`stage6_9_model_training_evaluation/Plots/`):

- `training_loss.png`, `training_eval_loss.png` — fine-tuning curves
- `V12_perplexity.png` — perplexity across stages
- `V10_retention_score.png` — knowledge retention
- `V11_kl_score_distributions.png`, `V11b_kl_summary_bar.png` — KL between
  teacher and student outputs
- `V1_radar_all_stages.png`, `V2_grouped_bar_dimensions.png` — multi-dimension
  quality
- `V3_bloom_level_lines.png`, `V7_bloom_breakdown_bar.png` — Bloom-level
  coverage
- `V4_quality_distribution.png`, `V6_cmqs_bar.png` — composite quality scores
- `V5_gap_heatmap.png`, `V9_gap_ranking.png` — gap analysis
- `V8_semantic_similarity.png` — semantic similarity to gold MCQs


---

## Related Repository

The experiments, teacher–student knowledge distillation, fine-tuning iterations, hyperparameter tuning, and evaluation studies that led to the final deployed model are documented in the following repository:

- Training & Experiments Repository: https://github.com/Rehab-Hamdy/Quiz-Generation-KD-FT

Multiple model versions were trained and evaluated throughout the research process. The current Agentic AI Tutor system integrates the best-performing model, **Version 8 (V8)**, which was selected based on its overall performance across the evaluation metrics and quality assessments.

### Final Selected Model

The final production model is publicly available on Hugging Face:

- https://huggingface.co/Rehab-Hamdy/Qwen-BloomAware-Educational-MCQ-Generator

This model corresponds to **Version 8 (V8)** from the experimentation repository and serves as the MCQ generation model deployed within the Agentic AI Tutor system.

The repository above contains the full research and experimentation history, while this repository focuses on integrating the selected model into the production MCQ generation pipeline.


---

## Tech Stack

- **Backend service:** FastAPI · Uvicorn · Pydantic
- **Document parsing:** PyMuPDF · python-docx · python-pptx · pdf2image ·
  pytesseract · Pillow · ftfy · langdetect
- **Embeddings & NLI:** sentence-transformers (`bge-large-en-v1.5`),
  CrossEncoder (`nli-deberta-v3-large`), Torch, FAISS
- **LLM providers:** Gemini (Teacher), Groq (judge + fallback), Anthropic,
  OpenAI / OpenRouter, Ollama
- **Storage:** SQLAlchemy · psycopg2
- **Training:** Hugging Face Transformers · PEFT (Qwen fine-tuning notebook)
- **Tooling:** tqdm · pytest
