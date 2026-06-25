package com.example.data.remote.interceptors

import android.content.Context
import androidx.datastore.preferences.core.stringPreferencesKey
import com.example.data.remote.dataStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response

class AuthInterceptor(private val context: Context) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val tokenKey = stringPreferencesKey("jwt_token")
        
        // Em um aplicativo de produção, evite runBlocking no interceptor se ele for chamado
        // na thread principal, ou prefira um TokenManager assíncrono antes da chamada.
        // O OkHttp executa interceptores em threads de background (worker threads),
        // então runBlocking aqui é geralmente seguro e necessário para interceptores síncronos.
        val token = runBlocking {
            context.dataStore.data.first()[tokenKey]
        }

        val requestBuilder = chain.request().newBuilder()
        if (!token.isNullOrEmpty()) {
            requestBuilder.addHeader("Authorization", "Bearer $token")
        }
        
        return chain.proceed(requestBuilder.build())
    }
}
