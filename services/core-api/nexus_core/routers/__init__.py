"""Router registry."""
from . import activity, auth, devices, files, inbox, nodes, notes, projects, sync, tasks

all_routers = [
    auth.router,
    devices.router,
    projects.router,
    tasks.router,
    notes.router,
    files.router,
    activity.router,
    inbox.router,
    nodes.router,
    sync.router,
]
