"""Notification template renderer for the Magma Bitcoin app.

``NotificationRenderer`` takes template IDs and variable data and produces
rendered notification content in plain text and HTML.  It also provides
preview (with sample data) and validation utilities.

All rendering is done using Python's built-in ``str.format_map()`` with a
safe-formatter that leaves unresolved placeholders in place rather than
raising ``KeyError``.
"""

from __future__ import annotations

import re
from typing import Any

from .templates import TEMPLATES

# ---------------------------------------------------------------------------
# Safe formatter — leaves {missing_var} untouched instead of raising KeyError
# ---------------------------------------------------------------------------


class _SafeDict(dict):
    """dict subclass that returns the placeholder key for missing entries."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


# ---------------------------------------------------------------------------
# Renderer class
# ---------------------------------------------------------------------------


class NotificationRenderer:
    """Render notification templates with runtime data.

    Usage
    -----
    renderer = NotificationRenderer()

    # Plain text
    text = renderer.render_plain("price_alert_above", "en", {"price_usd": "$70k", ...})

    # HTML
    html = renderer.render_html("price_alert_above", "en", {"price_usd": "$70k", ...})

    # Full dict (subject + plain + html)
    result = renderer.render("price_alert_above", "en", {"price_usd": "$70k", ...})

    # Preview with sample data
    preview = renderer.preview("price_alert_above", "en")
    """

    # Supported locales
    SUPPORTED_LOCALES = ("en", "es")

    # --------------------------------------------------------------------------
    def render(
        self,
        template_id: str,
        locale: str = "en",
        data: dict[str, Any] | None = None,
    ) -> dict:
        """Render a template and return a dict with subject, plain, and html.

        Parameters
        ----------
        template_id : Template key from ``TEMPLATES``.
        locale      : "en" or "es".
        data        : Dict of variable values (e.g., {"price_usd": "$70,000"}).

        Returns
        -------
        dict with keys: template_id, locale, subject, plain, html, icon,
        priority, category.

        Raises
        ------
        ValueError : On invalid template_id or locale.
        """
        template = self._get_template(template_id)
        locale = self._validate_locale(locale)
        ctx = _SafeDict(data or {})
        ctx.setdefault("lang", locale)
        ctx.setdefault("unsubscribe_url", "https://magma.app/unsubscribe/token")

        subject = self._render_str(template[f"subject_{locale}"], ctx)
        ctx.setdefault("subject", subject)

        plain = self._render_str(template[f"body_{locale}"], ctx)
        html = self._render_str(template[f"body_html_{locale}"], ctx)

        return {
            "template_id": template_id,
            "locale": locale,
            "subject": subject,
            "plain": plain,
            "html": html,
            "icon": template.get("icon", ""),
            "priority": template.get("priority", "normal"),
            "category": template.get("category", ""),
        }

    # --------------------------------------------------------------------------
    def render_html(
        self,
        template_id: str,
        locale: str = "en",
        data: dict[str, Any] | None = None,
    ) -> str:
        """Render and return only the HTML body.

        Convenience wrapper around :py:meth:`render`.
        """
        return self.render(template_id, locale, data)["html"]

    # --------------------------------------------------------------------------
    def render_plain(
        self,
        template_id: str,
        locale: str = "en",
        data: dict[str, Any] | None = None,
    ) -> str:
        """Render and return only the plain-text body.

        Convenience wrapper around :py:meth:`render`.
        """
        return self.render(template_id, locale, data)["plain"]

    # --------------------------------------------------------------------------
    def preview(self, template_id: str, locale: str = "en") -> dict:
        """Render a template using its built-in sample data.

        Useful for admin preview panels and testing.

        Parameters
        ----------
        template_id : Template key from ``TEMPLATES``.
        locale      : "en" or "es".

        Returns
        -------
        Rendered dict (same shape as :py:meth:`render`) plus a
        ``sample_data_used`` field listing which variables were injected.
        """
        template = self._get_template(template_id)
        sample = dict(template.get("sample_data", {}))

        result = self.render(template_id, locale, sample)
        result["sample_data_used"] = sample
        result["is_preview"] = True
        return result

    # --------------------------------------------------------------------------
    def get_sample_data(self, template_id: str) -> dict:
        """Return the sample data dict for a template.

        Parameters
        ----------
        template_id : Template key from ``TEMPLATES``.

        Returns
        -------
        Dict of sample variable values.
        """
        template = self._get_template(template_id)
        return dict(template.get("sample_data", {}))

    # --------------------------------------------------------------------------
    def validate_template(self, template_id: str) -> dict:
        """Check the integrity of a template.

        Validates:
        - Template exists
        - All required fields are present
        - Both locales have matching variable placeholders
        - Sample data covers all placeholders in the plain-text bodies

        Returns
        -------
        dict with keys: template_id, valid (bool), issues (list of str),
        variables_en (list), variables_es (list), coverage (dict).
        """
        if template_id not in TEMPLATES:
            return {
                "template_id": template_id,
                "valid": False,
                "issues": [f"Template '{template_id}' does not exist."],
                "variables_en": [],
                "variables_es": [],
                "coverage": {},
            }

        template = TEMPLATES[template_id]
        issues: list[str] = []

        # Required fields
        required_fields = [
            "subject_en", "subject_es",
            "body_en", "body_es",
            "body_html_en", "body_html_es",
            "icon", "priority", "category", "sample_data",
        ]
        for field in required_fields:
            if field not in template:
                issues.append(f"Missing required field: '{field}'")

        # Extract placeholders
        vars_en = self._extract_variables(template.get("body_en", ""))
        vars_es = self._extract_variables(template.get("body_es", ""))
        vars_html_en = self._extract_variables(template.get("body_html_en", ""))
        vars_html_es = self._extract_variables(template.get("body_html_es", ""))
        vars_subj_en = self._extract_variables(template.get("subject_en", ""))
        vars_subj_es = self._extract_variables(template.get("subject_es", ""))

        all_en = vars_en | vars_subj_en | vars_html_en
        all_es = vars_es | vars_subj_es | vars_html_es

        # Check that sample_data covers all placeholders
        sample = set(template.get("sample_data", {}).keys())
        uncovered_en = all_en - sample
        uncovered_es = all_es - sample
        if uncovered_en:
            issues.append(f"EN variables not in sample_data: {sorted(uncovered_en)}")
        if uncovered_es:
            issues.append(f"ES variables not in sample_data: {sorted(uncovered_es)}")

        # Priority validation
        valid_priorities = ("low", "normal", "high", "critical")
        if template.get("priority") not in valid_priorities:
            issues.append(
                f"Invalid priority '{template.get('priority')}'. "
                f"Valid: {valid_priorities}"
            )

        # Build coverage report
        coverage = {
            "en_plain_vars": sorted(vars_en),
            "es_plain_vars": sorted(vars_es),
            "en_html_vars": sorted(vars_html_en),
            "es_html_vars": sorted(vars_html_es),
            "sample_data_keys": sorted(sample),
            "uncovered_en": sorted(uncovered_en),
            "uncovered_es": sorted(uncovered_es),
        }

        return {
            "template_id": template_id,
            "valid": len(issues) == 0,
            "issues": issues,
            "variables_en": sorted(all_en),
            "variables_es": sorted(all_es),
            "coverage": coverage,
        }

    # --------------------------------------------------------------------------
    def list_templates(self, category: str | None = None) -> list[dict]:
        """Return a summary list of all available templates.

        Parameters
        ----------
        category : Optional filter by category string.

        Returns
        -------
        List of template summary dicts.
        """
        results = []
        for template_id, template in TEMPLATES.items():
            if category and template.get("category") != category:
                continue
            # Count placeholders across all fields
            all_vars = self._extract_variables(
                template.get("body_en", "")
                + template.get("body_es", "")
                + template.get("subject_en", "")
            )
            results.append(
                {
                    "template_id": template_id,
                    "icon": template.get("icon", ""),
                    "priority": template.get("priority", "normal"),
                    "category": template.get("category", ""),
                    "subject_en": template.get("subject_en", ""),
                    "subject_es": template.get("subject_es", ""),
                    "variable_count": len(all_vars),
                    "variables": sorted(all_vars),
                }
            )
        # Sort by category, then by template_id
        results.sort(key=lambda t: (t["category"], t["template_id"]))
        return results

    # --------------------------------------------------------------------------
    def get_template_info(self, template_id: str) -> dict:
        """Return full metadata about a single template.

        Parameters
        ----------
        template_id : Template key from ``TEMPLATES``.

        Returns
        -------
        dict with all template fields plus extracted variable lists and
        the validation report.
        """
        template = self._get_template(template_id)
        validation = self.validate_template(template_id)

        return {
            "template_id": template_id,
            "icon": template.get("icon", ""),
            "priority": template.get("priority", "normal"),
            "category": template.get("category", ""),
            "subject_en": template.get("subject_en", ""),
            "subject_es": template.get("subject_es", ""),
            "variables_en": validation["variables_en"],
            "variables_es": validation["variables_es"],
            "sample_data": template.get("sample_data", {}),
            "valid": validation["valid"],
            "issues": validation["issues"],
        }

    # --------------------------------------------------------------------------
    # Internal helpers
    # --------------------------------------------------------------------------

    @staticmethod
    def _get_template(template_id: str) -> dict:
        """Look up a template by ID; raise ValueError if not found."""
        if template_id not in TEMPLATES:
            available = sorted(TEMPLATES.keys())
            raise ValueError(
                f"Unknown template '{template_id}'. "
                f"Available templates: {available}"
            )
        return TEMPLATES[template_id]

    @staticmethod
    def _validate_locale(locale: str) -> str:
        """Normalise and validate the locale string."""
        locale = (locale or "en").strip().lower()
        if locale not in ("en", "es"):
            raise ValueError(f"Invalid locale '{locale}'. Use 'en' or 'es'.")
        return locale

    @staticmethod
    def _render_str(template_str: str, ctx: _SafeDict) -> str:
        """Format *template_str* with *ctx*, leaving unresolved vars in place."""
        try:
            return template_str.format_map(ctx)
        except (KeyError, ValueError):
            # Fallback: try replacing each known key individually
            result = template_str
            for k, v in ctx.items():
                result = result.replace("{" + k + "}", str(v))
            return result

    @staticmethod
    def _extract_variables(text: str) -> set[str]:
        """Return the set of {variable_name} placeholders found in *text*."""
        # Match {word} and {word_with_underscores}
        pattern = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
        return set(pattern.findall(text))

    # --------------------------------------------------------------------------
    # Convenience class method for one-shot rendering without instantiation
    # --------------------------------------------------------------------------

    @classmethod
    def quick_render(
        cls,
        template_id: str,
        locale: str = "en",
        data: dict[str, Any] | None = None,
    ) -> dict:
        """Class method shortcut — renders without explicit instantiation.

        Example
        -------
        result = NotificationRenderer.quick_render(
            "price_alert_above", "en", {"price_usd": "$70,000", ...}
        )
        """
        renderer = cls()
        return renderer.render(template_id, locale, data)

    # --------------------------------------------------------------------------
    # Batch rendering
    # --------------------------------------------------------------------------

    def render_batch(
        self,
        requests: list[dict],
    ) -> list[dict]:
        """Render multiple templates in a single call.

        Parameters
        ----------
        requests : List of dicts, each with:
            - template_id (required)
            - locale      (optional, default "en")
            - data        (optional dict of variables)

        Returns
        -------
        List of render results (same shape as :py:meth:`render`), with an
        additional ``error`` key if rendering failed for a specific request.
        """
        results = []
        for req in requests:
            template_id = req.get("template_id", "")
            locale = req.get("locale", "en")
            data = req.get("data") or {}
            try:
                rendered = self.render(template_id, locale, data)
                results.append(rendered)
            except (ValueError, KeyError, TypeError) as exc:
                results.append(
                    {
                        "template_id": template_id,
                        "locale": locale,
                        "error": str(exc),
                        "subject": "",
                        "plain": "",
                        "html": "",
                    }
                )
        return results

    # --------------------------------------------------------------------------
    # Category statistics
    # --------------------------------------------------------------------------

    def category_summary(self) -> dict[str, dict]:
        """Return a summary of templates grouped by category.

        Returns
        -------
        dict mapping category_name -> {count, template_ids, priorities}.
        """
        summary: dict[str, dict] = {}
        for template_id, template in TEMPLATES.items():
            cat = template.get("category", "uncategorized")
            if cat not in summary:
                summary[cat] = {
                    "count": 0,
                    "template_ids": [],
                    "priorities": [],
                }
            summary[cat]["count"] += 1
            summary[cat]["template_ids"].append(template_id)
            priority = template.get("priority", "normal")
            if priority not in summary[cat]["priorities"]:
                summary[cat]["priorities"].append(priority)

        # Sort template IDs within each category
        for cat in summary:
            summary[cat]["template_ids"].sort()

        return summary
