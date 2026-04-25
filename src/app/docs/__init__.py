"""API documentation generator for the Magma API.

Produces an OpenAPI 3.0 specification from the schema definitions in
``schemas.py`` and serves Swagger UI HTML via a simple route handler.

Quick start
-----------
::

    from app.docs import OpenAPIGenerator

    gen  = OpenAPIGenerator()
    spec = gen.generate()          # dict
    json = gen.to_json()           # JSON string
    yaml = gen.to_yaml_like()      # YAML-like string

Route handler (inline Swagger UI)
----------------------------------
::

    from app.docs.routes import handle_openapi_json, handle_swagger_ui

    # In your HTTP router:
    # GET /openapi.json  ->  handle_openapi_json()
    # GET /docs          ->  handle_swagger_ui()
"""

from .generator import OpenAPIGenerator
from .schemas import ENDPOINT_SCHEMAS, COMPONENT_SCHEMAS

__all__ = ["OpenAPIGenerator", "ENDPOINT_SCHEMAS", "COMPONENT_SCHEMAS"]


# ---------------------------------------------------------------------------
# Convenience route handlers so the HTTP server can import them directly.
# ---------------------------------------------------------------------------

_generator = OpenAPIGenerator()


def handle_openapi_json() -> tuple[dict, int]:
    """GET /openapi.json — return the OpenAPI spec as JSON."""
    spec = _generator.generate()
    return spec, 200


def handle_swagger_ui() -> tuple[str, int]:
    """GET /docs — return Swagger UI HTML page."""
    spec_url = "/openapi.json"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_generator.title} — API Docs</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
  <style>
    body {{ margin: 0; background: #0a0a0a; }}
    .topbar {{ display: none; }}
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    SwaggerUIBundle({{
      url: "{spec_url}",
      dom_id: "#swagger-ui",
      presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
      layout: "StandaloneLayout",
      deepLinking: true,
      displayRequestDuration: true,
    }});
  </script>
</body>
</html>"""
    return html, 200
