package com.nevesgo.app.domain.repository

import com.nevesgo.app.data.api.CorridaApi

class CorridaRepository(private val api: CorridaApi) {
    suspend fun getCockpit() = api.getCockpit()
    suspend fun getOrders() = api.getOrders()
    suspend fun acceptOrder(orderId: String) = api.acceptOrder(orderId)
    suspend fun rejectOrder(orderId: String, reason: Any) = api.rejectOrder(orderId, reason)
    suspend fun startOrder(orderId: String) = api.startOrder(orderId)
    suspend fun submitDeliveryProof(stopId: String, proof: Any) = api.submitDeliveryProof(stopId, proof)
    suspend fun completeBatch() = api.completeBatch()
}
