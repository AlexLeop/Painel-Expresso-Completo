package com.nevesgo.app.di

import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody

class MockInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val uri = request.url.toUri().toString()

        val responseString = when {
            uri.contains("orders") -> """
                [
                  {
                    "id": "ORD-8829",
                    "origin": { "name": "Restaurante Sabor Real", "address": "Rua das Flores, 123" },
                    "destination": { "name": "Ana Beatriz S.", "address": "Rua das Flores, 123 - Apt 42" },
                    "distance_meters": 4200,
                    "estimated_seconds": 1020,
                    "fare_cents": 2890,
                    "stops": []
                  }
                ]
            """.trimIndent()
            uri.contains("cockpit") -> """
                {
                  "driver": { "id": "1", "name": "Leandro Neves", "status": "ONLINE" },
                  "today": { "earnings_cents": 15000, "deliveries": 12, "goal_progress_percent": 80 },
                  "active_order": null,
                  "active_orders": [
                    { "order_id": "ORD-8829", "next_stop_type": "PICKUP" }
                  ],
                  "active_orders_count": 1,
                  "active_orders_limit": 3,
                  "alerts": [],
                  "pending_checklists": 0,
                  "open_incidents": 0,
                  "unread_messages": 0
                }
            """.trimIndent()
            uri.contains("balance") -> "{ \"balance_cents\": 45000 }"
            uri.contains("transactions") -> "[]"
            uri.contains("calendar") -> "[]"
            else -> "{}"
        }

        return Response.Builder()
            .code(200)
            .message("OK")
            .request(request)
            .protocol(Protocol.HTTP_1_1)
            .body(responseString.toResponseBody("application/json".toMediaTypeOrNull()))
            .addHeader("content-type", "application/json")
            .build()
    }
}
