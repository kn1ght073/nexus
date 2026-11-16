package local.nexus.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import local.nexus.mobile.api.LoginRequest
import local.nexus.mobile.api.NexusClient
import local.nexus.mobile.api.Task
import local.nexus.mobile.api.TaskCreate
import local.nexus.mobile.data.TokenStore

/**
 * Minimal MVVM scaffold: LoginViewModel + TasksViewModel wired to the Core
 * API; MainActivity renders login or the task list. Quick-capture flow
 * (text/voice) and offline Room cache are the next milestone (progress.md).
 */
class LoginViewModel(private val store: TokenStore) : ViewModel() {
    data class State(val busy: Boolean = false, val error: String? = null, val loggedIn: Boolean = store.accessToken() != null)

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state

    fun login(email: String, password: String) {
        viewModelScope.launch {
            _state.value = State(busy = true)
            try {
                val tokens = NexusClient.api().login(LoginRequest(email, password))
                store.saveTokens(tokens.access_token, tokens.refresh_token)
                _state.value = State(loggedIn = true)
            } catch (e: Exception) {
                _state.value = State(error = e.message ?: "login failed")
            }
        }
    }

    fun logout() {
        store.clear()
        _state.value = State()
    }
}

class TasksViewModel(private val store: TokenStore) : ViewModel() {
    data class State(val tasks: List<Task> = emptyList(), val busy: Boolean = false, val error: String? = null)

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state

    private fun auth(): String {
        val token = store.accessToken() ?: error("not logged in")
        return NexusClient.bearer(token)
    }

    fun refresh() {
        viewModelScope.launch {
            _state.value = State(busy = true)
            try {
                _state.value = State(tasks = NexusClient.api().listTasks(auth()))
            } catch (e: Exception) {
                _state.value = State(error = e.message ?: "failed to load")
            }
        }
    }

    fun createTask(title: String) {
        viewModelScope.launch {
            try {
                NexusClient.api().createTask(auth(), TaskCreate(title = title))
                refresh()
            } catch (e: Exception) {
                _state.value = State(tasks = _state.value.tasks, error = e.message)
            }
        }
    }

    fun completeTask(id: Int) {
        viewModelScope.launch {
            try {
                NexusClient.api().completeTask(auth(), id)
                refresh()
            } catch (e: Exception) {
                _state.value = State(tasks = _state.value.tasks, error = e.message)
            }
        }
    }
}

@Composable
fun LoginScreen(viewModel: LoginViewModel) {
    val state by viewModel.state.collectAsState()
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }

    Column(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("NEXUS", style = MaterialTheme.typography.headlineLarge)
        Text("capture → structure → everywhere", style = MaterialTheme.typography.bodySmall)
        Spacer(Modifier.height(24.dp))
        OutlinedTextField(value = email, onValueChange = { email = it }, label = { Text("Email") }, modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(value = password, onValueChange = { password = it }, label = { Text("Password") }, modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.height(16.dp))
        Button(
            onClick = { viewModel.login(email, password) },
            enabled = !state.busy && email.isNotBlank() && password.length >= 8,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(if (state.busy) "…" else "Log in") }
        state.error?.let {
            Spacer(Modifier.height(8.dp))
            Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
fun TasksScreen(viewModel: TasksViewModel) {
    val state by viewModel.state.collectAsState()
    var newTask by remember { mutableStateOf("") }

    LaunchedEffect(Unit) { viewModel.refresh() }

    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(
                value = newTask,
                onValueChange = { newTask = it },
                placeholder = { Text("Quick capture…") },
                modifier = Modifier.weight(1f),
            )
            Spacer(Modifier.width(8.dp))
            Button(onClick = { viewModel.createTask(newTask); newTask = "" }, enabled = newTask.isNotBlank()) { Text("+") }
        }
        state.error?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
        Spacer(Modifier.height(12.dp))

        if (state.busy && state.tasks.isEmpty()) {
            CircularProgressIndicator(Modifier.padding(24.dp))
        }

        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(state.tasks, key = { it.id }) { task ->
                Card(Modifier.fillMaxWidth()) {
                    Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(task.title, style = MaterialTheme.typography.titleMedium)
                            Text("${task.status} · rev ${task.revision}", style = MaterialTheme.typography.bodySmall)
                        }
                        if (task.status != "completed") {
                            TextButton(onClick = { viewModel.completeTask(task.id) }) { Text("Done") }
                        }
                    }
                }
            }
        }
    }
}
