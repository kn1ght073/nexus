"""TUI widgets package for NEXUS."""

from .account_view import AccountView
from .activity_view import ActivityView
from .context import ContextPanel
from .devices_view import DevicesView
from .diagnostics_view import DiagnosticsView
from .explorer import CommandExplorer
from .files_view import FilesView
from .form_modal import ParameterFormModal
from .header import StatusHeader
from .help_modal import HelpModal
from .network_view import NetworkView
from .nodes_view import NodesView
from .notes_tasks_view import (
    AddNoteToProjectModal,
    AddTaskToProjectModal,
    ConfirmDeleteProjectModal,
    NotesTasksView,
    ProjectDetailModal,
)
from .overview import OverviewDashboard
from .palette import CommandPaletteModal
from .result_modal import ExecutionResultModal
from .services_view import ServicesView
from .settings_modal import SettingsModal
from .settings_view import SettingsView
from .sidebar import NavigationSidebar
from .sync_view import SyncView
from .wizard import SetupWizardModal

__all__ = [
    "AccountView",
    "ActivityView",
    "AddNoteToProjectModal",
    "AddTaskToProjectModal",
    "CommandExplorer",
    "CommandPaletteModal",
    "ConfirmDeleteProjectModal",
    "ContextPanel",
    "DevicesView",
    "DiagnosticsView",
    "ExecutionResultModal",
    "FilesView",
    "HelpModal",
    "NavigationSidebar",
    "NetworkView",
    "NodesView",
    "NotesTasksView",
    "OverviewDashboard",
    "ParameterFormModal",
    "ProjectDetailModal",
    "ServicesView",
    "SettingsModal",
    "SettingsView",
    "StatusHeader",
    "SyncView",
    "SetupWizardModal",
]
