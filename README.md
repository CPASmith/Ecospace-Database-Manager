## Ecospace — ecological database explorer##
A Streamlit + PostgreSQL interface for recording and exploring ecological traits. Built for research on Triassic bivalve occurrences.


## Quick start (Docker) ##
Requirements: Docker Desktop (with Docker Compose), downloadable at https://www.docker.com/products/docker-desktop/. Docker Desktop is a containerisation tool that allows the application and its PostgreSQL database to run locally without requiring separate installation or configuration.

-->1. Download this repository (GitHub Code → Download ZIP) and extract it.

-->2. Open a terminal and navigate to the extracted folder (the one containing compose.yaml). For example:

Windows (PowerShell):
	cd "C:\path\to\Ecospace-Database-Manage"
macOS (Terminal):
	cd "/path/to/Ecospace-Database-Manage"
Replace the example path with the actual location of the extracted folder.

-->3. If Docker Desktop is not already installed, download and install it using the link above. Restart your computer if prompted.

-->4. Launch Docker Desktop and wait until it is running. On Windows, if Docker reports that your Windows Subsystem for Linux (WSL) is outdated, open PowerShell as administrator and run:
	wsl --update
Restart Docker Desktop afterwards.

-->5. In the terminal, run:
	docker compose up --build

-->6. Wait for the database import and application startup, then open http://localhost:8501 in your web browser.


The database is created automatically with four linked tables and a September 2026 snapsho of the bivalve dataset (18,245 occurrences, 72 contexts, 52 contextual dimension/answer definitions, 106,505 contextual values). Data are stored locally in a Docker volume; edits and deletions are persistent within that volume.

To stop the application, press `Ctrl+C` (or run `docker compose down`). 

To reset the demonstration database to its initial state, run:
	docker compose down -v
	docker compose up --build
**Warning:** `docker compose down -v` permanently deletes all changes made to the local demonstration database.


## Features ##
- Browse and filter occurrences and ecological traits.
- Add, edit and delete occurrences, including conditional ecological values.
- Explore an individual ecological profile and the overall conditional ecological hierarchy.
- PostgreSQL relational schema with constraints and foreign keys.


## Repository layout ##
- `app.py`, `ui/`, `utils.py`: Streamlit application.
- `db.py`: PostgreSQL connection (Docker environment variables, or local Streamlit secrets).
- `db_init/01_schema.sql`: database schema.
- `db_init/02_data.sql`, `data/*.csv`: database snapshot import.
- `compose.yaml`, `Dockerfile`: local reproducible deployment.

## Security ##
The database is not exposed on a host port; the application listens only on localhost (`127.0.0.1:8501`). Docker uses a local-only demonstration password. Never commit `.streamlit/secrets.toml`, real database credentials, or confidential data.



