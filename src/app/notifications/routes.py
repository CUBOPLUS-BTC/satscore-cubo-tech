"""HTTP route handlers for the notification template system.

All handlers follow the project convention: return ``(body_dict, status_code)``.

Endpoints
---------
GET  /notifications/templates
     Query params:
       - category : optional filter by category
       - locale   : "en" | "es" (default "en") — affects subject preview

POST /notifications/preview
     Body:
       - template_id : str    — required
       - locale      : str    — "en" | "es" (default "en")

POST /notifications/render
     Body:
       - template_id : str    — required
       - locale      : str    — "en" | "es" (default "en")
       - data        : dict   — variable values for interpolation
       - format      : str    — "full" | "plain" | "html" | "subject" (default "full")
"""

from __future__ import annotations

from .renderer import NotificationRenderer

_renderer = NotificationRenderer()


def handle_notification_templates(query: dict) -> tuple[dict, int]:
    """GET /notifications/templates

    Returns a list of available notification templates, optionally filtered
    by category.  Each entry includes the template ID, icon, priority,
    category, subject previews in both locales, and the variable list.
    """
    try:
        category = (query.get("category") or "").strip().lower() or None
        locale = (query.get("locale") or "en").strip().lower()

        if locale not in ("en", "es"):
            return {"detail": "Invalid locale. Use 'en' or 'es'."}, 400

        templates = _renderer.list_templates(category=category)

        # Add validation status to each summary
        enriched = []
        for tmpl in templates:
            validation = _renderer.validate_template(tmpl["template_id"])
            enriched.append(
                {
                    **tmpl,
                    "valid": validation["valid"],
                    "issue_count": len(validation["issues"]),
                }
            )

        # Build category summary
        category_summary = _renderer.category_summary()

        return {
            "total": len(enriched),
            "category_filter": category,
            "locale": locale,
            "templates": enriched,
            "categories": {
                cat: info["count"]
                for cat, info in sorted(category_summary.items())
            },
        }, 200

    except Exception as exc:
        return {"detail": f"Template list error: {exc}"}, 500


def handle_notification_preview(body: dict) -> tuple[dict, int]:
    """POST /notifications/preview

    Renders a template with its built-in sample data for preview purposes.
    No real user data is required.

    Expected body fields:
      - template_id : str    — required
      - locale      : str    — "en" | "es" (default "en")
    """
    try:
        template_id = (body.get("template_id") or "").strip()
        locale = (body.get("locale") or "en").strip().lower()

        if not template_id:
            return {"detail": "Missing required field: template_id"}, 400
        if locale not in ("en", "es"):
            return {"detail": "Invalid locale. Use 'en' or 'es'."}, 400

        preview = _renderer.preview(template_id, locale)
        return preview, 200

    except ValueError as exc:
        return {"detail": str(exc)}, 404
    except Exception as exc:
        return {"detail": f"Preview error: {exc}"}, 500


def handle_notification_render(body: dict) -> tuple[dict, int]:
    """POST /notifications/render

    Renders a template with caller-supplied variable data.

    Expected body fields:
      - template_id : str    — required
      - locale      : str    — "en" | "es" (default "en")
      - data        : dict   — variable substitution values
      - format      : str    — "full" | "plain" | "html" | "subject"
                               (default "full" returns all variants)
    """
    try:
        template_id = (body.get("template_id") or "").strip()
        locale = (body.get("locale") or "en").strip().lower()
        data = body.get("data") or {}
        fmt = (body.get("format") or "full").strip().lower()

        if not template_id:
            return {"detail": "Missing required field: template_id"}, 400
        if locale not in ("en", "es"):
            return {"detail": "Invalid locale. Use 'en' or 'es'."}, 400
        if not isinstance(data, dict):
            return {"detail": "Field 'data' must be an object."}, 400
        if fmt not in ("full", "plain", "html", "subject"):
            return {
                "detail": "Invalid format. Use 'full', 'plain', 'html', or 'subject'."
            }, 400

        rendered = _renderer.render(template_id, locale, data)

        # Return only the requested format variant
        if fmt == "plain":
            return {
                "template_id": template_id,
                "locale": locale,
                "format": "plain",
                "subject": rendered["subject"],
                "plain": rendered["plain"],
            }, 200
        elif fmt == "html":
            return {
                "template_id": template_id,
                "locale": locale,
                "format": "html",
                "subject": rendered["subject"],
                "html": rendered["html"],
            }, 200
        elif fmt == "subject":
            return {
                "template_id": template_id,
                "locale": locale,
                "format": "subject",
                "subject": rendered["subject"],
            }, 200
        else:
            # "full" — return everything
            return rendered, 200

    except ValueError as exc:
        return {"detail": str(exc)}, 404
    except Exception as exc:
        return {"detail": f"Render error: {exc}"}, 500
