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
    private val context: android.content.Context,
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
                                order.toEntity(details, context)
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

    override suspend fun arriveOrder(orderId: String): Result<Unit> {
        return try {
            val response = apiService.arriveOrder(orderId)
            if (response.isSuccessful) {
                val order = orderDao.getOrderById(orderId)
                if (order != null) {
                    orderDao.update(order.copy(status = response.body()?.status ?: "ARRIVED", syncStatus = "SYNCED"))
                }
                Result.success(Unit)
            } else {
                Result.failure(Exception("Falha ao registrar chegada: ${response.code()} ${response.message()}"))
            }
        } catch (e: java.io.IOException) {
            Result.failure(Exception("Sem conexão com a internet. Tente registrar chegada novamente."))
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

    override suspend fun finishOrder(orderId: String, stopId: String, deliveryPin: String?, deliveryProofUri: android.net.Uri?): Result<Unit> {
        return try {
            val nowIso = Instant.now().toString()
            val textPlain = "text/plain".toMediaType()
            val imageJpeg = "image/jpeg".toMediaType()
            
            val filePart: okhttp3.MultipartBody.Part? = if (deliveryProofUri != null) {
                val requestFile = object : okhttp3.RequestBody() {
                    override fun contentType() = imageJpeg
                    override fun writeTo(sink: okio.BufferedSink) {
                        context.contentResolver.openInputStream(deliveryProofUri)?.use { inputStream ->
                            sink.writeAll(okio.Okio.source(inputStream))
                        }
                    }
                }
                okhttp3.MultipartBody.Part.createFormData("file", "proof.jpg", requestFile)
            } else {
                null
            }

            val proofTypeStr = if (deliveryPin != null) "PIN" else "PHOTO"

            val proofResponse = apiService.sendDeliveryProof(
                stopId = stopId,
                proofType = okhttp3.RequestBody.create(textPlain, proofTypeStr),
                lat = null,
                lng = null,
                capturedAt = okhttp3.RequestBody.create(textPlain, nowIso),
                file = filePart
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

    override suspend fun reportIncident(orderId: String?, stopId: String?, type: String, description: String, incidentProofUri: android.net.Uri?): Result<Unit> {
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
                val incidentId = response.body()?.incidentId
                if (incidentId != null && incidentProofUri != null) {
                    val imageJpeg = "image/jpeg".toMediaType()
                    val requestFile = object : okhttp3.RequestBody() {
                        override fun contentType() = imageJpeg
                        override fun writeTo(sink: okio.BufferedSink) {
                            context.contentResolver.openInputStream(incidentProofUri)?.use { inputStream ->
                                sink.writeAll(okio.Okio.source(inputStream))
                            }
                        }
                    }
                    val filePart = okhttp3.MultipartBody.Part.createFormData("file", "incident.jpg", requestFile)
                    apiService.uploadIncidentAttachment(incidentId, filePart)
                }
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

private fun getAddress(context: android.content.Context?, lat: Double, lng: Double): String? {
    if (context == null) return "Lat $lat, Lng $lng"
    return try {
        val geocoder = android.location.Geocoder(context, java.util.Locale.getDefault())
        val addresses = geocoder.getFromLocation(lat, lng, 1)
        if (!addresses.isNullOrEmpty()) {
            val address = addresses[0]
            val street = address.thoroughfare ?: ""
            val number = address.subThoroughfare ?: ""
            val city = address.locality ?: address.subAdminArea ?: ""
            listOf(street, number, city).filter { it.isNotBlank() }.joinToString(", ").takeIf { it.isNotBlank() } ?: "Lat $lat, Lng $lng"
        } else {
            "Lat $lat, Lng $lng"
        }
    } catch (e: Exception) {
        "Lat $lat, Lng $lng"
    }
}

private fun DriverOrderSummary.toEntity(details: OrderDetailResponse?, context: android.content.Context? = null): OrderEntity {
    val originAddress = details?.origin?.location?.let { point ->
        if (point.lat != null && point.lng != null) {
            getAddress(context, point.lat, point.lng)
        } else {
            null
        }
    } ?: "Origem vinculada a ${store.name}"

    val destinationAddress = details?.destination?.lastStopLocation?.let { point ->
        if (point.lat != null && point.lng != null) {
            getAddress(context, point.lat, point.lng)
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
