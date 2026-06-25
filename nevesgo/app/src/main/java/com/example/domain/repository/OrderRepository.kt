package com.example.domain.repository

import com.example.data.local.OrderEntity
import com.example.domain.models.OrderDetailResponse
import kotlinx.coroutines.flow.Flow

interface OrderRepository {
    val allOrders: Flow<List<OrderEntity>>
    fun getOrdersByStatus(status: String): Flow<List<OrderEntity>>
    fun getOrdersByStatuses(statuses: List<String>): Flow<List<OrderEntity>>
    suspend fun insert(order: OrderEntity)
    suspend fun insertAll(orders: List<OrderEntity>)
    suspend fun update(order: OrderEntity)
    suspend fun clearAll()
    suspend fun syncOrders()
    suspend fun acceptOrder(orderId: String)
    suspend fun startOrder(orderId: String): Result<Unit>
    suspend fun arriveOrder(orderId: String): Result<Unit>
    suspend fun rejectOrder(orderId: String, reasonCode: String, reasonText: String? = null): Result<Unit>
    suspend fun releaseOrder(orderId: String, reason: String): Result<Unit>
    suspend fun getOrderDetails(orderId: String): Result<OrderDetailResponse>
    suspend fun finishOrder(orderId: String, stopId: String, deliveryPin: String? = null): Result<Unit>
    suspend fun reportIncident(orderId: String?, stopId: String?, type: String, description: String): Result<Unit>
}
