#!/usr/bin/env python
"""
Script to generate OpenAPI specification from API documentation.
This creates a standardized OpenAPI 3.0 specification that can be used with Swagger UI.
"""

import json
import os
import re
from datetime import datetime

import yaml

# Base specification
OPENAPI_SPEC = {
    "openapi": "3.0.1",
    "info": {
        "title": "ChessMate API",
        "description": "API for the ChessMate chess analysis platform",
        "version": "1.0.0",
        "contact": {"email": "support@chessmate.com"},
        "license": {
            "name": "Proprietary",
        },
    },
    "servers": [
        {"url": "https://api.chessmate.com/v1", "description": "Production server"},
        {"url": "https://staging-api.chessmate.com/v1", "description": "Staging server"},
        {"url": "http://localhost:8000/api", "description": "Local development server"},
    ],
    "tags": [
        {"name": "Authentication", "description": "Endpoints for user authentication and authorization"},
        {"name": "Games", "description": "Endpoints for game management and analysis"},
        {"name": "User", "description": "Endpoints for user profile and settings"},
    ],
    "paths": {},
    "components": {
        "schemas": {
            "SuccessResponse": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["success"],
                        "description": "Indicates a successful operation",
                    },
                    "data": {"type": "object", "description": "Contains the actual response data"},
                    "message": {"type": "string", "description": "Optional success message"},
                    "request_id": {
                        "type": "string",
                        "description": "Unique identifier for the request, useful for debugging",
                    },
                },
                "required": ["status"],
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["error"], "description": "Indicates an error occurred"},
                    "code": {"type": "string", "description": "Error code identifier"},
                    "message": {"type": "string", "description": "Human-readable error message"},
                    "details": {"type": "object", "description": "Additional error details"},
                    "request_id": {
                        "type": "string",
                        "description": "Unique identifier for the request, useful for debugging",
                    },
                },
                "required": ["status", "code", "message"],
            },
        },
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT authorization token, prefixed with 'Bearer: '",
            }
        },
        "parameters": {},
        "requestBodies": {},
        "responses": {
            "Unauthorized": {
                "description": "Authentication failed or token is invalid",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
            },
            "BadRequest": {
                "description": "The request contains invalid parameters",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
            },
            "NotFound": {
                "description": "The requested resource was not found",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
            },
            "ServerError": {
                "description": "An unexpected server error occurred",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
            },
        },
    },
    "security": [{"bearerAuth": []}],
}

# Path to API reference markdown file
API_DOCS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "api_reference.md")

# Path to output OpenAPI spec
OPENAPI_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "openapi.json")
OPENAPI_YAML_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "openapi.yaml")


def ensure_directory_exists(file_path):
    """Ensure the directory for the given file path exists."""
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


def extract_endpoints_from_markdown(md_path):
    """Extract endpoint information from markdown documentation."""
    with open(md_path, "r") as f:
        content = f.read()

    # Regular expressions to extract endpoint information
    endpoint_pattern = r"### (.*?)\n\n(.*?)\n\n\*\*URL\*\*: `(.*?)`\n\n\*\*Method\*\*: `(.*?)`\n\n\*\*Authentication\*\*: (.*?)(?:\n\n|$)"
    endpoint_matches = re.finditer(endpoint_pattern, content, re.DOTALL)

    endpoints = []
    for match in endpoint_matches:
        name = match.group(1).strip()
        description = match.group(2).strip()
        url = match.group(3).strip()
        method = match.group(4).strip().lower()
        auth_required = match.group(5).strip() == "Required"

        # Extract parameters if present
        params_pattern = r"\*\*(?:Path |Query |Request Body)Parameters\*\*:\n\n\| (.*?)\n\|(.*?)\n\n"
        params_match = re.search(params_pattern, content[match.end() :], re.DOTALL)

        params = []
        if params_match:
            param_rows = params_match.group(2).strip().split("\n")
            param_headers = params_match.group(1).strip().split("|")
            param_headers = [h.strip() for h in param_headers]

            for row in param_rows:
                cells = row.split("|")
                cells = [cell.strip() for cell in cells if cell.strip()]

                if len(cells) >= len(param_headers):
                    param = {}
                    for i, header in enumerate(param_headers):
                        param[header.lower()] = cells[i]
                    params.append(param)

        # Extract response example if present
        response_pattern = r"\*\*Success Response.*?\*\*:\n\n```json\n(.*?)\n```"
        response_match = re.search(response_pattern, content[match.end() :], re.DOTALL)
        response_example = None
        if response_match:
            response_example = response_match.group(1).strip()

        endpoints.append(
            {
                "name": name,
                "description": description,
                "url": url,
                "method": method,
                "auth_required": auth_required,
                "params": params,
                "response_example": response_example,
            }
        )

    return endpoints


def generate_path_item(endpoint):
    """Generate an OpenAPI path item from endpoint metadata."""
    method = endpoint["method"]

    # Determine tag based on endpoint URL
    tag = (
        "Authentication"
        if "/api/auth" in endpoint["url"]
        or any(
            auth_path in endpoint["url"]
            for auth_path in ["/login", "/register", "/logout", "/csrf", "/verify-email", "/password-reset", "/token"]
        )
        else "Games"
    )

    # Create path item
    path_item = {
        "tags": [tag],
        "summary": endpoint["name"],
        "description": endpoint["description"],
        "operationId": endpoint["name"].lower().replace(" ", "_").replace("-", "_"),
        "responses": {
            "200": {
                "description": "Successful operation",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SuccessResponse"}}},
            },
            "400": {"$ref": "#/components/responses/BadRequest"},
            "401": {"$ref": "#/components/responses/Unauthorized"},
            "404": {"$ref": "#/components/responses/NotFound"},
            "500": {"$ref": "#/components/responses/ServerError"},
        },
    }

    # Add security requirement if authentication is required
    if endpoint["auth_required"]:
        path_item["security"] = [{"bearerAuth": []}]
    else:
        path_item["security"] = []

    # Add parameters
    path_item["parameters"] = []

    # Process parameters
    for param in endpoint["params"]:
        param_name = param.get("parameter", param.get("field", ""))
        if not param_name:
            continue

        required = param.get("required", "").lower() == "yes"
        param_type = param.get("type", "string").lower()

        # Map markdown parameter types to OpenAPI types
        type_mapping = {
            "string": "string",
            "number": "number",
            "integer": "integer",
            "boolean": "boolean",
            "array": "array",
            "object": "object",
        }

        openapi_type = type_mapping.get(param_type, "string")

        # Check if it's a path parameter
        if "{" + param_name + "}" in endpoint["url"]:
            path_item["parameters"].append(
                {
                    "name": param_name,
                    "in": "path",
                    "description": param.get("description", ""),
                    "required": True,
                    "schema": {"type": openapi_type},
                }
            )
        # Check if it's likely a query parameter (GET method usually)
        elif method == "get":
            path_item["parameters"].append(
                {
                    "name": param_name,
                    "in": "query",
                    "description": param.get("description", ""),
                    "required": required,
                    "schema": {"type": openapi_type},
                }
            )

    # Add request body for non-GET methods if we have body parameters
    if method != "get" and endpoint["params"]:
        properties = {}
        required_props = []

        for param in endpoint["params"]:
            param_name = param.get("field", "")
            if not param_name:
                continue

            required = param.get("required", "").lower() == "yes"
            param_type = param.get("type", "string").lower()

            # Map markdown parameter types to OpenAPI types
            type_mapping = {
                "string": {"type": "string"},
                "number": {"type": "number"},
                "integer": {"type": "integer"},
                "boolean": {"type": "boolean"},
                "array": {"type": "array", "items": {"type": "string"}},
                "array[string]": {"type": "array", "items": {"type": "string"}},
                "object": {"type": "object"},
            }

            schema = type_mapping.get(param_type, {"type": "string"})
            properties[param_name] = {**schema, "description": param.get("description", "")}

            if required:
                required_props.append(param_name)

        path_item["requestBody"] = {
            "content": {"application/json": {"schema": {"type": "object", "properties": properties}}}
        }

        if required_props:
            path_item["requestBody"]["content"]["application/json"]["schema"]["required"] = required_props

        path_item["requestBody"]["required"] = bool(required_props)

    return {method: path_item}


def normalize_path(path):
    """Normalize OpenAPI path to handle path parameters."""
    return re.sub(r"{([^/]+)}", r"{\1}", path)


def main():
    # Extract endpoints from markdown
    endpoints = extract_endpoints_from_markdown(API_DOCS_PATH)

    # Generate OpenAPI paths
    paths = {}
    for endpoint in endpoints:
        url = endpoint["url"]
        # Convert URL to OpenAPI path format
        openapi_path = normalize_path(url)

        # Generate path item
        path_item = generate_path_item(endpoint)

        # Add to paths
        if openapi_path not in paths:
            paths[openapi_path] = {}

        paths[openapi_path].update(path_item)

    # Update OpenAPI spec with paths
    OPENAPI_SPEC["paths"] = paths

    # Add generation timestamp
    OPENAPI_SPEC["info"]["x-generated-at"] = datetime.now().isoformat()

    # Ensure output directories exist
    ensure_directory_exists(OPENAPI_JSON_PATH)
    ensure_directory_exists(OPENAPI_YAML_PATH)

    # Write OpenAPI spec to JSON file
    with open(OPENAPI_JSON_PATH, "w") as f:
        json.dump(OPENAPI_SPEC, f, indent=2)

    # Write OpenAPI spec to YAML file
    with open(OPENAPI_YAML_PATH, "w") as f:
        yaml.dump(OPENAPI_SPEC, f, sort_keys=False)

    print(f"OpenAPI specification generated at {OPENAPI_JSON_PATH} and {OPENAPI_YAML_PATH}")


if __name__ == "__main__":
    main()
