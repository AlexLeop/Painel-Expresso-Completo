package com.nevesgo.app.presentation.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nevesgo.app.data.local.TokenManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val tokenManager: TokenManager
) : ViewModel() {

    private val _navigationEvent = MutableSharedFlow<AuthNavigationEvent>()
    val navigationEvent: SharedFlow<AuthNavigationEvent> = _navigationEvent

    fun checkAuthStatus() {
        viewModelScope.launch {
            // Pequeno delay para garantir que a splash seja visível
            delay(1500)
            val token = tokenManager.getToken()
            if (token != null) {
                _navigationEvent.emit(AuthNavigationEvent.NavigateToMain)
            } else {
                _navigationEvent.emit(AuthNavigationEvent.NavigateToLogin)
            }
        }
    }

    fun login() {
        viewModelScope.launch {
            // Simulação de login salvando um token fake
            tokenManager.saveToken("fake-jwt-token")
            _navigationEvent.emit(AuthNavigationEvent.NavigateToMain)
        }
    }
}

sealed class AuthNavigationEvent {
    object NavigateToLogin : AuthNavigationEvent()
    object NavigateToMain : AuthNavigationEvent()
}
