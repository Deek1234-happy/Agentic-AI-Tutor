



The platform is a university-level intelligent learning system where students upload their own study materials and receive:

* AI tutoring (RAG-based chatbot)
* Audio interaction (Speech-to-Text and Text-to-Speech)
* Adaptive quizzes
* Personalized study planner
* Progress analytics
* Smart notifications

The design must feel:

Modern
Academic
Trustworthy
AI-driven
Clean and structured

Desktop-first design, fully responsive for mobile.

---

# 🧱 Global Layout Structure

Create a main application layout with:

* Left Sidebar Navigation
* Top Navbar
* Main Content Area
* Optional Right Context Panel (for citations / graph view)

Use soft shadows, rounded cards, clean typography (Inter or Poppins), and a blue/white educational theme.

---

# 🔐 Authentication Pages

Design:

1. Login Page
2. Register Page

Centered card layout with:

* First Name
* Last Name
* Email
* Password
* Confirm Password
* Primary CTA button

Minimal, modern design.

---

# 🏠 Dashboard Page

Create a structured dashboard with:

### Top Stats Cards:

* Total Subjects
* Uploaded Files Count
* Mastery Score %
* Quizzes Taken
* Completed Study Plan Items

### Sections:

* Weak Topics (highlighted in red)
* Upcoming Study Plan (next 3 items)
* Notifications Preview

Use cards and clean data visualization.

---

# 📚 Subjects Section (Core Feature)

Each user organizes materials by SUBJECT.

Design a grid layout of Subject Cards.

Each Subject Card includes:

* Subject Name
* Number of Documents
* Progress Bar
* Last Activity Date
* Edit Button
* Delete Button

Add:
➕ “Create Subject” button

---

## Add Subject Modal

Fields:

* Subject Name
* Create Button

Subjects must feel like learning spaces.

---

## Inside a Subject

Create tab navigation inside each subject:

* Documents
* Tutor
* Quizzes
* Study Plan
* Progress

---

# 📄 Document Upload Interface

Design a drag-and-drop uploader with:

* File Upload Area
* Subject Dropdown (Required)
* Upload Button

Show file status indicators:

* Pending
* Processing
* Completed
* Failed

Document List Table:

* File Name
* Type
* Size
* Upload Date
* Status
* Delete Option

---

# 🤖 Tutor Page (AI Chat Interface)

This is the most important page.

Layout:

Left Panel:

* Chat Sessions History

Center:

* Chat Conversation UI

Right Panel:

* Citations Section
* Confidence Score Meter
* Knowledge Graph Toggle

---

## Chat UI Requirements

* User message bubble (right side)
* AI message bubble (left side)
* Expandable citation references
* Confidence progress bar under each AI message
* Warning banner when confidence is low

---

# 🎤 Audio Features

## Speech-to-Text (STT)

Include:

* Microphone button inside chat input
* Recording animation (waveform)
* Recording timer
* Cancel option
* Editable transcript before sending

## Text-to-Speech (TTS)

Each AI response must include:

* Play button
* Pause button
* Speed selector (1x, 1.5x)

Audio interaction should feel smooth and intelligent.

---

# 🌐 Optional Web Search Toggle

Include a switch:
“Allow Web Search”

If enabled:
Show external source citations separately.

---

# 🧠 Knowledge Graph Panel

When enabled, show:

* Interactive graph visualization
* Nodes (concepts)
* Edges (depends-on, part-of)
* Clickable nodes that open explanation popup

Graph panel appears on the right side.

---

# 📝 Quiz Section

Create two tabs:

1. Generate Quiz
2. Quiz History

---

## Generate Quiz Page

Fields:

* Select Subject
* Select Topic
* Difficulty (Easy / Medium / Hard / Adaptive)
* Number of Questions
* Generate Button

---

## Quiz Taking Interface

Display:

* Question Text
* 4 Answer Options (A, B, C, D)
* Citation toggle
* Timer (optional)
* Submit Button

---

## Quiz Results Page

Show:

* Score %
* Difficulty Level
* Weak Topics Identified
* Explanation per question
* Citations
* Retry Button

Use mastery visualization (progress bars).

---

# 📅 Study Planner Section

Create:

## Planner Dashboard

Calendar view (Monthly + Weekly)

Visual Indicators:

* Upcoming tasks
* Completed (green)
* Missed (red)

---

## Generate Study Plan Page

Fields:

* Subject
* Start Date
* End Date
* Deadline
* Daily Available Hours

CTA:
Generate Plan

---

## Study Plan Detail View

List of items:

* Concept Name
* Estimated Time
* Scheduled Date
* Completion Checkbox

When updated dynamically, show banner:
“Your study plan has been updated based on your performance.”

---

# 📊 Progress Page

Create analytics dashboard with:

* Mastery per Topic (progress bars)
* Quiz Performance Over Time (line chart)
* Weak vs Strong Topics comparison
* Total Study Time

Each topic shows mastery % and last updated date.

---

# 🔔 Notification System

Add bell icon in navbar.

Dropdown panel:

* Title
* Message
* Time
* Mark as Read

---

## Notification Preferences Page

Toggle switches:

* Study Reminders
* Weak Topic Alerts
* Quiz Notifications
* Progress Updates

Save Button.

---

# ⚙️ Settings Page

Include:

* Profile Information
* Change Password
* Audio Preferences
* Default Web Search Toggle

---

# 🎨 Visual Design Guidelines

Color Palette:

* Primary: Soft Academic Blue
* Secondary: Light Gray
* Success: Green
* Warning: Yellow
* Error: Red

Typography:
Clean sans-serif (Inter or Poppins)

Style:
Rounded corners
Soft shadows
Minimalistic icons
Clear hierarchy
AI-powered intelligent aesthetic

---

# 📱 Responsive Design

Mobile version must include:

* Collapsible sidebar
* Bottom navigation
* Full-screen chat mode
* Simplified dashboard

---

# 🔁 Overall User Flow

1. Register / Login
2. Create Subject
3. Upload Documents to Subject
4. Chat with Tutor (Text or Audio)
5. Generate Quiz
6. Take Quiz
7. View Results
8. Generate Study Plan
9. Track Progress
10. Receive Notifications

---

Design the full design system including:

* Buttons
* Cards
* Inputs
* Modals
* Toggles
* Graph components
* Chat bubbles
* Audio components
* Calendar components
* Data visualization components

The final UI must feel like a smart AI academic assistant built for serious university students.

