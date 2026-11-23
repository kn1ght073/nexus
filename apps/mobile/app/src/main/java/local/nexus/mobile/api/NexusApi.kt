package local.nexus.mobile.api

import com.squareup.moshi.Json
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Header
import retrofit2.http.Path

/**
 * NEXUS Core API client (Retrofit + Moshi).
 *
 * Dev access: `adb reverse tcp:8000 tcp:8000` then hit 127.0.0.1:8000.
 * LAN access: https://nexus.local:8443 with the Node's CA pinned
 * (network_security_config.xml).
 */
data class LoginRequest(val email: String, val password: String)
data class TokenPair(val access_token: String, val refresh_token: String)
data class RegisterRequest(val email: String, val password: String)
data class UserOut(val id: Int, val email: String, val is_active: Boolean, val created_at: String)

data class Task(
    val id: Int,
    val title: String,
    val description: String? = null,
    val status: String = "pending",
    val project_id: Int? = null,
    val revision: Int = 1,
    val updated_at: String? = null,
)

data class TaskCreate(
    val title: String,
    val description: String? = null,
    val status: String = "pending",
    val project_id: Int? = null,
)

data class NoteCreate(val title: String, val content: String)
data class Note(val id: Int, val title: String, val content: String, val revision: Int = 1)

data class DeviceCreate(
    val name: String,
    val platform: String = "android",
    val capabilities: List<String> = listOf("notifications", "capture"),
)

data class DeviceOut(
    val id: Int,
    val name: String,
    val platform: String,
    val capabilities: List<String> = emptyList(),
    val is_online: Boolean = false,
)

interface NexusApi {
    @POST("api/auth/login")
    suspend fun login(@Body body: LoginRequest): TokenPair

    @POST("api/auth/register")
    suspend fun register(@Body body: RegisterRequest): UserOut

    @GET("api/auth/me")
    suspend fun me(@Header("Authorization") auth: String): UserOut

    @GET("api/tasks")
    suspend fun listTasks(@Header("Authorization") auth: String): List<Task>

    @POST("api/tasks")
    suspend fun createTask(@Header("Authorization") auth: String, @Body body: TaskCreate): Task

    @POST("api/tasks/{id}/done")
    suspend fun completeTask(@Header("Authorization") auth: String, @Path("id") id: Int): Task

    @POST("api/notes")
    suspend fun createNote(@Header("Authorization") auth: String, @Body body: NoteCreate): Note

    @GET("api/notes")
    suspend fun listNotes(@Header("Authorization") auth: String): List<Note>

    @POST("api/devices/register")
    suspend fun registerDevice(@Header("Authorization") auth: String, @Body body: DeviceCreate): DeviceOut

    @GET("api/devices")
    suspend fun listDevices(@Header("Authorization") auth: String): List<DeviceOut>
}

object NexusClient {
    @Volatile private var retrofit: Retrofit? = null
    @Volatile var baseUrl: String = "https://nexus-control-plane-uvi8.onrender.com/"
        set(value) {
            field = if (value.endsWith("/")) value else "$value/"
            retrofit = null // rebuild lazily
        }

    fun api(): NexusApi {
        return retrofit?.let { it.create(NexusApi::class.java) } ?: run {
            val logging = HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC }
            val client = OkHttpClient.Builder()
                .addInterceptor(logging)
                .build()
            val moshi = com.squareup.moshi.Moshi.Builder()
                .add(KotlinJsonAdapterFactory())
                .build()
            val r = Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(client)
                .addConverterFactory(MoshiConverterFactory.create(moshi))
                .build()
            retrofit = r
            r.create(NexusApi::class.java)
        }
    }

    fun bearer(token: String) = "Bearer $token"
}
