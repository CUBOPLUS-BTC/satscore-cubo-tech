"""Bitcoin educational content module.

Provides a bilingual (English / Spanish) glossary of Bitcoin terminology
and a structured curriculum of lessons with quizzes.  Every piece of
content in this module is Bitcoin-specific — no altcoins.

Public surface
--------------
Glossary
  - GLOSSARY            : dict[str, GlossaryEntry]
  - search_glossary()   : full-text search across terms and definitions
  - get_by_category()   : filter by topic category
  - get_by_difficulty() : filter by beginner / intermediate / advanced

Lessons
  - LESSONS             : list[LessonDict]
  - get_lesson()        : retrieve single lesson by id
  - list_lessons()      : filtered listing helper

Routes (HTTP handlers, return (body_dict, status_code))
  - handle_glossary()
  - handle_lesson_list()
  - handle_lesson_detail()
  - handle_quiz()
"""

from .glossary import (
    GLOSSARY,
    search_glossary,
    get_by_category,
    get_by_difficulty,
)
from .lessons import LESSONS, get_lesson, list_lessons
from .routes import (
    handle_glossary,
    handle_lesson_list,
    handle_lesson_detail,
    handle_quiz,
)

__all__ = [
    # glossary
    "GLOSSARY",
    "search_glossary",
    "get_by_category",
    "get_by_difficulty",
    # lessons
    "LESSONS",
    "get_lesson",
    "list_lessons",
    # routes
    "handle_glossary",
    "handle_lesson_list",
    "handle_lesson_detail",
    "handle_quiz",
]
