package com.example.data.remote.interceptors

import okhttp3.Interceptor
import okhttp3.Response
import java.util.UUID

class IdempotencyInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val method = request.method
        
        // Add Idempotency-Key only to state-changing requests
        if (method == "POST" || method == "PUT" || method == "PATCH" || method == "DELETE") {
            // Check if it already has one (e.g., for retries)
            if (request.header("Idempotency-Key") == null) {
                val newRequest = request.newBuilder()
                    .addHeader("Idempotency-Key", UUID.randomUUID().toString())
                    .build()
                return chain.proceed(newRequest)
            }
        }
        
        return chain.proceed(request)
    }
}
