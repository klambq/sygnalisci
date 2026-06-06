import json
import re
from pathlib import Path

import pdfplumber


PDF_PATH = next(Path(".").glob("Ochrona sygnalist*w + zagadnienia.pdf"))
OUTPUT_PATH = "baza_pytan.json"

QUESTION_RE = re.compile(r"^(\d+)\.\s+(.*)$")
OPTION_RE = re.compile(r"^([A-Ea-e])\s*[\.)]\s*(.*)$")
ANSWER_RE = re.compile(r"(?<!\w)([A-D](?:,\s*[A-D])*)(?!\w)")
ARTICLE_PREFIX_RE = re.compile(r"^\d+(?:,\s*\d+)*,?\s+")


def clean_line(line):
    line = re.sub(r"\s+Z komentarzem\s+\[MM\d+\]:.*$", "", line)
    return re.sub(r"\s+", " ", line).strip()


def clean_text(text):
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("ae prawdziwe", "prawdziwe")
    text = text.replace(
        "przekraczającej przekraczającej progi unijne. progi unijne:",
        "przekraczającej progi unijne:",
    )
    text = text.replace(
        "przekraczającej przekraczającej progi unijne progi unijne:",
        "przekraczającej progi unijne:",
    )
    text = text.replace(
        "przed terminem otwarcia przekraczającej progi unijne.",
        "przed terminem otwarcia",
    )
    return text


def split_question_line(rest):
    matches = list(ANSWER_RE.finditer(rest))
    if not matches:
        return None, None

    answer_match = matches[-1]
    question_text = rest[: answer_match.start()].strip()
    question_text = ARTICLE_PREFIX_RE.sub("", question_text, count=1).strip()
    correct_answers = [
        answer.strip().lower() for answer in answer_match.group(1).split(",")
    ]
    return question_text, correct_answers


def append_question(questions, question):
    if not question:
        return

    question["text"] = clean_text(question["text"])
    question["correct_answers"] = sorted(set(question["correct_answers"]))
    question["options"] = {
        key: clean_text(value) for key, value in question["options"].items()
    }
    questions.append(question)


def extract_questions(pdf_path):
    questions = []
    current_question = None
    current_option = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
            for raw_line in page_text.splitlines():
                line = clean_line(raw_line)
                if (
                    not line
                    or line.startswith("NR. ")
                    or line.startswith("GRUPA ")
                ):
                    continue

                question_match = QUESTION_RE.match(line)
                if question_match:
                    question_text, correct_answers = split_question_line(
                        question_match.group(2).strip()
                    )
                    if question_text is not None:
                        append_question(questions, current_question)
                        current_question = {
                            "id": int(question_match.group(1)),
                            "text": question_text,
                            "options": {},
                            "correct_answers": correct_answers,
                        }
                        current_option = None
                        continue

                option_match = OPTION_RE.match(line)
                if option_match and current_question:
                    current_option = option_match.group(1).lower()
                    current_question["options"][current_option] = clean_line(
                        option_match.group(2)
                    )
                    continue

                if current_question:
                    if current_option:
                        current_question["options"][current_option] += " " + line
                    else:
                        current_question["text"] += " " + line

    append_question(questions, current_question)
    return questions


def validate_questions(questions):
    ids = [question["id"] for question in questions]
    missing_ids = [number for number in range(min(ids), max(ids) + 1) if number not in ids]
    without_options = [question["id"] for question in questions if not question["options"]]
    without_answers = [
        question["id"] for question in questions if not question["correct_answers"]
    ]
    invalid_answers = [
        question["id"]
        for question in questions
        if not set(question["correct_answers"]).issubset(question["options"])
    ]

    return {
        "missing_ids": missing_ids,
        "without_options": without_options,
        "without_answers": without_answers,
        "invalid_answers": invalid_answers,
    }


if __name__ == "__main__":
    data = extract_questions(PDF_PATH)
    validation = validate_questions(data)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print(f"Extracted {len(data)} questions.")
    print(f"Missing IDs: {validation['missing_ids']}")
    print(f"Without options: {validation['without_options']}")
    print(f"Without answers: {validation['without_answers']}")
    print(f"Invalid answers: {validation['invalid_answers']}")
