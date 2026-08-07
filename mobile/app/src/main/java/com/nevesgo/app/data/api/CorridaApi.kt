package com.nevesgo.app.data.api

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import com.nevesgo.app.domain.model.DriverCockpitResponse
import com.nevesgo.app.domain.model.OrderResponse

interface CorridaApi {
    @GET("driver/cockpit")
    suspend fun getCockpit(): Response<DriverCockpitResponse>

    @GET("driver/orders")
    suspend fun getOrders(): Response<List<OrderResponse>>

    @POST("driver/orders/{order_id}/accept")
    suspend fun acceptOrder(@Path("order_id") orderId: String): Response<Unit>

    @POST("driver/orders/{order_id}/reject")
    suspend fun rejectOrder(@Path("order_id") orderId: String, @Body reason: Any): Response<Unit>

    @POST("driver/orders/{order_id}/start")
    suspend fun startOrder(@Path("order_id") orderId: String): Response<Unit>

    @POST("driver/stops/{stop_id}/delivery-proof")
    suspend fun submitDeliveryProof(@Path("stop_id") stopId: String, @Body proof: Any): Response<Unit>

    @POST("driver/stops/complete-batch")
    suspend fun completeBatch(): Response<Unit>
}
