#!/usr/bin/env python3
# ==============================================================================
# Script Name:    app.py
# Description:    Flask application server for the Modern BEJSON Editor (104/104a).
#                 Provides zero-external-dependency local database persistence
#                 serving the single-page editor interface and managing the
#                 server-side databases/ repository.
# Version:        1.2.9
# Date Created:   2026-11-10
# Author Credit:  Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
# Relational ID:  4c8e1a2f-7b3d-4f9e-9a1c-5d2e8b91c0a6
# License:        PolyForm Noncommercial License 1.0.0 (PolyForm-Noncommercial-1.0.0)
# ==============================================================================

import os
import re
import json
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Union

from flask import Flask, request, jsonify, render_template, send_from_directory

# ------------------------------------------------------------------------------
# Logging & Dynamic Paths Configuration
# ------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("BEJSON_Editor_Flask")

SCRIPT_PATH = Path(__file__).resolve().parent
USER_DIR = SCRIPT_PATH / "user"
DATABASES_DIR = USER_DIR / "databases"
TAXONOMY_DIR = USER_DIR / "taxonomy"
TEMPLATES_DIR = SCRIPT_PATH / "templates"
STATIC_DIR = SCRIPT_PATH / "static"

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR)
)

# ------------------------------------------------------------------------------
# Validation & Sanitization Helpers
# ------------------------------------------------------------------------------
# Filenames: letters, digits, spaces, dots, underscores, hyphens only.
# Strictly prohibits directory separators (/ and \), null bytes, and traversal ('..').
_SAFE_FILENAME_REGEX = re.compile(r"^[A-Za-z0-9._\- ]+$")

MANDATORY_BEJSON_KEYS = (
    "Format",
    "Format_Version",
    "Format_Creator",
    "Records_Type",
    "Fields",
    "Values"
)


def get_safe_filename(name: Optional[str]) -> Optional[str]:
    """
    Sanitizes and enforces standard '.bejson' naming rules.
    Returns None if input contains path separators or traversal characters.
    """
    if not name or not isinstance(name, str):
        return None
    cleaned = name.strip()
    if not cleaned or not _SAFE_FILENAME_REGEX.match(cleaned) or ".." in cleaned:
        return None
    if not cleaned.lower().endswith(".bejson"):
        cleaned = f"{cleaned}.bejson"
    return cleaned


def resolve_database_path(name: Optional[str]) -> Optional[Path]:
    """
    Resolves a sanitized filename ensuring destination stays strictly inside DATABASES_DIR.
    """
    safe_name = get_safe_filename(name)
    if safe_name is None:
        return None
    base_dir = DATABASES_DIR.resolve()
    target_path = (DATABASES_DIR / safe_name).resolve()
    if target_path.parent != base_dir:
        logger.warning("Path traversal attempt blocked: %s", name)
        return None
    return target_path


def validate_bejson_envelope(doc: Union[str, Dict[str, Any]]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Verifies that a payload conforms strictly to BEJSON 104/104a envelope requirements.
    """
    if isinstance(doc, str):
        try:
            parsed = json.loads(doc)
        except json.JSONDecodeError as err:
            return False, f"Malformed JSON: {err}", {}
    elif isinstance(doc, dict):
        parsed = doc
    else:
        return False, "Payload must be a JSON object.", {}

    if not isinstance(parsed, dict) or isinstance(parsed, list):
        return False, "BEJSON document root must be an object.", {}

    for key in MANDATORY_BEJSON_KEYS:
        if key not in parsed:
            return False, f"Missing mandatory BEJSON envelope key: '{key}'.", {}

    if parsed.get("Format") != "BEJSON":
        return False, f"Envelope 'Format' must be 'BEJSON' (got {parsed.get('Format')!r}).", {}

    ver = parsed.get("Format_Version")
    if ver not in ("104", "104a"):
        return False, f"Unsupported Format_Version: {ver!r} (expected '104' or '104a').", {}

    if parsed.get("Format_Creator") != "Elton Boehnen":
        return False, "Envelope 'Format_Creator' must be 'Elton Boehnen'.", {}

    records_type = parsed.get("Records_Type")
    if not isinstance(records_type, list) or len(records_type) != 1 or not isinstance(records_type[0], str):
        return False, "'Records_Type' must be an array with exactly one string identifier.", {}

    fields = parsed.get("Fields")
    if not isinstance(fields, list) or len(fields) == 0:
        return False, "'Fields' must be a non-empty array of field descriptor objects.", {}

    values = parsed.get("Values")
    if not isinstance(values, list):
        return False, "'Values' must be a 2D matrix array of record rows.", {}

    return True, "", parsed


def atomic_write_text(path: Path, content: str) -> None:
    """
    Performs an atomic write using temporary file staging and atomic rename.
    """
    DATABASES_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = path.with_suffix(f"{path.suffix}.tmp_{os.getpid()}")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_file, path)
    except Exception as err:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass
        raise err


# ------------------------------------------------------------------------------
# Flask HTTP Routes
# ------------------------------------------------------------------------------

@app.route("/")
def index():
    """Serves the primary Modern BEJSON Editor interface."""
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health_check():
    """Service health and environment telemetry."""
    DATABASES_DIR.mkdir(parents=True, exist_ok=True)
    file_count = len(list(DATABASES_DIR.glob("*.bejson")))
    return jsonify({
        "status": "healthy",
        "service": "BEJSON_Editor_Flask",
        "version": "1.2.9",
        "package": "PKG169",
        "database_count": file_count,
        "author": "Elton Boehnen",
        "license": "PolyForm-Noncommercial-1.0.0"
    }), 200


@app.route("/api/databases", methods=["GET"])
def list_databases():
    """
    Returns an array of all available .bejson documents located inside DATABASES_DIR.
    """
    DATABASES_DIR.mkdir(parents=True, exist_ok=True)
    database_entries = []

    for item in sorted(DATABASES_DIR.glob("*.bejson")):
        if item.is_file():
            stat_info = item.stat()
            database_entries.append({
                "filename": item.name,
                "size_bytes": stat_info.st_size,
                "modified_timestamp": stat_info.st_mtime,
                "modified_iso": None
            })

    return jsonify({"databases": database_entries, "count": len(database_entries)}), 200


@app.route("/api/databases", methods=["POST"])
def create_database():
    """
    Creates a new database or saves a new file in DATABASES_DIR.
    Payload: { "filename": "...", "content": {...}, "overwrite": false }
    """
    body = request.get_json(force=True, silent=True) or {}
    filename = body.get("filename")
    content = body.get("content")
    overwrite = bool(body.get("overwrite", False))

    if not filename:
        return jsonify({"error": "Parameter 'filename' is required."}), 400
    if content is None:
        return jsonify({"error": "Parameter 'content' is required."}), 400

    target_path = resolve_database_path(filename)
    if target_path is None:
        return jsonify({"error": f"Invalid filename format: '{filename}'."}), 400

    DATABASES_DIR.mkdir(parents=True, exist_ok=True)
    if target_path.exists() and not overwrite:
        return jsonify({
            "error": f"Database '{target_path.name}' already exists.",
            "exists": True
        }), 409

    is_valid, validation_error, parsed_doc = validate_bejson_envelope(content)
    if not is_valid:
        logger.warning("Rejected invalid BEJSON document on create: %s", validation_error)
        return jsonify({"error": validation_error}), 400

    formatted_text = json.dumps(parsed_doc, indent=2, ensure_ascii=False)
    atomic_write_text(target_path, formatted_text)
    logger.info("Created database file: %s (%d bytes)", target_path.name, target_path.stat().st_size)

    return jsonify({
        "success": True,
        "filename": target_path.name,
        "size_bytes": target_path.stat().st_size
    }), 201


@app.route("/api/databases/<path:filename>", methods=["GET"])
def get_database(filename: str):
    """
    Reads and returns the JSON document for a given database file.
    """
    target_path = resolve_database_path(filename)
    if target_path is None or not target_path.exists():
        return jsonify({"error": f"Database '{filename}' not found."}), 404

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
    except Exception as err:
        logger.error("Failed to read database %s: %s", target_path.name, err)
        return jsonify({"error": f"Read error: {err}"}), 500

    is_valid, validation_error, parsed_doc = validate_bejson_envelope(raw_text)
    if not is_valid:
        logger.warning("Database file on disk failed BEJSON envelope check: %s - %s", target_path.name, validation_error)
        return jsonify({"error": f"Database file corrupt or non-BEJSON: {validation_error}"}), 422

    return jsonify({
        "filename": target_path.name,
        "content": parsed_doc,
        "size_bytes": target_path.stat().st_size
    }), 200


@app.route("/api/databases/<path:filename>", methods=["PUT"])
def update_database(filename: str):
    """
    Updates the content of an existing database in DATABASES_DIR.
    Payload: { "content": {...} }
    """
    target_path = resolve_database_path(filename)
    if target_path is None:
        return jsonify({"error": f"Invalid filename format: '{filename}'."}), 400

    body = request.get_json(force=True, silent=True) or {}
    content = body.get("content")
    if content is None:
        return jsonify({"error": "Parameter 'content' is required."}), 400

    is_valid, validation_error, parsed_doc = validate_bejson_envelope(content)
    if not is_valid:
        logger.warning("Rejected invalid BEJSON document on update for %s: %s", filename, validation_error)
        return jsonify({"error": validation_error}), 400

    formatted_text = json.dumps(parsed_doc, indent=2, ensure_ascii=False)
    atomic_write_text(target_path, formatted_text)
    logger.info("Saved database file: %s (%d bytes)", target_path.name, target_path.stat().st_size)

    return jsonify({
        "success": True,
        "filename": target_path.name,
        "size_bytes": target_path.stat().st_size
    }), 200


@app.route("/api/databases/<path:filename>", methods=["DELETE"])
def delete_database(filename: str):
    """
    Deletes a database from DATABASES_DIR.
    """
    target_path = resolve_database_path(filename)
    if target_path is None or not target_path.exists():
        return jsonify({"error": f"Database '{filename}' not found."}), 404

    try:
        target_path.unlink()
        logger.info("Deleted database file: %s", target_path.name)
        return jsonify({"success": True, "deleted": target_path.name}), 200
    except Exception as err:
        logger.error("Failed to delete database %s: %s", target_path.name, err)
        return jsonify({"error": f"Delete error: {err}"}), 500


# ------------------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------------------
DEFAULT_PORT = 5016

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="BEJSON Editor Flask Server")
    parser.add_argument("--port", "-p", type=int, default=int(os.environ.get("PORT", DEFAULT_PORT)), help="Port to bind (default: 5016)")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    args = parser.parse_args()

    DATABASES_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Starting BEJSON Editor Flask Server on http://%s:%d", args.host, args.port)
    logger.info("Databases folder: %s", DATABASES_DIR)
    app.run(host=args.host, port=args.port, debug=False)
