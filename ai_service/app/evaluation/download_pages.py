import wikipedia
import os
import time

wikipedia.set_lang("en")

TITLES_FILE = "/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/wiki_titles.txt"
OUTPUT_DIR = "/home/aya/EvalFinalRAGWithDatasets/Agentic-AI-Tutor/ai_service/wiki_docs"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_filename(title):
    return title.replace("/", "_").replace(" ", "_")


with open(TITLES_FILE, "r", encoding="utf-8") as f:
    titles = [line.strip() for line in f.readlines() if line.strip()]


success = 0
failed = 0


for title in titles:
    try:
        # ✅ أهم تعديل
        page = wikipedia.page(title, auto_suggest=False)
        content = page.content

    except wikipedia.exceptions.DisambiguationError as e:
        try:
            # ✅ خدي أول اختيار منطقي
            page = wikipedia.page(e.options[0], auto_suggest=False)
            content = page.content
        except:
            print(f"❌ Failed (disambiguation): {title}")
            failed += 1
            continue

    except wikipedia.exceptions.PageError:
        print(f"❌ Page not found: {title}")
        failed += 1
        continue

    except Exception as e:
        print(f"❌ Failed: {title} → {e}")
        failed += 1
        continue

    # حفظ الملف
    filename = clean_filename(title) + ".txt"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Title: {title}\n\n")
        f.write(content)

    print(f"✅ Saved: {title}")
    success += 1

    time.sleep(0.3)


print("\n--- DONE ---")
print(f"Success: {success}")
print(f"Failed: {failed}")