package com.example.data.remote.interceptors

import android.util.Log
import okhttp3.Interceptor
import okhttp3.Response
import java.io.IOException

class RetryInterceptor(private val maxRetries: Int = 3) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        var response: Response? = null
        var tryCount = 0
        var exception: Exception? = null

        while (tryCount < maxRetries && (response == null || !response.isSuccessful)) {
            try {
                if (tryCount > 0) {
                    Log.d("RetryInterceptor", "Tentativa ${tryCount + 1} de $maxRetries para ${request.url}")
                    // Backoff exponencial simples: 1s, 2s, 4s...
                    Thread.sleep((1000 * Math.pow(2.0, (tryCount - 1).toDouble())).toLong())
                }
                
                // Se já temos uma resposta (que falhou com 5xx, etc), precisamos fechá-la antes de tentar de novo
                response?.close()
                
                response = chain.proceed(request)
                
                // Se a requisição for bem sucedida ou for erro do cliente (4xx), não vamos tentar de novo
                // Focamos o retry em instabilidades de rede (IOException) ou erros no servidor (5xx)
                if (response.isSuccessful || (response.code in 400..499)) {
                    break
                }
                
            } catch (e: IOException) {
                exception = e
                Log.e("RetryInterceptor", "Falha de rede na tentativa ${tryCount + 1}", e)
            }
            tryCount++
        }

        // Se após todas as tentativas a resposta for nula, lançamos a última exceção capturada
        return response ?: throw exception ?: IOException("Falha de rede desconhecida após $maxRetries tentativas")
    }
}
