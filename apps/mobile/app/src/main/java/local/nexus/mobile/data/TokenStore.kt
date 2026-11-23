package local.nexus.mobile.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

/**
 * Token store: access/refresh JWTs live in EncryptedSharedPreferences
 * (Android Keystore-backed) — never plain SharedPreferences (plan §6.3).
 * The Core URL is plain DataStore (not secret).
 */
private val Context.dataStore by preferencesDataStore(name = "nexus_settings")

class TokenStore(private val context: Context) {

    private val secure by lazy {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "nexus_secure",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    fun saveTokens(access: String, refresh: String) {
        secure.edit().putString(KEY_ACCESS, access).putString(KEY_REFRESH, refresh).apply()
    }

    fun accessToken(): String? = secure.getString(KEY_ACCESS, null)
    fun refreshToken(): String? = secure.getString(KEY_REFRESH, null)

    fun clear() {
        secure.edit().clear().apply()
    }

    val coreUrl: Flow<String> = context.dataStore.data.map { prefs ->
        prefs[KEY_CORE_URL] ?: "https://nexus-control-plane-uvi8.onrender.com"
    }

    suspend fun setCoreUrl(url: String) {
        context.dataStore.edit { prefs -> prefs[KEY_CORE_URL] = url }
    }

    companion object {
        private const val KEY_ACCESS = "nexus.access"
        private const val KEY_REFRESH = "nexus.refresh"
        private val KEY_CORE_URL = stringPreferencesKey("nexus.core_url")
    }
}
