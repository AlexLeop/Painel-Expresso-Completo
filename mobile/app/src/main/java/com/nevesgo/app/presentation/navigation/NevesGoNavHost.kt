package com.nevesgo.app.presentation.navigation

import com.nevesgo.app.ui.theme.*
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController

// Importações dos módulos refatorados
import com.nevesgo.app.presentation.corrida.CorridaScreen
import com.nevesgo.app.presentation.corrida.CorridaViewModel
import com.nevesgo.app.presentation.entregas.MinhasEntregasScreen
import com.nevesgo.app.presentation.financeiro.FinanceiroViewModel
import com.nevesgo.app.presentation.financeiro.SolicitarSaqueScreen
import com.nevesgo.app.presentation.escala.DetalhesEscalaScreen
import com.nevesgo.app.presentation.escala.EscalaAbasScreen
import com.nevesgo.app.presentation.escala.EscalaViewModel
import com.nevesgo.app.ui.theme.NevesGoBottomNav

/**
 * Definição centralizada de todas as rotas do aplicativo.
 */
object Routes {
    // Auth
    const val SPLASH = "splash"
    const val LOGIN = "login"

    // Corrida
    const val CORRIDA = "corrida_screen"
    const val CONFIRMAR_CODIGO = "confirmar_codigo"
    const val PROXIMO_PASSO = "proximo_passo"
    const val CORRIDA_FINALIZADA = "corrida_finalizada"

    // Entregas
    const val MINHAS_ENTREGAS = "minhas_entregas"
    const val DETALHES_AGENDAMENTO = "detalhes_agendamento/{id}"

    // Financeiro
    const val CARTEIRA = "carteira"
    const val SOLICITAR_SAQUE = "solicitar_saque"

    // Escala
    const val ESCALA_ABAS = "escala_abas"
    const val DETALHES_ESCALA = "detalhes_escala/{id}"

    // Perfil
    const val PERFIL = "perfil"
    const val DADOS_PESSOAIS = "dados_pessoais"
    const val SEGURANCA = "seguranca"
}

@Composable
fun NevesGoApp() {
    val navController = rememberNavController()
    
    // Escuta a pilha de navegação para descobrir a rota atual
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route
    
    // Lógica de visibilidade: BottomBar SÓ aparece nestas rotas principais
    val showBottomBar = currentRoute in listOf(
        Routes.CORRIDA,
        Routes.MINHAS_ENTREGAS,
        Routes.CARTEIRA,
        Routes.ESCALA_ABAS,
        Routes.PERFIL
    )

    // Lógica de seleção ativa na BottomBar
    val activeTab = when (currentRoute) {
        Routes.CORRIDA -> "inicio"
        Routes.MINHAS_ENTREGAS -> "entregas"
        Routes.CARTEIRA -> "carteira"
        Routes.ESCALA_ABAS -> "escala"
        Routes.PERFIL -> "perfil"
        else -> "inicio"
    }

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                NevesGoBottomNav(activeTab = activeTab)
            }
        }
    ) { innerPadding ->
        NevesGoNavHost(
            navController = navController,
            modifier = Modifier.padding(innerPadding)
        )
    }
}

@Composable
fun NevesGoNavHost(navController: NavHostController, modifier: Modifier = Modifier) {
    NavHost(
        navController = navController,
        startDestination = Routes.SPLASH,
        modifier = modifier
    ) {
        // ==========================================
        // MÓDULO AUTH
        // ==========================================
        composable(Routes.SPLASH) {
            com.nevesgo.app.presentation.auth.SplashScreen(
                onNavigateToLogin = {
                    navController.navigate(Routes.LOGIN) {
                        popUpTo(Routes.SPLASH) { inclusive = true }
                    }
                },
                onNavigateToMain = {
                    navController.navigate(Routes.CORRIDA) {
                        popUpTo(Routes.SPLASH) { inclusive = true }
                    }
                }
            )
        }
        composable(Routes.LOGIN) {
            com.nevesgo.app.presentation.auth.LoginScreen(
                onLoginSuccess = {
                    navController.navigate(Routes.CORRIDA) {
                        popUpTo(Routes.LOGIN) { inclusive = true }
                    }
                }
            )
        }

        // ==========================================
        // MÓDULO CORRIDA
        // ==========================================
        composable(Routes.CORRIDA) {
            val viewModel: CorridaViewModel = hiltViewModel()
            // Na implementação real, passamos o viewModel para a tela via parâmetro
            // Ex: CorridaScreen(viewModel = viewModel, navController = navController)
            CorridaScreen()
        }
        composable(Routes.CONFIRMAR_CODIGO) {
            val viewModel: CorridaViewModel = hiltViewModel()
            // Placeholder: Tela de confirmação OTP embutida
        }
        composable(Routes.PROXIMO_PASSO) {
            val viewModel: CorridaViewModel = hiltViewModel()
            // Placeholder: Múltiplos pedidos (ir para próxima rota)
        }
        composable(Routes.CORRIDA_FINALIZADA) {
            val viewModel: CorridaViewModel = hiltViewModel()
            // Placeholder: Tela final de feedback
        }

        // ==========================================
        // MÓDULO ENTREGAS
        // ==========================================
        composable(Routes.MINHAS_ENTREGAS) {
            MinhasEntregasScreen()
        }
        composable(Routes.DETALHES_AGENDAMENTO) { backStackEntry ->
            val id = backStackEntry.arguments?.getString("id")
            // Placeholder: DetalhesAgendamentoScreen(id)
        }

        // ==========================================
        // MÓDULO FINANCEIRO
        // ==========================================
        composable(Routes.CARTEIRA) {
            val viewModel: FinanceiroViewModel = hiltViewModel()
            // Placeholder: CarteiraScreen(viewModel)
        }
        composable(Routes.SOLICITAR_SAQUE) {
            val viewModel: FinanceiroViewModel = hiltViewModel()
            SolicitarSaqueScreen()
            // Na implementação real: SolicitarSaqueScreen(viewModel = viewModel)
        }

        // ==========================================
        // MÓDULO ESCALA
        // ==========================================
        composable(Routes.ESCALA_ABAS) {
            val viewModel: EscalaViewModel = hiltViewModel()
            EscalaAbasScreen()
        }
        composable(Routes.DETALHES_ESCALA) { backStackEntry ->
            val id = backStackEntry.arguments?.getString("id")
            val viewModel: EscalaViewModel = hiltViewModel()
            DetalhesEscalaScreen()
        }

        // ==========================================
        // MÓDULO PERFIL
        // ==========================================
        composable(Routes.PERFIL) {
            // Placeholder
        }
        composable(Routes.DADOS_PESSOAIS) {
            // Placeholder
        }
        composable(Routes.SEGURANCA) {
            // Placeholder
        }
    }
}
