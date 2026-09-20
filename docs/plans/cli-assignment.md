# NEXUS — Assignment Deliverable Implementation Plan

Since you need to submit a smaller portion of the overall NEXUS vision as an assignment, we will focus exclusively on delivering a highly functional, end-to-end slice of the ecosystem: **The Windows Node MVP + The CLI Minor Project**. 

This will perfectly demonstrate the core concept: a central data node controlled remotely via a fast terminal interface.

## User Review Required

> [!IMPORTANT]  
> Please review this focused feature list for your assignment. If this looks like enough to get a great grade, approve it and I will begin building the CLI! 

## Proposed Assignment Feature List

### 1. The Core Node (Already Completed! ✅)
We have already built the backend required for this assignment:
- **Local Database:** SQLite schema storing Projects, Tasks, Notes, and Users.
- **REST API:** FastAPI server with endpoints for creation and retrieval.
- **Health Check:** Live `/health` endpoint.

### 2. The CLI Application (To Be Built 🚧)
We will build the CLI client in `apps/cli/` using **Python** (specifically the `Typer` library for beautiful terminal commands and `requests` for talking to the API).

**Core CLI Features for the Assignment:**
- `nexus init`: Connect the CLI to your local server (e.g., `http://127.0.0.1:8000`) and save the configuration.
- `nexus status`: Ping the server `/health` endpoint to ensure it's online.
- `nexus project list`: Fetch and display all projects in a clean terminal table.
- `nexus project create "Title"`: Send a POST request to create a new project.
- `nexus task list`: Fetch and display tasks.
- `nexus task add "Finish report" --project 1`: Create a new task assigned to a project.
- `nexus note add "Title" "Content"`: Quickly capture a note.

## Development Plan

1. **Git Context**: We will switch to the `feature/cli-power-tools` branch to do this work.
2. **Environment Setup**: Set up a virtual environment in `apps/cli/` and install `typer`, `rich` (for colored terminal output), and `requests`.
3. **Configuration Module**: Build a small module to read/write the server URL to a local config file (e.g., `~/.nexus-cli.json`) so the CLI knows where the API lives.
4. **Command Routing**: Implement the `project`, `task`, and `note` subcommands.
5. **Global Packaging**: Add `pyproject.toml` to package the CLI so it can be installed globally via `pip install -e .`, enabling the `nexus` command anywhere on the system.
6. **Cross-Device Networking**: Document the workflow to run the backend on Windows (`--host 0.0.0.0`) and connect from Mac via `nexus init --url http://<WINDOWS_IP>:8000`.
7. **Testing**: We will test the CLI commands against your live backend server to prove the ecosystem works.

## Verification Plan

### Manual Verification
- We will run `nexus project create "Assignment Project"` from the terminal.
- We will then check the Swagger UI in the browser to prove the terminal successfully injected data into the central node. 
- We will run a `git commit` to save the assignment deliverable.
