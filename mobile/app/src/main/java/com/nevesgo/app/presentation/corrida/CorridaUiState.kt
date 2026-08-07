package com.nevesgo.app.presentation.corrida

import com.nevesgo.app.domain.model.DriverCockpitResponse
import com.nevesgo.app.domain.model.OrderResponse

sealed class CorridaUiState {
    object Loading : CorridaUiState()
    data class Cockpit(
        val cockpitData: DriverCockpitResponse,
        val orders: List<OrderResponse> = emptyList()
    ) : CorridaUiState()
    data class Error(val message: String) : CorridaUiState()
}
