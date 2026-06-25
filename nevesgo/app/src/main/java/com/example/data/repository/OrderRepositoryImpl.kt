package com.example.data.repository

import com.example.data.local.OrderDao
import com.example.data.local.OrderEntity
import com.example.data.remote.DriverApiService
import com.example.domain.models.DriverOrderSummary
import com.example.domain.models.IncidentRequest
import com.example.domain.models.StopBatchCompleteItem
import com.example.domain.models.OrderDetailResponse
import com.example.domain.models.RejectReason
import com.example.domain.models.ReleaseReason
import com.example.domain.repository.OrderRepository
import kotlinx.coroutines.flow.Flow
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.time.Instant

class OrderRepositoryImpl(
    private val orderDao: OrderDao,
    private val apiService: DriverApiService
) : OrderRepository {

    override val allOrders: Flow<List<OrderEntity>> = orderDao.getAllOrders()

    override fun getOrdersByStatus(status: String): Flow<List<OrderEntity>> {
        return orderDao.getOrdersByStatus(status)
    }

    override fun getOrdersByStatuses(statuses: List<String>): Flow<List<OrderEntity>> {
        return orderDao.getOrdersByStatuses(statuses)
    }

    override suspend fun insert(order: OrderEntity) {
        orderDao.insert(order)
    }
    
    override suspend fun insertAll(orders: List<OrderEntity>) {
        orderDao.insertAll(orders)
    }

    override suspend fun update(order: OrderEntity) {
        orderDao.update(order)
    }
    
    override suspend fun clearAll() {
        orderDao.clearAll()
    }

    override suspend fun syncOrders() {
        try {
            val response = apiService.getOrders()
            if (response.isSuccessful) {
                response.body()?.let { orders ->
                    val entities = kotlinx.coroutines.coroutineScope {
                        orders.map { order ->
                            kotlinx.coroutines.async {
                                val details = try {
                                    apiService.getOrderDetails(order.id).takeIf { it.isSuccessful }?.body()
                                } catch (e: Exception) {
                                    if (e is kotlinx.coroutines.CancellationException) throw e
                                    null
                                }
                                order.toEntity(details)
                            }
                        }.let { kotlinx.coroutines.awaitAll(*it.toTypedArray()) }
                    }
                    orderDao.clearAll()
                    orderDao.insertAll(entities)
                }
            }
        } catch (e: Exception) {
            // Log error
        }
    }

    override suspend fun acceptOrder(orderId: String) {
        try {
            val response = apiService.acceptOrder(orderId)
            if (response.isSuccessful) {
                val order = orderDao.getOrderById(orderId)
                if (order != null) {
                    val acceptedStatus = response.body()?.status ?: "ACCEPTED"
                    orderDao.update(order.copy(status = acceptedStatus, syncStatus = "SYNCED"))
                }
            }
        } catch (e: Exception) {
            val order = orderDao.getOrderById(orderId)
            if (order != null) {
                orderDao.update(order.copy(syncStatus = "PENDING_ACCEPT"))
            }
        }
    }

    override suspend fun startOrder(orderId: String): Result<Unit> {
        return try {
            val response = apiService.startOrder(orderId)
            if (response.isSuccessful) {
                val order = orderDao.getOrderById(orderId)
                if (order != null) {
                    orderDao.update(order.copy(status = response.body()?.status ?: "STARTED", syncStatus = "SYNCED"))
                }
                Result.success(Unit)
            } else {
                Result.failure(Exception("Falha ao iniciar ordem: ${response.code()} ${response.message()}"))
            }
        } catch (e: java.io.IOException) {
            Result.failure(Exception("Sem conexão com a internet. Tente aceitar a corrida novamente."))
        } catch (e: Exception) {
            if (e is kotlinx.coroutines.CancellationException) throw e
            Result.failure(e)
        }
    }

    override suspend fun rejectOrder(orderId: String, reasonCode: String, reasonText: String?): Result<Unit> {
        return try {
            val response = apiService.rejectOrder(orderId, RejectReason(reasonCode = reasonCode, reasonText = reasonText))
            if (response.isSuccessful) {
                orderDao.getOrderById(orderId)?.let { orderDao.delete(it) }
                Result.success(Unit)
            } else {
                Result.failure(Exception("Falha ao recusar ordem: ${response.code()} ${response.message()}"))
            }
        } catch (e: java.io.IOException) {
            Result.failure(Exception("Sem conexão com a internet. Tente recusar a corrida novamente."))
        } catch (e: Exception) {
            if (e is kotlinx.coroutines.CancellationException) throw e
            Result.failure(e)
        }
    }

    override suspend fun releaseOrder(orderId: String, reason: String): Result<Unit> {
        return try {
            val response = apiService.releaseOrder(orderId, ReleaseReason(reason))
            if (response.isSuccessful) {
                val updatedStatus = response.body()?.status ?: "OFFERED"
                orderDao.getOrderById(orderId)?.let {
                    orderDao.update(it.copy(status = updatedStatus, syncStatus = "SYNCED"))
                }
                Result.success(Unit)
            } else {
                Result.failure(Exception("Falha ao devolver ordem: ${response.code()} ${response.message()}"))
            }
        } catch (e: java.io.IOException) {
            Result.failure(Exception("Sem conexão com a internet. Tente devolver a corrida novamente."))
        } catch (e: Exception) {
            if (e is kotlinx.coroutines.CancellationException) throw e
            Result.failure(e)
        }
    }

    override suspend fun getOrderDetails(orderId: String): Result<OrderDetailResponse> {
        return try {
            val response = apiService.getOrderDetails(orderId)
            if (response.isSuccessful) {
                response.body()?.let { Result.success(it) }
                    ?: Result.failure(Exception("Body is null"))
            } else {
                Result.failure(Exception("Falha ao carregar detalhes: ${response.code()} ${response.message()}"))
            }
        } catch (e: java.io.IOException) {
            Result.failure(Exception("Sem conexão com a internet. Verifique sua rede."))
        } catch (e: Exception) {
            if (e is kotlinx.coroutines.CancellationException) throw e
            Result.failure(e)
        }
    }

    override suspend fun finishOrder(orderId: String, stopId: String, deliveryPin: String?): Result<Unit> {
        return try {
            val nowIso = Instant.now().toString()
            val textPlain = "text/plain".toMediaType()
            val emptyFile = "dummy".toRequestBody(textPlain)
            val dummyPart = okhttp3.MultipartBody.Part.createFormData("file", "dummy.txt", emptyFile)

            val proofResponse = apiService.sendDeliveryProof(
                stopId = stopId,
                proofType = "PIN".toRequestBody(textPlain),
                lat = null,
                lng = null,
                capturedAt = nowIso.toRequestBody(textPlain),
                file = dummyPart
            )
            if (!proofResponse.isSuccessful) {
                return Result.failure(Exception("Falha ao enviar prova de entrega: ${proofResponse.code()} ${proofResponse.message()}"))
            }

            val completionResponse = apiService.completeStopsBatch(
                items = listOf(
                    StopBatchCompleteItem(
                        stopId = stopId,
                        deliveryPin = deliveryPin,
                        timestamp = nowIso
                    )
                )
            )
            if (completionResponse.isSuccessful) {
                val order = orderDao.getOrderById(orderId)
                if (order != null) {
                    orderDao.update(order.copy(status = "COMPLETED", syncStatus = "SYNCED"))
                }
                Result.success(Unit)
            } else {
                val order = orderDao.getOrderById(orderId)
                if (order != null) {
                    orderDao.update(order.copy(syncStatus = "PENDING_COMPLETE_BATCH"))
                }
                Result.failure(Exception("Falha ao concluir parada: ${completionResponse.code()} ${completionResponse.message()}"))
            }
        } catch (e: java.io.IOException) {
            orderDao.getOrderById(orderId)?.let {
                orderDao.update(it.copy(syncStatus = "PENDING_COMPLETE_BATCH"))
            }
            Result.failure(Exception("Você está sem internet! Conecte-se a uma rede 4G ou Wi-Fi para finalizar a entrega."))
        } catch (e: Exception) {
            orderDao.getOrderById(orderId)?.let {
                orderDao.update(it.copy(syncStatus = "PENDING_COMPLETE_BATCH"))
            }
            Result.failure(e)
        }
    }

    override suspend fun reportIncident(orderId: String?, stopId: String?, type: String, description: String): Result<Unit> {
        return try {
            val response = apiService.reportIncident(
                IncidentRequest(
                    orderId = orderId,
                    stopId = stopId,
                    type = type,
                    description = description
                )
            )
            if (response.isSuccessful) {
                Result.success(Unit)
            } else {
                Result.failure(Exception("Falha ao reportar incidente: ${response.code()} ${response.message()}"))
            }
        } catch (e: java.io.IOException) {
            Result.failure(Exception("Sem conexão com a internet. Verifique sua rede."))
        } catch (e: Exception) {
            if (e is kotlinx.coroutines.CancellationException) throw e
            Result.failure(e)
        }
    }
}

private fun DriverOrderSummary.toEntity(details: OrderDetailResponse?): OrderEntity {
    val originAddress = details?.origin?.location?.let { point ->
        if (point.lat != null && point.lng != null) {
            "Lat ${point.lat}, Lng ${point.lng}"
        } else {
            null
        }
    } ?: "Origem vinculada a ${store.name}"

    val destinationAddress = details?.destination?.lastStopLocation?.let { point ->
        if (point.lat != null && point.lng != null) {
            "Lat ${point.lat}, Lng ${point.lng}"
        } else {
            null
        }
    } ?: "Abra os detalhes da entrega"

    return OrderEntity(
        id = id,
        originName = details?.origin?.storeName ?: store.name,
        originAddress = originAddress,
        destinationName = details?.destination?.lastStopId ?: "Destino final",
        destinationAddress = destinationAddress,
        distanceMeters = distanceMeters ?: 0,
        fareCents = fareValueCents,
        slaSeconds = 0,
        status = status,
        syncStatus = "SYNCED"
    )
}
