package com.example.data.remote

import com.example.domain.models.*
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.*

interface DriverApiService {

    @POST("accounts/auth/login")
    suspend fun completeLoginBootstrap(): Response<LoginBootstrapResponse>

    @GET("driver/cockpit")
    suspend fun getCockpit(): Response<CockpitResponse>

    @POST("driver/status")
    suspend fun setStatus(@Body statusRequest: StatusRequest): Response<Unit>

    @GET("driver/orders")
    suspend fun getOrders(): Response<List<DriverOrderSummary>>

    @GET("driver/orders/{order_id}")
    suspend fun getOrderDetails(@Path("order_id") orderId: String): Response<OrderDetailResponse>

    @POST("driver/orders/{order_id}/accept")
    suspend fun acceptOrder(@Path("order_id") orderId: String): Response<DriverOrderSummary>

    @POST("driver/orders/{order_id}/reject")
    suspend fun rejectOrder(@Path("order_id") orderId: String, @Body reason: RejectReason): Response<Unit>
    
    @POST("driver/orders/{order_id}/start")
    suspend fun startOrder(@Path("order_id") orderId: String): Response<DriverOrderSummary>

    @POST("driver/orders/{order_id}/arrive")
    suspend fun arriveOrder(@Path("order_id") orderId: String): Response<DriverOrderSummary>

    @POST("driver/orders/{order_id}/release")
    suspend fun releaseOrder(@Path("order_id") orderId: String, @Body reason: ReleaseReason): Response<DriverOrderSummary>

    @Multipart
    @POST("driver/stops/{stop_id}/pickup-proof")
    suspend fun sendPickupProof(
        @Path("stop_id") stopId: String,
        @Part("proof_type") proofType: RequestBody,
        @Part("lat") lat: RequestBody?,
        @Part("lng") lng: RequestBody?,
        @Part("captured_at") capturedAt: RequestBody?,
        @Part file: MultipartBody.Part?
    ): Response<ProofUploadResponse>

    @Multipart
    @POST("driver/stops/{stop_id}/delivery-proof")
    suspend fun sendDeliveryProof(
        @Path("stop_id") stopId: String,
        @Part("proof_type") proofType: RequestBody,
        @Part("lat") lat: RequestBody?,
        @Part("lng") lng: RequestBody?,
        @Part("captured_at") capturedAt: RequestBody?,
        @Part file: MultipartBody.Part?
    ): Response<ProofUploadResponse>

    @POST("driver/stops/complete-batch")
    suspend fun completeStopsBatch(@Body items: List<StopBatchCompleteItem>): Response<CompleteBatchResponse>

    @POST("driver/incidents")
    suspend fun reportIncident(@Body incident: IncidentRequest): Response<IncidentResponse>

    @Multipart
    @POST("driver/incidents/{incident_id}/attachments")
    suspend fun uploadIncidentAttachment(
        @Path("incident_id") incidentId: String,
        @Part file: MultipartBody.Part
    ): Response<Unit>

    @POST
    suspend fun updateLocation(
        @Url url: String,
        @Header("X-Device-Token") deviceToken: String,
        @Body location: LocationUpdate
    ): Response<Unit>

    @POST("driver/shifts/check-in")
    suspend fun checkIn(@Body payload: ShiftCheckInRequest): Response<ShiftCheckInResponse>

    @POST("driver/shifts/check-out")
    suspend fun checkOut(@Body payload: ShiftCheckOutRequest): Response<ShiftCheckOutResponse>

    @GET("driver/shifts/calendar")
    suspend fun getShiftCalendar(
        @Query("start_date") startDate: String? = null,
        @Query("end_date") endDate: String? = null
    ): Response<List<DriverCalendarItem>>

    @POST("driver/shifts/reservations")
    suspend fun createShiftReservation(@Body payload: ShiftReservationRequest): Response<ShiftReservationResponse>

    @GET("driver/performance")
    suspend fun getPerformance(@Query("period") period: String): Response<PerformanceResponse>

    @GET("finance/wallet/balance")
    suspend fun getWalletBalance(): Response<WalletBalanceResponse>

    @GET("finance/transactions")
    suspend fun getWalletTransactions(
        @Query("limit") limit: Int = 50,
        @Query("offset") offset: Int = 0
    ): Response<PaginatedTransactionsResponse>

    @POST("finance/wallet/withdraw")
    suspend fun requestWalletWithdrawal(@Body payload: WithdrawalRequestPayload): Response<WithdrawalResponsePayload>

    @GET("driver/communications/threads")
    suspend fun getCommunicationThreads(): Response<List<CommunicationThreadItem>>

    @GET("driver/communications/threads/{thread_id}/messages")
    suspend fun getThreadMessages(@Path("thread_id") threadId: String): Response<List<CommunicationMessageItem>>

    @POST("driver/communications/threads/{thread_id}/messages")
    suspend fun sendThreadMessage(
        @Path("thread_id") threadId: String,
        @Body payload: CommunicationMessageRequest
    ): Response<CommunicationMessageSendResponse>

    @POST("driver/fcm-token")
    suspend fun registerFcmToken(@Body payload: Map<String, String>): Response<Unit>
}
