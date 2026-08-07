package com.nevesgo.app.presentation.escala

import com.nevesgo.app.ui.theme.*
sealed class DetalhesEscalaUiState {
    object Disponivel : DetalhesEscalaUiState()
    object Agendada : DetalhesEscalaUiState()
}
