package com.nevesgo.app.presentation.financeiro

import com.nevesgo.app.ui.theme.*
sealed class SaqueUiState {
    object Formulario : SaqueUiState()
    object Sucesso : SaqueUiState()
}
