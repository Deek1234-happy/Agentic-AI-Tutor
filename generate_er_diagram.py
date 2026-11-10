from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import HexColor, Color

OUTPUT_PATH = r"C:\Users\Admin\Documents\MCA_3rdSem_Project\Project\Agentic-AI-Tutor\ER_Diagram_GenT.pdf"
W, H = 842, 595


def draw_box(canvas, x, y, w, h, title, attrs):
    canvas.setFillColor(Color(0.95, 0.98, 1.0))
    canvas.setStrokeColor(HexColor("#2f5d8a"))
    canvas.setLineWidth(1.2)
    canvas.roundRect(x, y, w, h, 10, fill=1, stroke=1)

    canvas.setFillColor(HexColor("#dfeeff"))
    canvas.roundRect(x, y + h - 26, w, 26, 10, fill=1, stroke=0)

    canvas.setFillColor(HexColor("#1d3557"))
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(x + 10, y + h - 18, title)

    canvas.setFont("Helvetica", 8.5)
    for i, attr in enumerate(attrs):
        canvas.drawString(x + 10, y + h - 42 - i * 12, attr)


def connector(canvas, x1, y1, x2, y2, label=None):
    canvas.setStrokeColor(HexColor("#4a627d"))
    canvas.setLineWidth(1.1)
    canvas.line(x1, y1, x2, y2)
    if label:
        canvas.setFillColor(HexColor("#2d3f5c"))
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString((x1 + x2) / 2, (y1 + y2) / 2 + 6, label)


canvas = Canvas(OUTPUT_PATH, pagesize=(W, H))
canvas.setTitle("Agentic AI Tutor ER Diagram")
canvas.setFont("Helvetica-Bold", 22)
canvas.setFillColor(HexColor("#1d3557"))
canvas.drawString(30, H - 38, "Agentic AI Tutor — Core ER Diagram")
canvas.setFont("Helvetica", 10)
canvas.setFillColor(HexColor("#4a627d"))
canvas.drawString(30, H - 58, "Conceptual ER model for the relational data layer. Neo4j knowledge graph is maintained separately.")

box_w = 170
box_h = 145

row1 = [
    (30, 350, "User", ["id PK", "email", "password_hash", "full_name", "role", "created_at"]),
    (230, 350, "Subject", ["id PK", "user_id FK", "name", "description", "created_at"]),
    (430, 350, "Document", ["id PK", "subject_id FK", "title", "file_path", "status", "upload_date"]),
    (630, 350, "DocumentChunk", ["id PK", "document_id FK", "chunk_no", "content", "page_no", "embedding_ref"]),
    (830, 350, "ChatSession", ["id PK", "user_id FK", "subject_id FK", "title", "created_at"]),
]

row2 = [
    (30, 150, "ChatMessage", ["id PK", "session_id FK", "sender", "message_text", "citations_json", "created_at"]),
    (230, 150, "Quiz", ["id PK", "subject_id FK", "document_id FK", "title", "status", "created_at"]),
    (430, 150, "QuizQuestion", ["id PK", "quiz_id FK", "question_text", "bloom_level", "explanation"]),
    (630, 150, "QuizOption", ["id PK", "question_id FK", "option_text", "is_correct"]),
    (830, 150, "QuizAttempt", ["id PK", "quiz_id FK", "user_id FK", "score", "started_at", "submitted_at"]),
]

row3 = [
    (30, 20, "QuizAnswer", ["id PK", "attempt_id FK", "question_id FK", "selected_option_id FK", "is_correct"]),
    (230, 20, "Notification", ["id PK", "user_id FK", "title", "message", "is_read", "created_at"]),
    (430, 20, "StudyPlan", ["id PK", "user_id FK", "title", "status", "created_at"]),
    (630, 20, "KnowledgeGraph", ["Neo4j store", "entity nodes", "relationship edges", "subject/document IDs"]),
]

for x, y, title, attrs in row1 + row2 + row3:
    draw_box(canvas, x, y, box_w, box_h, title, attrs)

# Main relationships
connector(canvas, 200, 420, 230, 420, "1:N")
connector(canvas, 400, 420, 430, 420, "1:N")
connector(canvas, 600, 420, 630, 420, "1:N")
connector(canvas, 800, 420, 830, 420, "1:N")
connector(canvas, 200, 220, 230, 220, "1:N")
connector(canvas, 400, 220, 430, 220, "1:N")
connector(canvas, 600, 220, 630, 220, "1:N")
connector(canvas, 800, 220, 830, 220, "1:N")
connector(canvas, 195, 90, 230, 90, "1:N")
connector(canvas, 395, 90, 430, 90, "1:N")
connector(canvas, 595, 90, 630, 90, "1:N")
connector(canvas, 795, 90, 830, 90, "1:N")
connector(canvas, 200, 420, 830, 420, "1:N")
connector(canvas, 200, 220, 830, 220, "1:N")
connector(canvas, 830, 220, 830, 350, "1:N")

# Legend band
canvas.setFillColor(HexColor("#eef6ff"))
canvas.roundRect(30, H - 110, 420, 42, 8, fill=1, stroke=1)
canvas.setFillColor(HexColor("#1d3557"))
canvas.setFont("Helvetica-Bold", 11)
canvas.drawString(45, H - 90, "Key interpretation")
canvas.setFont("Helvetica", 9)
canvas.drawString(45, H - 108, "Relational records live in PostgreSQL; the concept graph lives in Neo4j with subject/document references.")

canvas.setFillColor(HexColor("#475569"))
canvas.setFont("Helvetica-Oblique", 8)
canvas.drawCentredString(W / 2, 12, "Agentic AI Tutor project • Conceptual ER diagram • Generated for documentation and download")

canvas.save()
print(f"PDF created: {OUTPUT_PATH}")
