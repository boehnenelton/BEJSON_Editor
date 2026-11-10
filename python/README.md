# Modern BEJSON Editor (Flask Edition)

> Python Flask server edition of the Modern BEJSON Editor (104/104a). Serves a high-performance web spreadsheet interface backed by automatic server-side storage in the `databases/` folder.

[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)]()
[![Version](https://img.shields.io/badge/Version-1.2.9-blue.svg)]()
[![Package](https://img.shields.io/badge/Package-PKG%20169-orange.svg)]()
[![License](https://img.shields.io/badge/License-PolyForm%20Noncommercial%201.0.0-red.svg)](https://polyformproject.org/licenses/noncommercial/1.0.0/)

---

## Technical Metadata & Credits

- **Application Name:** BEJSON Editor (Flask Edition)
- **Primary Executable:** `app.py`
- **Frontend Template:** `templates/index.html`
- **Target Runtime:** Python 3.10+ with Flask 3.x on Linux / Android Termux
- **Current Version:** V129 / PKG169
- **Format Heritage:** BEJSON 104 and 104a (Foundational & Metadata Eras)
- **Database Storage:** Server-backed `databases/` repository (JSON/BEJSON)
- **Cryptographic Standard:** Web Crypto API (AES-256-GCM, PBKDF2-SHA256 100k iterations)
- **Author & Format Creator:** Elton Boehnen
- **Email Contact:** [boehnenelton2024@gmail.com](mailto:boehnenelton2024@gmail.com)
- **Web Portal:** [boehnenelton2024.pages.dev](https://boehnenelton2024.pages.dev)
- **License:** PolyForm Noncommercial License 1.0.0

---

## Architecture Overview

The Flask edition provides zero-configuration local server persistence for BEJSON datasets:

1. **Server Layer (`app.py`)**:
   - Python 3.10+ microservice built on Flask.
   - Strictly enforces path traversal blocks (no `..` or slashes allowed in filenames).
   - Validates BEJSON 104/104a structural envelope integrity on create, update, and load.
   - Executes atomic writes using temporary files and atomic `os.replace` to prevent data corruption.
2. **Client Interface (`templates/index.html`)**:
   - Fully synchronized with the V129/PKG169 JS editor core.
   - Features built-in `Server Databases` browser modal to inspect, open, save, and delete databases in `databases/`.
   - Keyboard shortcut `Ctrl+S` / `Cmd+S` commits directly back to the active server file.
   - Retains full support for client-side Web Crypto AES-GCM encryption, schema editing, and validation reporting.
3. **Storage Tier (`databases/`)**:
   - Standard directory containing `.bejson` files.
   - Automatically seeded with `sample_database.bejson`.

---

## REST API Directory

| Endpoint | Method | Request Payload | Description |
| :--- | :--- | :--- | :--- |
| `/` | `GET` | None | Serves the web editor front end (`templates/index.html`). |
| `/api/health` | `GET` | None | Returns JSON health status, version counters, and database count. |
| `/api/databases` | `GET` | None | Returns array of all available `.bejson` files in `databases/`. |
| `/api/databases` | `POST` | `{"filename": "...", "content": {...}, "overwrite": bool}` | Creates a new database in `databases/` with BEJSON validation. |
| `/api/databases/<filename>` | `GET` | None | Retrieves and validates the JSON content of a database file. |
| `/api/databases/<filename>` | `PUT` | `{"content": {...}}` | Saves and updates an existing database file via atomic replace. |
| `/api/databases/<filename>` | `DELETE` | None | Safely deletes a database file from `databases/`. |

---

## Quick Start & Execution

### 1. Launch the Server
```bash
python3 app.py
```
By default, the server binds to `http://0.0.0.0:5000`.

### 2. Access in Browser
Open your browser and navigate to:
```
http://localhost:5000/
```

### 3. Usage Workflows
- **Open Existing Server Database**: Click **🗄 Server DBs** in the header or **📂 Browse Server Databases** in the Hub to view and load databases.
- **Create New Database**: In the Hub, configure Mode, Record Type, and Initial Fields, then click **Create & Open**.
- **Save to Server**: Press `Ctrl+S` or click `💾 Save File` to write changes back to `databases/<filename>.bejson`.

---

## License

This software is released under the **PolyForm Noncommercial License 1.0.0** (`PolyForm-Noncommercial-1.0.0`). Commercial use, closed redistribution, or monetized deployment is strictly prohibited without explicit authorization from Elton Boehnen.
