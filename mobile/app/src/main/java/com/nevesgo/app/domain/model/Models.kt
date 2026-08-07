package com.nevesgo.app.domain.model

data class DriverCockpitResponse(
    val driver: DriverInfo,
    val shift: ShiftInfo?,
    val today: TodayInfo,
    val active_order: ActiveOrderInfo?,
    val active_orders: List<ActiveOrderInfo>,
    val active_orders_count: Int,
    val active_orders_limit: Int,
    val alerts: List<AlertInfo>,
    val pending_checklists: Int,
    val open_incidents: Int,
    val unread_messages: Int
)

data class DriverInfo(
    val id: String,
    val name: String,
    val status: String
)

data class ShiftInfo(
    val id: String,
    val started_at: String,
    val worked_minutes: Int
)

data class TodayInfo(
    val earnings_cents: Int,
    val deliveries: Int,
    val goal_progress_percent: Int
)

data class ActiveOrderInfo(
    val order_id: String,
    val manifest_id: String?,
    val next_stop_id: String?,
    val next_stop_type: String?
)

data class AlertInfo(
    val code: String,
    val message: String
)

data class OrderResponse(
    val id: String,
    val origin: LocationInfo,
    val destination: LocationInfo,
    val distance_meters: Int,
    val estimated_seconds: Int,
    val fare_cents: Int,
    val sla_seconds: Int,
    val weight_grams: Int,
    val volume_cm3: Int,
    val packages_count: Int,
    val stops: List<StopInfo>
)

data class LocationInfo(
    val name: String,
    val address: String
)

data class StopInfo(
    val id: String,
    val sequence: Int,
    val type: String
)

data class WalletBalanceResponse(
    val balance_cents: Int
)
