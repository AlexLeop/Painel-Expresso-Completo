package com.example.domain.models

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class LoginBootstrapResponse(
    val message: String
)

@JsonClass(generateAdapter = true)
data class WalletInfo(
    @Json(name = "balance_cents") val balanceCents: Int = 0
)

@JsonClass(generateAdapter = true)
data class CockpitResponse(
    val driver: DriverInfo,
    val shift: ShiftInfo?,
    val today: TodayStats,
    val wallet: WalletInfo = WalletInfo(),
    @Json(name = "active_order") val activeOrder: ActiveOrder?,
    @Json(name = "active_orders") val activeOrders: List<ActiveOrder> = emptyList(),
    @Json(name = "active_orders_count") val activeOrdersCount: Int = 0,
    @Json(name = "active_orders_limit") val activeOrdersLimit: Int = 3,
    @Json(name = "pending_documents") val pendingDocuments: Int = 0,
    @Json(name = "unread_messages") val unreadMessages: Int = 0
)

@JsonClass(generateAdapter = true)
data class DriverInfo(
    val id: String,
    val name: String,
    val online: Boolean = false,
    val active: Boolean = true,
    val status: String
)

@JsonClass(generateAdapter = true)
data class ShiftInfo(
    @Json(name = "schedule_id") val scheduleId: String? = null,
    @Json(name = "store_id") val storeId: String? = null,
    @Json(name = "store_name") val storeName: String? = null,
    @Json(name = "turno_id") val turnoId: String? = null,
    @Json(name = "turno_name") val turnoName: String? = null,
    val date: String? = null,
    @Json(name = "planned_minutes") val plannedMinutes: Int? = null,
    @Json(name = "session_id") val sessionId: String? = null,
    @Json(name = "checked_in_at") val checkedInAt: String? = null
)

@JsonClass(generateAdapter = true)
data class TodayStats(
    @Json(name = "earnings_cents") val earningsCents: Int,
    val deliveries: Int,
    @Json(name = "goal_progress_percent") val goalProgressPercent: Int = 0
)

@JsonClass(generateAdapter = true)
data class ActiveOrder(
    @Json(name = "order_id") val orderId: String,
    val status: String? = null,
    @Json(name = "fare_cents") val fareCents: Int = 0,
    @Json(name = "store_name") val storeName: String? = null,
    @Json(name = "manifest_id") val manifestId: String? = null,
    @Json(name = "next_stop_id") val nextStopId: String? = null,
    @Json(name = "next_stop_type") val nextStopType: String? = null,
    @Json(name = "next_stop_sequence") val nextStopSequence: Int? = null
)

@JsonClass(generateAdapter = true)
data class StatusRequest(
    val status: String,
    val reason: String? = null
)

@JsonClass(generateAdapter = true)
data class StoreSummary(
    val id: String,
    val name: String,
    @Json(name = "averagePrepTimeMinutes") val averagePrepTimeMinutes: Int = 0
)

@JsonClass(generateAdapter = true)
data class DriverOrderSummary(
    val id: String,
    val status: String,
    @Json(name = "fareValueCents") val fareValueCents: Int,
    @Json(name = "distanceMeters") val distanceMeters: Int? = null,
    @Json(name = "businessDate") val businessDate: String? = null,
    val store: StoreSummary,
    val driver: DriverInfo? = null,
    val manifest: String? = null
)

@JsonClass(generateAdapter = true)
data class SimplePoint(
    val lat: Double? = null,
    val lng: Double? = null
)

@JsonClass(generateAdapter = true)
data class OrderOrigin(
    @Json(name = "store_id") val storeId: String,
    @Json(name = "store_name") val storeName: String,
    @Json(name = "average_prep_minutes") val averagePrepMinutes: Int = 0,
    val location: SimplePoint? = null
)

@JsonClass(generateAdapter = true)
data class OrderDestination(
    @Json(name = "stops_count") val stopsCount: Int = 0,
    @Json(name = "last_stop_id") val lastStopId: String? = null,
    @Json(name = "last_stop_location") val lastStopLocation: SimplePoint? = null
)

@JsonClass(generateAdapter = true)
data class OrderStop(
    val id: String,
    val sequence: Int,
    val type: String,
    @Json(name = "requiresPin") val requiresPin: Boolean = false,
    @Json(name = "completedAt") val completedAt: String? = null,
    val location: SimplePoint? = null
)

@JsonClass(generateAdapter = true)
data class OrderDetailResponse(
    val id: String,
    val status: String,
    @Json(name = "fareValueCents") val fareValueCents: Int,
    @Json(name = "distanceMeters") val distanceMeters: Int? = null,
    @Json(name = "businessDate") val businessDate: String? = null,
    val origin: OrderOrigin,
    val destination: OrderDestination,
    @Json(name = "current_driver_id") val currentDriverId: String? = null,
    val stops: List<OrderStop> = emptyList()
)

@JsonClass(generateAdapter = true)
data class RejectReason(
    @Json(name = "reason_code") val reasonCode: String,
    @Json(name = "reason_text") val reasonText: String? = null
)

@JsonClass(generateAdapter = true)
data class ReleaseReason(
    val reason: String
)

@JsonClass(generateAdapter = true)
data class IncidentRequest(
    @Json(name = "order_id") val orderId: String? = null,
    @Json(name = "stop_id") val stopId: String? = null,
    val type: String,
    val description: String,
    val lat: Double? = null,
    val lng: Double? = null,
    val metadata: Map<String, String> = emptyMap()
)

@JsonClass(generateAdapter = true)
data class IncidentResponse(
    @Json(name = "incident_id") val incidentId: String,
    val status: String,
    val type: String
)

@JsonClass(generateAdapter = true)
data class ShiftCheckInRequest(
    @Json(name = "turno_id") val turnoId: String,
    @Json(name = "store_id") val storeId: String,
    val date: String
)

@JsonClass(generateAdapter = true)
data class ShiftCheckOutRequest(
    val reason: String? = null
)

@JsonClass(generateAdapter = true)
data class ShiftCheckInResponse(
    val message: String,
    @Json(name = "device_token") val deviceToken: String,
    @Json(name = "schedule_id") val scheduleId: String,
    @Json(name = "session_id") val sessionId: String
)

@JsonClass(generateAdapter = true)
data class ShiftCheckOutResponse(
    val message: String,
    @Json(name = "session_id") val sessionId: String,
    @Json(name = "worked_minutes") val workedMinutes: Int
)

@JsonClass(generateAdapter = true)
data class DriverCalendarItem(
    val kind: String,
    val date: String,
    val status: String,
    @Json(name = "store_id") val storeId: String,
    @Json(name = "store_name") val storeName: String,
    @Json(name = "turno_id") val turnoId: String,
    @Json(name = "turno_name") val turnoName: String
)

@JsonClass(generateAdapter = true)
data class ShiftReservationRequest(
    @Json(name = "store_id") val storeId: String,
    @Json(name = "turno_id") val turnoId: String,
    val date: String,
    val note: String? = null
)

@JsonClass(generateAdapter = true)
data class ShiftReservationResponse(
    @Json(name = "reservation_id") val reservationId: String,
    val status: String
)

@JsonClass(generateAdapter = true)
data class ProofUploadResponse(
    @Json(name = "proof_id") val proofId: String,
    val stage: String,
    @Json(name = "file_url") val fileUrl: String
)

@JsonClass(generateAdapter = true)
data class StopBatchCompleteItem(
    @Json(name = "stop_id") val stopId: String,
    @Json(name = "delivery_pin") val deliveryPin: String? = null,
    val lat: Double? = null,
    val lng: Double? = null,
    val timestamp: String
)

@JsonClass(generateAdapter = true)
data class CompleteBatchResponse(
    @Json(name = "completed_stops") val completedStops: List<String> = emptyList()
)

@JsonClass(generateAdapter = true)
data class LocationUpdate(
    val lat: Double,
    val lng: Double,
    val heading: Int,
    @Json(name = "speedKmh") val speedKmh: Int,
    val timestamp: Long
)

@JsonClass(generateAdapter = true)
data class PerformanceResponse(
    val deliveries: Int,
    @Json(name = "earnings_cents") val earningsCents: Int,
    @Json(name = "incidents_open") val incidentsOpen: Int,
    @Json(name = "acceptance_rate") val acceptanceRate: Double,
    @Json(name = "completion_rate") val completionRate: Double
)

@JsonClass(generateAdapter = true)
data class WalletBalanceResponse(
    val balanceCents: Int,
    val updatedAt: String
)

@JsonClass(generateAdapter = true)
data class WithdrawalRequestPayload(
    val amountCents: Int,
    val pixKey: String
)

@JsonClass(generateAdapter = true)
data class WithdrawalResponsePayload(
    val id: String,
    val amountCents: Int,
    val status: String,
    val pixKey: String,
    val createdAt: String
)

@JsonClass(generateAdapter = true)
data class WalletTransactionItem(
    val id: String,
    val amountCents: Int,
    val category: String,
    val taxCategory: String,
    val createdAt: String
)

@JsonClass(generateAdapter = true)
data class PaginatedTransactionsResponse(
    val items: List<WalletTransactionItem> = emptyList(),
    val count: Int = 0
)

@JsonClass(generateAdapter = true)
data class CommunicationThreadItem(
    @Json(name = "thread_id") val threadId: String,
    @Json(name = "order_id") val orderId: String? = null,
    @Json(name = "store_id") val storeId: String? = null,
    val status: String,
    @Json(name = "source_type") val sourceType: String,
    val subject: String? = null,
    @Json(name = "updated_at") val updatedAt: String? = null
)

@JsonClass(generateAdapter = true)
data class CommunicationMessageItem(
    @Json(name = "message_id") val messageId: String,
    @Json(name = "sender_type") val senderType: String,
    @Json(name = "sender_name") val senderName: String,
    val message: String,
    val metadata: Map<String, String> = emptyMap(),
    @Json(name = "created_at") val createdAt: String? = null
)

@JsonClass(generateAdapter = true)
data class CommunicationMessageRequest(
    val message: String,
    val metadata: Map<String, String> = emptyMap()
)

@JsonClass(generateAdapter = true)
data class CommunicationMessageSendResponse(
    @Json(name = "thread_id") val threadId: String,
    @Json(name = "message_id") val messageId: String
)
