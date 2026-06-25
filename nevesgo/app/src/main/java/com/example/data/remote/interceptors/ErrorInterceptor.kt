package com.example.data.remote.interceptors

import android.content.Context
import android.content.Intent
import android.util.Log
import okhttp3.Interceptor
import okhttp3.Response
import java.io.IOException

class ErrorInterceptor(private val context: Context) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val response: Response
        
        try {
            response = chain.proceed(request)
        } catch (e: Exception) {
            Log.e("NetworkError", "Network connection error", e)
            throw IOException("Falha na conexão de rede. Verifique sua internet.", e)
        }

        if (!response.isSuccessful) {
            val code = response.code
            val message = response.message
            Log.e("NetworkError", "HTTP Error $code: $message")
            
            when (code) {
                401 -> {
                    // Tratar token expirado ou não autorizado
                    Log.e("NetworkError", "Não autorizado. O token JWT pode estar expirado.")
                    // Lógica para renovar token ou deslogar o usuário iria aqui
                    context.sendBroadcast(Intent("com.example.ACTION_LOGOUT").apply {
                        setPackage(context.packageName)
                    })
                }
                403 -> {
                    Log.e("NetworkError", "Acesso negado (Proibido).")
                }
                404 -> {
                    Log.e("NetworkError", "Recurso não encontrado.")
                }
                in 500..599 -> {
                    Log.e("NetworkError", "Erro no servidor.")
                }
            }
        }
        
        return response
    }
}
