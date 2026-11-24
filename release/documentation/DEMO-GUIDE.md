# NEXUS — Unified Cross-Client Demonstration Guide

This guide outlines the exact verification sequence demonstrating that NEXUS operates as **one unified, local-first personal command center** across macOS Desktop, Android Mobile, and Terminal CLI.

---

## Architecture Overview
```text
                  NEXUS MAC HOST
             Authoritative Local SQLite
               (~/.nexus/nexus.db)
                        │
                ┌───────┴───────┐
                │ NEXUS Core API │ (127.0.0.1:8000)
                └───────┬───────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   macOS Desktop    NEXUS Mobile     CLI Client
     (Tauri 2)        (Android)      (Rich TUI)
```

---

## Scenario A: Mac Desktop Host Bootstrap & SQLite Authoritative State

1. **Start the Sovereign Core API**:
   ```bash
   nexus host start
   ```
   *Verification*: Run `curl -s http://127.0.0.1:8000/health`. Response confirms `"status": "ok"`. The authoritative SQLite database is active at `~/.nexus/nexus.db`.

2. **Launch macOS Desktop Application**:
   Open `NEXUS Desktop.app` (from `release/macos/NEXUS.dmg`).
   - The top banner displays: `Local Mac Host (Primary Core)` with green status dot and low latency (~2ms).
   - Authoritative storage badge confirms `SQLite · ~/.nexus/nexus.db`.

---

## Scenario B: Project & Task Lifecycle on Desktop

1. On NEXUS Desktop, navigate to **Projects**.
2. Click **+ New Project**:
   - Title: `Project Sovereign Alpha`
   - Description: `First end-to-end multi-device verification milestone.`
3. Click **Create Project**.
   - Project appears with `Status: ACTIVE` and `Rev: 1`.
4. Navigate to **Tasks**:
   - Click **+ Add Task** with Title: `Review local-first sync protocol`.
   - Assign to `Project Sovereign Alpha`.
5. Return to **Dashboard**:
   - Metrics cards instantly reflect 1 active project and 1 open task.
   - Audit stream displays `project.created` and `task.created`.

---

## Scenario C: Instant Visibility on Companion Mobile Client

1. Open `NEXUS Mobile` (installed from `release/mobile/NEXUS-android.apk`).
2. Tap **Continue with Google** to authenticate with the same identity.
3. Mobile auto-discovers the Mac host:
   - Cockpit header indicates `Connected to Mac Host`.
4. Open the **Workspace** tab on mobile:
   - `Project Sovereign Alpha` is already listed.
   - `Review local-first sync protocol` task is visible.
5. On mobile, tap the task checkbox to mark it **Completed**.

---

## Scenario D: Cross-Client Reflection on Terminal CLI

1. Open your terminal and inspect tasks:
   ```bash
   nexus tasks list
   ```
   *Output*:
   ```text
   ID   Title                                 Status      Rev   Project
   1    Review local-first sync protocol      completed   2     #1
   ```
   *Notice*: The task status updated from `pending` to `completed`, and revision bumped from `1` to `2`.

2. Add a new note from CLI:
   ```bash
   nexus notes create "Field Memo" --content "Synced from terminal across LAN socket."
   ```

3. Switch back to **macOS Desktop** -> **Notes Wall**:
   - `Field Memo` immediately appears on the desktop interface without page refresh.

---

## Scenario E: Jailed Shared Files Upload & Download

1. In NEXUS Desktop, navigate to **Files**.
2. The breadcrumb indicates the jailed storage root (e.g. `~/Documents`).
3. Click **↑ Upload File** and select a document (e.g. `spec.pdf`).
4. File appears in the table with size and path.
5. Search files by keyword:
   - Enter query in the search bar.
   - Instant full-text search matches within the storage root.
6. Click **↓ Download** to verify clean file retrieval from the jailed storage root.

---

## Scenario F: Host Offline & Data Sovereignty Verification

1. Stop the host process:
   ```bash
   nexus host stop
   ```
2. Verify local database file on Mac:
   ```bash
   sqlite3 ~/.nexus/nexus.db "SELECT title, status, revision FROM projects;"
   ```
   *Output*:
   ```text
   Project Sovereign Alpha|active|1
   ```
3. Restart the host:
   ```bash
   nexus host start
   ```
   *Verification*: Desktop, Mobile, and CLI immediately reconnect. All records, revisions, and files persist without data loss or remote cloud dependency.
