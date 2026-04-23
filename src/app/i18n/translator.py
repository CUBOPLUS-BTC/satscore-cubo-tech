"""
Translation system for Magma Bitcoin app.
Provides locale detection, key-based translation with interpolation,
and locale metadata management.
Pure Python stdlib — no third-party dependencies.
"""

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Locale metadata
# ---------------------------------------------------------------------------

_LOCALE_INFO = {
    "en": {
        "name":       "English",
        "native":     "English",
        "direction":  "ltr",
        "currency":   "USD",
        "date_format": "MM/DD/YYYY",
        "number_sep":  {"thousands": ",", "decimal": "."},
        "territory":  "US",
    },
    "es": {
        "name":       "Spanish",
        "native":     "Español",
        "direction":  "ltr",
        "currency":   "USD",
        "date_format": "DD/MM/YYYY",
        "number_sep":  {"thousands": ".", "decimal": ","},
        "territory":  "SV",
    },
    "pt": {
        "name":       "Portuguese",
        "native":     "Português",
        "direction":  "ltr",
        "currency":   "BRL",
        "date_format": "DD/MM/YYYY",
        "number_sep":  {"thousands": ".", "decimal": ","},
        "territory":  "BR",
    },
    "fr": {
        "name":       "French",
        "native":     "Français",
        "direction":  "ltr",
        "currency":   "EUR",
        "date_format": "DD/MM/YYYY",
        "number_sep":  {"thousands": " ", "decimal": ","},
        "territory":  "FR",
    },
    "de": {
        "name":       "German",
        "native":     "Deutsch",
        "direction":  "ltr",
        "currency":   "EUR",
        "date_format": "DD.MM.YYYY",
        "number_sep":  {"thousands": ".", "decimal": ","},
        "territory":  "DE",
    },
    "ar": {
        "name":       "Arabic",
        "native":     "العربية",
        "direction":  "rtl",
        "currency":   "USD",
        "date_format": "DD/MM/YYYY",
        "number_sep":  {"thousands": ",", "decimal": "."},
        "territory":  "SA",
    },
    "zh": {
        "name":       "Chinese (Simplified)",
        "native":     "中文",
        "direction":  "ltr",
        "currency":   "CNY",
        "date_format": "YYYY/MM/DD",
        "number_sep":  {"thousands": ",", "decimal": "."},
        "territory":  "CN",
    },
    "ja": {
        "name":       "Japanese",
        "native":     "日本語",
        "direction":  "ltr",
        "currency":   "JPY",
        "date_format": "YYYY/MM/DD",
        "number_sep":  {"thousands": ",", "decimal": "."},
        "territory":  "JP",
    },
}

_INTERPOLATION_PATTERN = re.compile(r"\{(\w+)\}")


# ---------------------------------------------------------------------------
# LocaleManager
# ---------------------------------------------------------------------------

class LocaleManager:
    """
    Manages locale registrations and metadata.
    Locales can be registered dynamically at runtime.
    """

    def __init__(self) -> None:
        self._translations: dict[str, dict] = {}
        self._default: str = "en"
        self._load_bundled_locales()

    def _load_bundled_locales(self) -> None:
        """Load the bundled en and es translation dicts."""
        try:
            from .locales import AVAILABLE
            for code, translations in AVAILABLE.items():
                self._translations[code] = translations
        except Exception:
            # Fallback: empty translations
            self._translations = {"en": {}, "es": {}}

    def register_locale(self, code: str, translations: dict) -> None:
        """
        Register (or replace) a locale with a translations dict.
        ``code`` should be a BCP-47 language tag (e.g. "en", "es", "pt-BR").
        """
        if not isinstance(code, str) or not code:
            raise ValueError("Locale code must be a non-empty string")
        if not isinstance(translations, dict):
            raise TypeError("translations must be a dict")

        normalized = code.lower().replace("-", "_")
        self._translations[normalized] = translations

    def set_default(self, code: str) -> None:
        """Set the default fallback locale."""
        code = code.lower().replace("-", "_")
        if code not in self._translations:
            raise ValueError(f"Locale {code!r} not registered")
        self._default = code

    def get_locale_info(self, code: str) -> dict:
        """Return metadata for a locale (name, direction, date format, etc.)."""
        code = code.lower().split("_")[0].split("-")[0]
        return dict(_LOCALE_INFO.get(code, _LOCALE_INFO.get("en", {})))

    def get_translations(self, locale: str) -> dict:
        """Return the full translations dict for a locale (with en fallback)."""
        normalized = self._normalize(locale)
        return dict(self._translations.get(normalized, self._translations.get("en", {})))

    def get_available_locales(self) -> list:
        """Return a list of registered locale codes."""
        return sorted(self._translations.keys())

    def _normalize(self, code: str) -> str:
        if not isinstance(code, str):
            return self._default
        normalized = code.lower().replace("-", "_")
        # Exact match
        if normalized in self._translations:
            return normalized
        # Language-only match (e.g. "en_us" → "en")
        lang = normalized.split("_")[0]
        if lang in self._translations:
            return lang
        return self._default


# ---------------------------------------------------------------------------
# Translator
# ---------------------------------------------------------------------------

class Translator:
    """
    Core translation engine.
    Looks up keys in the registered locale dict and falls back to English.
    Supports {variable} interpolation in translation strings.
    """

    def __init__(self, default_locale: str = "en") -> None:
        self._manager = LocaleManager()
        self._default = default_locale
        try:
            self._manager.set_default(default_locale)
        except Exception:
            pass

    def set_locale(self, code: str) -> None:
        """Change the default locale."""
        try:
            self._manager.set_default(code)
            self._default = code
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Core translation
    # ------------------------------------------------------------------

    def translate(self, key: str, locale: str = None, **kwargs) -> str:
        """
        Translate a dot-separated key into the target locale.

        Falls back to English if the key is not found in the target locale.
        Falls back to the key itself if not found in English either.

        Supports {variable} interpolation::

            translator.translate("auth.rate_limited", locale="es", wait_seconds=30)
            # → "Demasiados intentos... Espere 30 segundos."
        """
        target_locale = locale or self._default
        normalized = self._manager._normalize(target_locale)

        # Try target locale first
        translations = self._manager.get_translations(normalized)
        template = translations.get(key)

        # Fallback to English
        if template is None and normalized != "en":
            en_translations = self._manager.get_translations("en")
            template = en_translations.get(key)

        # Last resort: return the key itself
        if template is None:
            return key

        # Interpolate
        if kwargs:
            return self._interpolate(template, kwargs)

        return template

    def t(self, key: str, locale: str = None, **kwargs) -> str:
        """Shorthand for translate()."""
        return self.translate(key, locale=locale, **kwargs)

    # ------------------------------------------------------------------
    # Locale detection
    # ------------------------------------------------------------------

    def get_locale(self, accept_language: str) -> str:
        """
        Parse an HTTP Accept-Language header and return the best matching
        registered locale code.

        Example: "es-SV,es;q=0.9,en-US;q=0.8,en;q=0.7" → "es"
        """
        if not accept_language:
            return self._default

        available = set(self._manager.get_available_locales())
        candidates: list = []

        for part in accept_language.split(","):
            part = part.strip()
            if not part:
                continue

            if ";q=" in part:
                lang, q_str = part.split(";q=", 1)
                try:
                    quality = float(q_str)
                except ValueError:
                    quality = 1.0
            else:
                lang   = part
                quality = 1.0

            lang = lang.strip().lower().replace("-", "_")
            candidates.append((quality, lang))

        # Sort by quality descending
        candidates.sort(key=lambda x: -x[0])

        for _, lang in candidates:
            # Exact match
            if lang in available:
                return lang
            # Language-only
            base = lang.split("_")[0]
            if base in available:
                return base

        return self._default

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_available_locales(self) -> list:
        """Return a list of all available locale codes."""
        return self._manager.get_available_locales()

    def get_translations(self, locale: str) -> dict:
        """Return the full translation dict for a locale."""
        return self._manager.get_translations(locale)

    def has_translation(self, key: str, locale: str) -> bool:
        """Return True if the key exists in the given locale."""
        translations = self._manager.get_translations(locale)
        return key in translations

    def get_missing_translations(self, locale: str) -> list:
        """
        Compare the given locale against English and return keys that
        are present in English but missing in the target locale.
        """
        en_keys  = set(self._manager.get_translations("en").keys())
        loc_keys = set(self._manager.get_translations(locale).keys())
        return sorted(en_keys - loc_keys)

    def get_locale_info(self, code: str) -> dict:
        """Return metadata for a locale."""
        return self._manager.get_locale_info(code)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _interpolate(self, template: str, variables: dict) -> str:
        """Replace {variable} placeholders in a template string."""
        def replace(match: re.Match) -> str:
            var_name = match.group(1)
            value = variables.get(var_name)
            if value is None:
                return match.group(0)  # Leave unreplaced if not provided
            return str(value)

        return _INTERPOLATION_PATTERN.sub(replace, template)

    def bulk_translate(self, keys: list, locale: str = None) -> dict:
        """
        Translate multiple keys at once.
        Returns a dict mapping key → translated string.
        """
        return {key: self.translate(key, locale=locale) for key in keys}

    def translate_dict(self, data: dict, locale: str = None) -> dict:
        """
        Recursively translate all string values in a dict that start with 'i18n:'.
        Useful for translating API responses that embed translation keys.
        """
        result = {}
        for k, v in data.items():
            if isinstance(v, str) and v.startswith("i18n:"):
                result[k] = self.translate(v[5:], locale=locale)
            elif isinstance(v, dict):
                result[k] = self.translate_dict(v, locale=locale)
            elif isinstance(v, list):
                result[k] = [
                    self.translate_dict(item, locale=locale)
                    if isinstance(item, dict)
                    else item
                    for item in v
                ]
            else:
                result[k] = v
        return result
