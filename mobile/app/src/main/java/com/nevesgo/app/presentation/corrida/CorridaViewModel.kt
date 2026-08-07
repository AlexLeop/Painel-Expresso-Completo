package com.nevesgo.app.presentation.corrida

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nevesgo.app.domain.repository.CorridaRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

@HiltViewModel
class CorridaViewModel @Inject constructor(
    private val repository: CorridaRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<CorridaUiState>(CorridaUiState.Loading)
    val uiState: StateFlow<CorridaUiState> = _uiState.asStateFlow()

    init {
        carregarOfertas()
    }

    fun carregarOfertas() {
        viewModelScope.launch {
            _uiState.value = CorridaUiState.Loading
            try {
                val cockpitResp = repository.getCockpit()
                val ordersResp = repository.getOrders()

                if (cockpitResp.isSuccessful && cockpitResp.body() != null) {
                    val cockpitData = cockpitResp.body()!!
                    val ordersData = if (ordersResp.isSuccessful) ordersResp.body() ?: emptyList() else emptyList()
                    _uiState.value = CorridaUiState.Cockpit(cockpitData, ordersData)
                } else {
                    _uiState.value = CorridaUiState.Error("Erro ao carregar dados do Cockpit")
                }
            } catch (e: Exception) {
                _uiState.value = CorridaUiState.Error("Erro de conexão: ${e.message}")
            }
        }
    }

    fun aceitarPedido(orderId: String) {
        viewModelScope.launch {
            try {
                val resp = repository.acceptOrder(orderId)
                if (resp.isSuccessful) {
                    carregarOfertas()
                } else {
                    // Tratar erro
                }
            } catch (e: Exception) {
                // Tratar erro
            }
        }
    }

    fun recusarPedido(orderId: String, motivo: String) {
        viewModelScope.launch {
            try {
                repository.rejectOrder(orderId, motivo)
                carregarOfertas()
            } catch (e: Exception) {
                // Tratar erro
            }
        }
    }

    fun iniciarEntrega(orderId: String) {
        viewModelScope.launch {
            try {
                repository.startOrder(orderId)
                carregarOfertas()
            } catch (e: Exception) {
                // Tratar erro
            }
        }
    }

    fun confirmarEntregaComOtp(stopId: String, otpCode: String) {
        viewModelScope.launch {
            try {
                repository.submitDeliveryProof(stopId, otpCode)
                carregarOfertas() 
            } catch (e: Exception) {
                // Tratar erro
            }
        }
    }
    
    fun completarLoteDeEntregas() {
        viewModelScope.launch {
            try {
                repository.completeBatch()
                carregarOfertas() 
            } catch (e: Exception) {
                // Tratar erro
            }
        }
    }
}
