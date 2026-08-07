package com.nevesgo.app.presentation.escala

import com.nevesgo.app.ui.theme.*
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nevesgo.app.domain.repository.EscalaRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

@HiltViewModel
class EscalaViewModel @Inject constructor(
    private val repository: EscalaRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<DetalhesEscalaUiState>(DetalhesEscalaUiState.Disponivel)
    val uiState: StateFlow<DetalhesEscalaUiState> = _uiState.asStateFlow()

    fun carregarCalendario() {
        viewModelScope.launch {
            try {
                repository.getCalendarShifts()
            } catch (e: Exception) {
                // TODO: Notificar falha na obtenção do calendário
            }
        }
    }

    fun candidatarSeAVaga() {
        viewModelScope.launch {
            try {
                repository.reserveShift()
                _uiState.value = DetalhesEscalaUiState.Agendada
            } catch (e: Exception) {
                // TODO: Notificar falha ao agendar
            }
        }
    }

    fun desistirDaVaga() {
        viewModelScope.launch {
            try {
                repository.checkOutShift()
                _uiState.value = DetalhesEscalaUiState.Disponivel
            } catch (e: Exception) {
                // TODO: Notificar erro no check-out
            }
        }
    }
}
