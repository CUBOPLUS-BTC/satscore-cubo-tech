"""HTTP route handlers for the Bitcoin education module.

All handlers follow the project convention: return ``(body_dict, status_code)``.
The HTTP server layer is responsible for JSON serialisation.

Endpoints
---------
GET  /education/glossary
     Query params:
       - q          : search query (optional)
       - category   : filter by category (optional)
       - difficulty : filter by difficulty (optional)
       - locale     : "en" | "es"  (default "en")

GET  /education/lessons
     Query params:
       - category   : filter by category (optional)
       - difficulty : filter by difficulty (optional)
       - locale     : "en" | "es"  (default "en")

GET  /education/lessons/<id>
     Query params:
       - locale     : "en" | "es"  (default "en")

POST /education/quiz
     Body:
       - lesson_id  : str
       - answers    : list[int]  — 0-based index of chosen option per question
       - locale     : "en" | "es"  (default "en")
"""

from __future__ import annotations

from .glossary import GLOSSARY, search_glossary, get_by_category, get_by_difficulty
from .lessons import LESSONS, get_lesson, list_lessons

# ---------------------------------------------------------------------------
# Glossary handler
# ---------------------------------------------------------------------------


def handle_glossary(query: dict) -> tuple[dict, int]:
    """GET /education/glossary

    Accepts optional query parameters:
      - q          : free-text search
      - category   : filter by category
      - difficulty : filter by difficulty level
      - locale     : "en" or "es" (affects search text preference)

    Returns a list of glossary entries.  If multiple filters are supplied the
    results are intersected.
    """
    try:
        q = (query.get("q") or "").strip()
        category = (query.get("category") or "").strip().lower()
        difficulty = (query.get("difficulty") or "").strip().lower()
        locale = (query.get("locale") or "en").strip().lower()

        if locale not in ("en", "es"):
            return {"detail": "Invalid locale. Use 'en' or 'es'."}, 400

        # Start with all entries
        if q:
            results = search_glossary(q, locale=locale)
        else:
            results = [{"key": k, **v} for k, v in GLOSSARY.items()]

        # Apply category filter
        if category:
            try:
                by_cat = {e["key"] for e in get_by_category(category)}
                results = [r for r in results if r["key"] in by_cat]
            except ValueError as exc:
                return {"detail": str(exc)}, 400

        # Apply difficulty filter
        if difficulty:
            try:
                by_diff = {e["key"] for e in get_by_difficulty(difficulty)}
                results = [r for r in results if r["key"] in by_diff]
            except ValueError as exc:
                return {"detail": str(exc)}, 400

        # Build locale-specific response (flatten to single-language fields)
        formatted = []
        for entry in results:
            formatted.append(
                {
                    "key": entry["key"],
                    "term": entry.get(f"term{'_es' if locale == 'es' else ''}") or entry.get("term"),
                    "definition": entry.get(f"definition_{locale}") or entry.get("definition_en", ""),
                    "category": entry.get("category"),
                    "difficulty": entry.get("difficulty"),
                    "related_terms": entry.get("related_terms", []),
                    "example": entry.get(f"example_{locale}") or entry.get("example_en", ""),
                }
            )

        # Sort alphabetically by term
        formatted.sort(key=lambda e: e["term"].lower())

        return {
            "total": len(formatted),
            "locale": locale,
            "filters": {
                "q": q or None,
                "category": category or None,
                "difficulty": difficulty or None,
            },
            "results": formatted,
        }, 200

    except Exception as exc:
        return {"detail": f"Glossary error: {exc}"}, 500


# ---------------------------------------------------------------------------
# Lesson list handler
# ---------------------------------------------------------------------------


def handle_lesson_list(query: dict) -> tuple[dict, int]:
    """GET /education/lessons

    Accepts optional query parameters:
      - category   : filter by lesson category
      - difficulty : filter by difficulty level
      - locale     : "en" or "es" (affects which title/description fields are returned)
    """
    try:
        category = (query.get("category") or "").strip().lower() or None
        difficulty = (query.get("difficulty") or "").strip().lower() or None
        locale = (query.get("locale") or "en").strip().lower()

        if locale not in ("en", "es"):
            return {"detail": "Invalid locale. Use 'en' or 'es'."}, 400

        lessons = list_lessons(category=category, difficulty=difficulty)

        # Return locale-specific fields
        locale_lessons = []
        for lesson in lessons:
            locale_lessons.append(
                {
                    "id": lesson["id"],
                    "title": lesson[f"title_{locale}"],
                    "description": lesson[f"description_{locale}"],
                    "category": lesson["category"],
                    "difficulty": lesson["difficulty"],
                    "duration_min": lesson["duration_min"],
                    "quiz_count": lesson["quiz_count"],
                }
            )

        return {
            "total": len(locale_lessons),
            "locale": locale,
            "filters": {
                "category": category,
                "difficulty": difficulty,
            },
            "lessons": locale_lessons,
        }, 200

    except Exception as exc:
        return {"detail": f"Lesson list error: {exc}"}, 500


# ---------------------------------------------------------------------------
# Lesson detail handler
# ---------------------------------------------------------------------------


def handle_lesson_detail(query: dict) -> tuple[dict, int]:
    """GET /education/lessons/<id>

    Required query parameter (or path-injected):
      - id     : lesson slug
      - locale : "en" or "es"
    """
    try:
        lesson_id = (query.get("id") or "").strip()
        locale = (query.get("locale") or "en").strip().lower()

        if not lesson_id:
            return {"detail": "Missing required parameter: id"}, 400
        if locale not in ("en", "es"):
            return {"detail": "Invalid locale. Use 'en' or 'es'."}, 400

        lesson = get_lesson(lesson_id)
        if lesson is None:
            return {"detail": f"Lesson '{lesson_id}' not found."}, 404

        # Build locale-specific quiz (strip alternate-language fields)
        quiz = []
        for q in lesson.get("quiz", []):
            quiz.append(
                {
                    "question": q[f"question_{locale}"],
                    "options": q["options"],
                    "explanation": q[f"explanation_{locale}"],
                    # Do NOT send correct_index to the client — only used in POST /quiz
                }
            )

        return {
            "id": lesson["id"],
            "title": lesson[f"title_{locale}"],
            "description": lesson[f"description_{locale}"],
            "category": lesson["category"],
            "difficulty": lesson["difficulty"],
            "duration_min": lesson["duration_min"],
            "content": lesson[f"content_{locale}"],
            "quiz": quiz,
            "locale": locale,
        }, 200

    except Exception as exc:
        return {"detail": f"Lesson detail error: {exc}"}, 500


# ---------------------------------------------------------------------------
# Quiz answer handler
# ---------------------------------------------------------------------------


def handle_quiz(body: dict) -> tuple[dict, int]:
    """POST /education/quiz

    Expected body fields:
      - lesson_id : str  — the lesson slug
      - answers   : list[int]  — 0-based chosen option index per question
      - locale    : "en" | "es"  (default "en")

    Returns per-question feedback (correct/incorrect, explanation) and
    an overall score.
    """
    try:
        lesson_id = (body.get("lesson_id") or "").strip()
        answers = body.get("answers")
        locale = (body.get("locale") or "en").strip().lower()

        # Validate inputs
        if not lesson_id:
            return {"detail": "Missing required field: lesson_id"}, 400
        if answers is None:
            return {"detail": "Missing required field: answers"}, 400
        if not isinstance(answers, list):
            return {"detail": "Field 'answers' must be a list of integers."}, 400
        if locale not in ("en", "es"):
            return {"detail": "Invalid locale. Use 'en' or 'es'."}, 400

        lesson = get_lesson(lesson_id)
        if lesson is None:
            return {"detail": f"Lesson '{lesson_id}' not found."}, 404

        quiz = lesson.get("quiz", [])
        if len(answers) != len(quiz):
            return {
                "detail": (
                    f"Expected {len(quiz)} answers for lesson '{lesson_id}', "
                    f"got {len(answers)}."
                )
            }, 400

        # Grade each question
        results = []
        correct_count = 0
        for i, (question, chosen_idx) in enumerate(zip(quiz, answers)):
            if not isinstance(chosen_idx, int):
                return {
                    "detail": f"Answer at index {i} must be an integer (0-based option index)."
                }, 400

            is_correct = chosen_idx == question["correct_index"]
            if is_correct:
                correct_count += 1

            results.append(
                {
                    "question_number": i + 1,
                    "question": question[f"question_{locale}"],
                    "chosen_index": chosen_idx,
                    "correct_index": question["correct_index"],
                    "is_correct": is_correct,
                    "explanation": question[f"explanation_{locale}"],
                }
            )

        total = len(quiz)
        score_pct = round(correct_count / total * 100, 1) if total else 0.0

        # Determine pass/fail (60% threshold)
        passed = score_pct >= 60.0

        return {
            "lesson_id": lesson_id,
            "locale": locale,
            "score": {
                "correct": correct_count,
                "total": total,
                "percentage": score_pct,
                "passed": passed,
                "grade": _grade_label(score_pct, locale),
            },
            "results": results,
        }, 200

    except Exception as exc:
        return {"detail": f"Quiz error: {exc}"}, 500


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _grade_label(score_pct: float, locale: str) -> str:
    """Return a human-readable grade label based on score percentage."""
    if score_pct == 100:
        return "Perfect!" if locale == "en" else "¡Perfecto!"
    if score_pct >= 80:
        return "Excellent" if locale == "en" else "Excelente"
    if score_pct >= 60:
        return "Good — keep learning" if locale == "en" else "Bien — sigue aprendiendo"
    return "Keep practicing" if locale == "en" else "Sigue practicando"
