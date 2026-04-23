"""
Internationalization (i18n) module for Magma Bitcoin app.
Provides translation, locale detection, and locale-aware number/date formatting.
"""

from .translator import Translator, LocaleManager
from .formatter import NumberFormatter, DateFormatter, MessageFormatter

__all__ = [
    "Translator",
    "LocaleManager",
    "NumberFormatter",
    "DateFormatter",
    "MessageFormatter",
]

# Module-level singleton translator (configure with set_default_locale)
_translator = Translator(default_locale="en")


def t(key: str, locale: str = None, **kwargs) -> str:
    """Shorthand global translate function."""
    return _translator.translate(key, locale=locale, **kwargs)


def set_default_locale(code: str) -> None:
    """Set the module-level default locale."""
    _translator.set_locale(code)


def get_translator() -> Translator:
    """Return the module-level Translator singleton."""
    return _translator
