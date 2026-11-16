"""Router registry."""
from . import activity, auth, devices, files, github, inbox, nodes, notes, projects, relay, services, sync, tasks

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
    relay.router,
    services.router,
    github.router,
]
