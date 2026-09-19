# NEXUS CLI (Command Line Interface)

The NEXUS CLI is a powerful terminal-based tool for interacting with your Central API Node. It allows you to rapidly capture notes, manage tasks, and organize projects directly from your command line.

## Installation

To install the CLI globally on your system (so you can run the `nexus` command from anywhere):

```bash
cd apps/cli
source venv/bin/activate
pip install -e .
```

## Global Commands

### `nexus init`
Initialize the CLI and connect it to your NEXUS Core API server.
- **Arguments:** None
- **Options:** 
  - `--url` (string): The base URL of your API server (e.g., `http://127.0.0.1:8000`).
- **Example:** `nexus init --url http://192.168.1.15:8000`

### `nexus status`
Check the health and connectivity of your configured API server.
- **Arguments:** None
- **Example:** `nexus status`

---

## Projects Management

### `nexus project list`
Fetch and display all your projects in a clean table format.
- **Arguments:** None
- **Example:** `nexus project list`

### `nexus project create`
Create a new project.
- **Arguments:**
  - `TITLE` (string): The title of the new project. (Enclose in quotes if it contains spaces).
- **Options:**
  - `--description` (string, optional): A description for the project.
- **Example:** `nexus project create "My Super Project" --description "Top secret work"`

---

## Tasks Management

### `nexus task list`
Fetch and display all active tasks.
- **Arguments:** None
- **Example:** `nexus task list`

### `nexus task add`
Add a new task and assign it to a specific project.
- **Arguments:**
  - `TITLE` (string): The title of the task. (Enclose in quotes if it contains spaces).
  - `PROJECT_ID` (integer): The numeric ID of the project this task belongs to.
- **Example:** `nexus task add "Finish the assignment" 1`

---

## Notes Capture

### `nexus note add`
Quickly capture a thought or text note to the central brain.
- **Arguments:**
  - `TITLE` (string): The title of the note.
  - `CONTENT` (string): The body content of the note.
- **Example:** `nexus note add "Shopping List" "Milk, Eggs, Bread"`
