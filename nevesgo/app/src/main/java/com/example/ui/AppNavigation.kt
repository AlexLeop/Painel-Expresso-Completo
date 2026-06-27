package com.example.ui

import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ListAlt
import androidx.compose.material.icons.filled.AttachMoney
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Button
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.example.MyApplication
import com.example.data.remote.dataStore
import com.example.ui.screens.ChatScreen
import com.example.ui.screens.ConfirmDeliveryScreen
import com.example.ui.screens.DeliveriesScreen
import com.example.ui.screens.DeliveryAcceptedScreen
import com.example.ui.screens.DeliveryFinishedScreen
import com.example.ui.screens.EarningsScreen
import com.example.ui.screens.HomeScreen
import com.example.ui.screens.JourneyDetailsScreen
import com.example.ui.screens.NotificationsScreen
import com.example.ui.screens.PaymentsScreen
import com.example.ui.screens.ProfileScreen
import com.example.ui.screens.ReportProblemScreen
import com.example.ui.screens.RouteNavigationScreen
import com.example.ui.screens.ScheduleDetailsScreen
import com.example.ui.screens.SchedulesScreen
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

private val jwtTokenKey = stringPreferencesKey("jwt_token")

private sealed class Route(val value: String) {
    data object Splash : Route("splash")
    data object Login : Route("login")
    data object Register : Route("register")
    data object Home : Route("home")
    data object Deliveries : Route("deliveries")
    data object Earnings : Route("earnings")
    data object Profile : Route("profile")
}

private sealed class MainTab(val route: String, val title: String, val icon: ImageVector) {
    data object Home : MainTab(Route.Home.value, "Home", Icons.Filled.Map)
    data object Deliveries : MainTab(Route.Deliveries.value, "Entregas", Icons.AutoMirrored.Filled.ListAlt)
    data object Earnings : MainTab(Route.Earnings.value, "Ganhos", Icons.Filled.AttachMoney)
    data object Profile : MainTab(Route.Profile.value, "Perfil", Icons.Filled.Person)
}

@Composable
fun NevesGoApp() {
    val navController = rememberNavController()
    val context = LocalContext.current
    val application = remember(context) { context.applicationContext as MyApplication }
    val apiService = remember(application) { application.container.driverApiService }
    val items = listOf(
        MainTab.Home,
        MainTab.Deliveries,
        MainTab.Earnings,
        MainTab.Profile
    )

    androidx.compose.runtime.DisposableEffect(context) {
        val receiver = object : android.content.BroadcastReceiver() {
            override fun onReceive(c: android.content.Context, intent: android.content.Intent) {
                if (intent.action == "com.example.ACTION_LOGOUT") {
                    com.example.data.local.SecureStorage.clearToken(context)
                    navController.navigate(Route.Login.value) {
                        popUpTo(0)
                        launchSingleTop = true
                    }
                }
            }
        }
        val filter = android.content.IntentFilter("com.example.ACTION_LOGOUT")
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            context.registerReceiver(receiver, filter, android.content.Context.RECEIVER_NOT_EXPORTED)
        } else {
            context.registerReceiver(receiver, filter)
        }
        onDispose {
            context.unregisterReceiver(receiver)
        }
    }

    Scaffold(
        bottomBar = {
            val navBackStackEntry by navController.currentBackStackEntryAsState()
            val currentRoute = navBackStackEntry?.destination?.route

            if (currentRoute in items.map { it.route }) {
                Box(
                    modifier = Modifier
                        .shadow(16.dp, RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
                        .clip(RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
                ) {
                    NavigationBar(
                        containerColor = MaterialTheme.colorScheme.surface,
                        tonalElevation = 0.dp
                    ) {
                        items.forEach { screen ->
                            NavigationBarItem(
                                icon = { Icon(screen.icon, contentDescription = screen.title) },
                                label = { Text(screen.title) },
                                selected = currentRoute == screen.route,
                                colors = NavigationBarItemDefaults.colors(
                                    selectedIconColor = MaterialTheme.colorScheme.onPrimary,
                                    selectedTextColor = MaterialTheme.colorScheme.primary,
                                    indicatorColor = MaterialTheme.colorScheme.primary,
                                    unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                                    unselectedTextColor = MaterialTheme.colorScheme.onSurfaceVariant
                                ),
                                onClick = {
                                    navController.navigate(screen.route) {
                                        popUpTo(navController.graph.findStartDestination().id) {
                                            saveState = true
                                        }
                                        launchSingleTop = true
                                        restoreState = true
                                    }
                                }
                            )
                        }
                    }
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Route.Splash.value,
            modifier = Modifier
                .padding(innerPadding)
                .background(MaterialTheme.colorScheme.background)
        ) {
            composable(Route.Splash.value) {
                com.example.ui.screens.SplashScreen(
                    onNavigateToLogin = {
                        navController.navigate(Route.Login.value) {
                            popUpTo(Route.Splash.value) { inclusive = true }
                        }
                    },
                    onNavigateToHome = {
                        navController.navigate(Route.Home.value) {
                            popUpTo(Route.Splash.value) { inclusive = true }
                        }
                    },
                    onValidateSession = { apiService.completeLoginBootstrap() }
                )
            }

            composable(Route.Login.value) {
                com.example.ui.screens.LoginScreen(
                    onNavigateToHome = {
                        navController.navigate(Route.Home.value) {
                            popUpTo(Route.Login.value) { inclusive = true }
                        }
                    },
                    onNavigateToRegister = {
                        navController.navigate(Route.Register.value)
                    },
                    onValidateSession = { apiService.completeLoginBootstrap() }
                )
            }

            composable(Route.Register.value) {
                com.example.ui.screens.RegisterScreen(
                    onNavigateBack = {
                        navController.popBackStack()
                    }
                )
            }

            composable(Route.Home.value) { HomeScreen(navController) }
            composable(Route.Deliveries.value) { DeliveriesScreen(navController) }
            composable(Route.Earnings.value) { EarningsScreen(navController) }
            composable(Route.Profile.value) { ProfileScreen(navController) }

            composable("corrida_aceita") {
                DeliveryAcceptedScreen(navController = navController, orderId = null)
            }
            composable("corrida_aceita/{orderId}") { backStackEntry ->
                DeliveryAcceptedScreen(
                    navController = navController,
                    orderId = backStackEntry.arguments?.getString("orderId")
                )
            }
            composable("navigation_screen") {
                RouteNavigationScreen(navController = navController, orderId = null)
            }
            composable("navigation_screen/{orderId}") { backStackEntry ->
                RouteNavigationScreen(
                    navController = navController,
                    orderId = backStackEntry.arguments?.getString("orderId")
                )
            }
            composable("confirmar_entrega") { ConfirmDeliveryScreen(navController, orderId = null) }
            composable("confirmar_entrega/{orderId}") { backStackEntry ->
                ConfirmDeliveryScreen(navController, orderId = backStackEntry.arguments?.getString("orderId"))
            }
            composable("entrega_finalizada") { DeliveryFinishedScreen(navController, fareCents = null) }
            composable("entrega_finalizada/{fareCents}") { backStackEntry ->
                DeliveryFinishedScreen(
                    navController = navController,
                    fareCents = backStackEntry.arguments?.getString("fareCents")?.toIntOrNull()
                )
            }
            composable("reportar_problema") { ReportProblemScreen(navController, orderId = null, stopId = null) }
            composable("reportar_problema/{orderId}/{stopId}") { backStackEntry ->
                ReportProblemScreen(
                    navController,
                    orderId = backStackEntry.arguments?.getString("orderId"),
                    stopId = backStackEntry.arguments?.getString("stopId")
                )
            }
            composable("escalas") { SchedulesScreen(navController) }
            composable("escala_detalhes") {
                ScheduleDetailsScreen(
                    navController = navController,
                    kind = null,
                    date = null,
                    status = null,
                    storeId = null,
                    storeName = null,
                    turnoId = null,
                    turnoName = null
                )
            }
            composable("escala_detalhes/{kind}/{date}/{status}/{storeId}/{storeName}/{turnoId}/{turnoName}") { backStackEntry ->
                ScheduleDetailsScreen(
                    navController = navController,
                    kind = backStackEntry.arguments?.getString("kind")?.let(Uri::decode),
                    date = backStackEntry.arguments?.getString("date")?.let(Uri::decode),
                    status = backStackEntry.arguments?.getString("status")?.let(Uri::decode),
                    storeId = backStackEntry.arguments?.getString("storeId")?.let(Uri::decode),
                    storeName = backStackEntry.arguments?.getString("storeName")?.let(Uri::decode),
                    turnoId = backStackEntry.arguments?.getString("turnoId")?.let(Uri::decode),
                    turnoName = backStackEntry.arguments?.getString("turnoName")?.let(Uri::decode)
                )
            }
            composable("pagamentos") { PaymentsScreen(navController) }
            composable("jornada_detalhes") { JourneyDetailsScreen(navController) }
            composable("notificacoes") { NotificationsScreen(navController) }
            composable("chat") { ChatScreen(navController, threadId = null) }
            composable("chat/{threadId}") { backStackEntry ->
                ChatScreen(
                    navController = navController,
                    threadId = backStackEntry.arguments?.getString("threadId")
                )
            }
        }
    }
}

