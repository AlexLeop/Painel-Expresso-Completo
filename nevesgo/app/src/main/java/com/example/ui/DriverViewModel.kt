package com.example.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.MyApplication
import com.example.domain.models.CockpitResponse
import com.example.domain.repository.CockpitRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed class CockpitUiState {
    object Loading : CockpitUiState()
    data class Success(val cockpit: CockpitResponse) : CockpitUiState()
    data class Error(val message: String) : CockpitUiState()
}

class DriverViewModel(application: Application) : AndroidViewModel(application) {
    private val repository: CockpitRepository = (application as MyApplication).container.cockpitRepository

    private val _uiState = MutableStateFlow<CockpitUiState>(CockpitUiState.Loading)
    val uiState: StateFlow<CockpitUiState> = _uiState
    private val _statusUpdateInFlight = MutableStateFlow(false)
    val statusUpdateInFlight = _statusUpdateInFlight.asStateFlow()

    init {
        loadCockpit()
    }

    fun loadCockpit() {
        viewModelScope.launch {
            _uiState.value = CockpitUiState.Loading
            
            val result = repository.getCockpitData()
            
            result.onSuccess { cockpit ->
                _uiState.value = CockpitUiState.Success(cockpit)
                
                // Garante que o tracking persista se a jornada/online estiver ativa
                val isOnline = cockpit.driver.online == true
                val hasActiveShift = cockpit.shift?.sessionId != null
                if (isOnline || hasActiveShift) {
                    com.example.services.TrackingService.start(getApplication())
                } else {
                    com.example.services.TrackingService.stop(getApplication())
                }
            }.onFailure { error ->
                _uiState.value = CockpitUiState.Error(error.localizedMessage ?: "Falha ao carregar dados do cockpit.")
            }
        }
    }

    fun setAvailability(isOnline: Boolean) {
        viewModelScope.launch {
            _statusUpdateInFlight.value = true
            val newStatus = if (isOnline) "ONLINE" else "OFFLINE"
            repository.setDriverStatus(status = newStatus).onSuccess {
                loadCockpit()
            }.onFailure { error ->
                _uiState.value = CockpitUiState.Error(error.localizedMessage ?: "Falha ao atualizar disponibilidade.")
            }
            _statusUpdateInFlight.value = false
        }
    }
}
