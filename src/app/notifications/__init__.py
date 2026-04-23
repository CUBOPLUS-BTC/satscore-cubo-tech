"""Bitcoin notification template system.

Provides bilingual (English / Spanish) notification templates for all
significant events in the Magma Bitcoin app, plus a renderer that can
produce plain-text and HTML versions of each template with runtime data
interpolation.

Public surface
--------------
Templates
  - TEMPLATES              : dict[str, TemplateDict]

Renderer
  - NotificationRenderer   : class for rendering and previewing templates
    - render()
    - render_html()
    - render_plain()
    - preview()
    - get_sample_data()
    - validate_template()
    - list_templates()
    - get_template_info()

Routes (HTTP handlers, return (body_dict, status_code))
  - handle_notification_templates()
  - handle_notification_preview()
  - handle_notification_render()
"""

from .templates import TEMPLATES
from .renderer import NotificationRenderer
from .routes import (
    handle_notification_templates,
    handle_notification_preview,
    handle_notification_render,
)

__all__ = [
    "TEMPLATES",
    "NotificationRenderer",
    "handle_notification_templates",
    "handle_notification_preview",
    "handle_notification_render",
]
