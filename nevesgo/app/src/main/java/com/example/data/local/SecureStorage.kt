package com.example.data.local

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

object SecureStorage {
    private const val PREFS_NAME = "secure_prefs"

    fun getPrefs(context: Context): SharedPreferences {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        return EncryptedSharedPreferences.create(
            context,
            PREFS_NAME,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    fun saveToken(context: Context, token: String) {
        getPrefs(context).edit().putString("jwt_token", token).apply()
    }

    fun getToken(context: Context): String? {
        return getPrefs(context).getString("jwt_token", null)
    }

    fun clearToken(context: Context) {
        getPrefs(context).edit().remove("jwt_token").apply()
    }

    fun saveRefreshToken(context: Context, token: String) {
        getPrefs(context).edit().putString("refresh_token", token).apply()
    }

    fun getRefreshToken(context: Context): String? {
        return getPrefs(context).getString("refresh_token", null)
    }
}
