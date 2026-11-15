package local.nexus.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.lifecycle.viewmodel.compose.viewModel
import local.nexus.mobile.data.TokenStore
import local.nexus.mobile.ui.LoginScreen
import local.nexus.mobile.ui.LoginViewModel
import local.nexus.mobile.ui.TasksScreen
import local.nexus.mobile.ui.TasksViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val tokenStore = TokenStore(this)
        setContent {
            NexusTheme {
                NexusApp(tokenStore)
            }
        }
    }
}

@Composable
fun NexusTheme(content: @Composable () -> Unit) {
    // NEXUS ships a single dark theme regardless of system setting,
    // matching the Desktop/CLI aesthetic.
    MaterialTheme(colorScheme = darkColorScheme(), content = content)
}

@Composable
fun NexusApp(store: TokenStore) {
    val loginVm: LoginViewModel = viewModel(factory = viewModelFactory { initializer { LoginViewModel(store) } })
    val loginState by loginVm.state.collectAsState()

    if (loginState.loggedIn) {
        val tasksVm: TasksViewModel = viewModel(factory = viewModelFactory { initializer { TasksViewModel(store) } })
        TasksScreen(tasksVm)
    } else {
        LoginScreen(loginVm)
    }
}
