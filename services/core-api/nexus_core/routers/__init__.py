"""Router registry."""
from . import activity, auth, devices, files, inbox, notes, projects, sync, tasks

all_routers = [
    auth.router,
    devices.router,
    projects.router,
    tasks.router,
    notes.router,
    files.router,
    activity.router,
    inbox.router,
    sync.router,
]
