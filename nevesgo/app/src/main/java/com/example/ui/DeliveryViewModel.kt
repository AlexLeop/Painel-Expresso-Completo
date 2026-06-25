package com.example.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.MyApplication
import com.example.data.local.OrderEntity
import com.example.domain.models.OrderDetailResponse
import com.example.domain.repository.OrderRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class DeliveryViewModel(application: Application) : AndroidViewModel(application) {
    private val repository: OrderRepository
    private val activeStatuses = listOf("ACCEPTED", "STARTED", "ARRIVED", "CANCELED_IN_TRANSIT", "RETURNING_TO_STORE")
    private val _orderDetails = MutableStateFlow<Map<String, OrderDetailResponse>>(emptyMap())
    val orderDetails = _orderDetails.asStateFlow()
    private val _operationError = MutableStateFlow<String?>(null)
    val operationError = _operationError.asStateFlow()

    val allDeliveries: StateFlow<List<OrderEntity>>
    
    val pendingDeliveries: StateFlow<List<OrderEntity>>
    val inProgressDeliveries: StateFlow<List<OrderEntity>>
    val completedDeliveries: StateFlow<List<OrderEntity>>

    init {
        val container = (application as MyApplication).container
        repository = container.orderRepository
        
        allDeliveries = repository.allOrders.stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )
        
        pendingDeliveries = repository.getOrdersByStatus("OFFERED").stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )
        
        inProgressDeliveries = repository.getOrdersByStatuses(activeStatuses).stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )

        completedDeliveries = repository.getOrdersByStatus("COMPLETED").stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )
        
        // Sync orders with polling
        viewModelScope.launch {
            while (kotlinx.coroutines.isActive) {
                repository.syncOrders()
                kotlinx.coroutines.delay(10000)
            }
        }
    }

    fun acceptDelivery(delivery: OrderEntity) {
        viewModelScope.launch {
            repository.acceptOrder(delivery.id)
            repository.syncOrders()
        }
    }

    fun loadOrderDetails(orderId: String) {
        if (_orderDetails.value.containsKey(orderId)) return

        viewModelScope.launch {
            repository.getOrderDetails(orderId)
                .onSuccess { detail ->
                    _orderDetails.value = _orderDetails.value + (orderId to detail)
                }
                .onFailure { error ->
                    _operationError.value = error.localizedMessage
                }
        }
    }

    fun startDelivery(orderId: String, onSuccess: (() -> Unit)? = null) {
        viewModelScope.launch {
            repository.startOrder(orderId)
                .onSuccess {
                    repository.syncOrders()
                    loadOrderDetails(orderId)
                    onSuccess?.invoke()
                }
                .onFailure { error ->
                    _operationError.value = error.localizedMessage
                }
        }
    }

    fun releaseDelivery(orderId: String, reason: String) {
        viewModelScope.launch {
            repository.releaseOrder(orderId, reason)
                .onSuccess {
                    repository.syncOrders()
                }
                .onFailure { error ->
                    _operationError.value = error.localizedMessage
                }
        }
    }

    fun rejectDelivery(orderId: String, reasonCode: String, reasonText: String? = null) {
        viewModelScope.launch {
            repository.rejectOrder(orderId, reasonCode, reasonText)
                .onSuccess {
                    repository.syncOrders()
                }
                .onFailure { error ->
                    _operationError.value = error.localizedMessage
                }
        }
    }
    
    fun finishDelivery(delivery: OrderEntity, onSuccess: () -> Unit = {}) {
        // Mantido para compatibilidade temporária com telas antigas.
        val detail = _orderDetails.value[delivery.id]
        val lastStop = detail?.stops?.lastOrNull() ?: return
        finishDelivery(orderId = delivery.id, stopId = lastStop.id, deliveryPin = null, onSuccess = onSuccess)
    }

    fun finishDelivery(
        orderId: String,
        stopId: String,
        deliveryPin: String? = null,
        onSuccess: () -> Unit = {}
    ) {
        viewModelScope.launch {
            repository.finishOrder(orderId, stopId, deliveryPin)
                .onSuccess {
                    repository.syncOrders()
                    _orderDetails.value = _orderDetails.value - orderId
                    onSuccess()
                }
                .onFailure { error ->
                    _operationError.value = error.localizedMessage
                }
        }
    }

    fun reportIncident(orderId: String?, stopId: String?, type: String, description: String, onSuccess: () -> Unit = {}) {
        viewModelScope.launch {
            repository.reportIncident(orderId, stopId, type, description)
                .onSuccess {
                    onSuccess()
                }
                .onFailure { error ->
                    _operationError.value = error.localizedMessage
                }
        }
    }

    fun clearOperationError() {
        _operationError.value = null
    }
}
