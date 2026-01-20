"""
Simple Flask API auto-generated from OpenAPI spec using Connexion.

Install: pip install connexion[flask,uvicorn]
Run with: python server.py

Example requests:
  curl http://localhost:3000/public/greetings
  curl -H "Authorization: Bearer demo-token-12345" http://localhost:3000/private/greetings
"""

import connexion

PORT = 3000
VALID_AUTHENTICATION_TOKEN = "demo-token-12345"


def validate_token(token: str) -> dict | None:
    """Validate the Bearer token and return token info."""
    if token == VALID_AUTHENTICATION_TOKEN:
        return {"sub": "demo-user", "scope": ["read"]}
    return None


def get_greetings(token_info: dict) -> dict:
    """Handler for authenticated GetGreetings operation."""
    return {"message": f"Hello, {token_info.get('sub', 'World')}!"}


def get_public_greetings() -> dict:
    """Handler for public GetGreetings operation."""
    return {"message": "Hello, World!"}


# Create the Connexion app with the OpenAPI spec
app = connexion.App(__name__, specification_dir=".")
app.add_api("openapi.json")


if __name__ == "__main__":
    print(f"Starting Simple API server on http://localhost:{PORT}")
    print(f"Authentication token: {VALID_AUTHENTICATION_TOKEN}")
    app.run(host="0.0.0.0", port=PORT)
