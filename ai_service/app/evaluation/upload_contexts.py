import requests
import os
import time
import json


USER_ID = "0a222ef4-81ab-4d90-81c1-4a6eaf4d8330"

SUBJECT_ID = "082a9538-9f2d-4d97-b53c-14e6d1ba05b2"

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InNoYWhkQGdtYWlsLmNvbSIsImp0aSI6IjBhMjIyZWY0LTgxYWItNGQ5MC04MWMxLTRhNmVhZjRkODMzMCIsImV4cCI6MTc4MjE0MDc1MywiaXNzIjoiU2VjdXJlQXBpIiwiYXVkIjoiU2VjdXJlQXBpVXNlciJ9.O-syLK92yU7cb6_j_yHuVcbKhhdOr9oyMuozKqr0qS4"


headers = {
    "Authorization": f"Bearer {TOKEN}"
}


DATA_FOLDER = "/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/nq_contexts_for_kg_500"

TRACK_FILE = "/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/data/uploaded_files.json"

UPLOAD_LIMIT = 1


# =========================
# Load uploaded history
# =========================

if os.path.exists(TRACK_FILE):

    with open(TRACK_FILE, "r") as f:
        uploaded_files = set(json.load(f))

else:
    uploaded_files = set()


# =========================
# Get remaining files
# =========================

all_files = sorted(os.listdir(DATA_FOLDER))

remaining_files = [

    f for f in all_files

    if f not in uploaded_files
]


print(f"Remaining files: {len(remaining_files)}")


# =========================
# Upload only 30 files
# =========================

uploaded_this_run = 0


for file in remaining_files:

    if uploaded_this_run >= UPLOAD_LIMIT:
        break

    file_path = os.path.join(DATA_FOLDER, file)

    try:

        with open(file_path, "rb") as f:

            res = requests.post(

                "http://localhost:5099/api/Document",

                files={"File": f},

                data={
                    "UserId": USER_ID,
                    "SubjectId": SUBJECT_ID
                },

                headers=headers
            )

        print(file, res.status_code)

        if res.status_code in [200, 201]:

            uploaded_files.add(file)

            uploaded_this_run += 1

            # Save progress immediately
            with open(TRACK_FILE, "w") as f:
                json.dump(
                    list(uploaded_files),
                    f,
                    indent=2
                )

        time.sleep(0.4)

    except Exception as e:

        print(f"Error uploading {file}: {e}")


print(f"\nUploaded this run: {uploaded_this_run}")
print(f"Total uploaded: {len(uploaded_files)}")