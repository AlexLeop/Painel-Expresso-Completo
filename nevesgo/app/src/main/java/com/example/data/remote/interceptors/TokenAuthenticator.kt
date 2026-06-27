package com.example.data.remote.interceptors

import android.content.Context
import com.example.data.local.SecureStorage
import okhttp3.Authenticator
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route

class TokenAuthenticator(private val context: Context) : Authenticator {
    private val Response.responseCount: Int
        get() {
            var result = 1
            var current = priorResponse
            while (current != null) {
                result++
                current = current.priorResponse
            }
            return result
        }

    override fun authenticate(route: Route?, response: Response): Request? {
        // Prevent infinite loops if refresh fails
        if (response.responseCount >= 3) {
            return null
        }

        val currentToken = SecureStorage.getToken(context)
        val refreshToken = SecureStorage.getRefreshToken(context)

        if (currentToken.isNullOrEmpty() || refreshToken.isNullOrEmpty()) {
            return null
        }

        // Call the synchronous API to refresh the token using OKHttp
        val client = okhttp3.OkHttpClient()
        
        // Supabase REST endpoint for token refresh
        val supabaseUrl = ""
        val supabaseKey = ""
        
        if (supabaseUrl.isEmpty()) return null

        val requestBody = okhttp3.RequestBody.create(
            "application/json".toMediaTypeOrNull(),
            """{"refresh_token": "$refreshToken"}"""
        )

        val request = Request.Builder()
            .url("$supabaseUrl/auth/v1/token?grant_type=refresh_token")
            .post(requestBody)
            .addHeader("apikey", supabaseKey)
            .addHeader("Content-Type", "application/json")
            .build()

        try {
            val refreshResponse = client.newCall(request).execute()
            if (refreshResponse.isSuccessful) {
                refreshResponse.body?.string()?.let { bodyString ->
                    // Parse JSON manually or use org.json.JSONObject (Android standard)
                    try {
                        val jsonObject = org.json.JSONObject(bodyString)
                        val newAccessToken = jsonObject.optString("access_token")
                        val newRefreshToken = jsonObject.optString("refresh_token")
                        
                        if (newAccessToken.isNotEmpty()) {
                            SecureStorage.saveToken(context, newAccessToken)
                            SecureStorage.saveRefreshToken(context, newRefreshToken)
                            
                            return response.request.newBuilder()
                                .header("Authorization", "Bearer $newAccessToken")
                                .build()
                        }
                    } catch (e: Exception) {
                        e.printStackTrace()
                    }
                }
            } else {
                // If refresh fails, clear tokens
                SecureStorage.clearToken(context)
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }

        return null
    }
}
