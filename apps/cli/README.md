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

### `nexus ui`
Launch the full-screen interactive Terminal User Interface (TUI). This interface provides a persistent, interactive way to view and add Projects, Tasks, and Notes using a synthwave aesthetic.

**TUI Keyboard Shortcuts & Interactions:**
- `p`: Switch view to Projects
- `t`: Switch view to Tasks
- `n`: Switch view to Notes
- `f`: Switch view to Files (Local filesystem)
- `s`: Open global file search modal
- `P`: Open modal to add a new Project
- `T`: Open modal to add a new Task
- `N`: Open modal to add a new Note
- `Ctrl+S`: Open the Command Palette
- `Enter` or `Click`: Select a Project or Task row to change its status (Pending, In Progress, Completed)
- `q`: Quit the application

---

## File Operations

### `nexus file list`
List all files in a specific directory (defaults to the home directory).
- **Arguments:**
  - `PATH` (string, optional): The directory path to list.
- **Example:** `nexus file list /Users/jaishastri/Documents`

### `nexus search`
Globally search for text within files on the connected device.
- **Arguments:**
  - `QUERY` (string): The text to search for.
- **Options:**
  - `--path` (string, optional): The directory to search within (defaults to home).
- **Example:** `nexus search "API_KEY" --path /Users/jaishastri/Projects`

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
