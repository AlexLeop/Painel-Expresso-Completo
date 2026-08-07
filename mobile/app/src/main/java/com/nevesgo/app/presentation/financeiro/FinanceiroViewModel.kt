package com.nevesgo.app.presentation.financeiro

import com.nevesgo.app.ui.theme.*
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nevesgo.app.domain.repository.FinanceiroRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

@HiltViewModel
class FinanceiroViewModel @Inject constructor(
    private val repository: FinanceiroRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<SaqueUiState>(SaqueUiState.Formulario)
    val uiState: StateFlow<SaqueUiState> = _uiState.asStateFlow()

    fun carregarCarteira() {
        viewModelScope.launch {
            try {
                repository.getWalletBalance()
                repository.getTransactions()
            } catch (e: Exception) {
                // TODO: Tratar erro de rede
            }
        }
    }

    fun solicitarSaque() {
        viewModelScope.launch {
            try {
                repository.withdrawWallet()
                _uiState.value = SaqueUiState.Sucesso
            } catch (e: Exception) {
                _uiState.value = SaqueUiState.Formulario
                // TODO: Notificar erro ao usuário
            }
        }
    }
    
    fun resetarSaque() {
        _uiState.value = SaqueUiState.Formulario
    }
}
