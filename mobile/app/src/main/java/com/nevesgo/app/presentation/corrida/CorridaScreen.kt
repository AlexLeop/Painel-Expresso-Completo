package com.nevesgo.app.presentation.corrida

import androidx.compose.animation.core.*
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import com.nevesgo.app.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import androidx.hilt.navigation.compose.hiltViewModel

import com.nevesgo.app.domain.model.DriverCockpitResponse

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CorridaScreen(viewModel: CorridaViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsState()
    var isOnline by remember { mutableStateOf(true) }
    var isStarting by remember { mutableStateOf(false) }
    var isConfirming by remember { mutableStateOf(false) }
    var isFinished by remember { mutableStateOf(false) }
    val coroutineScope = rememberCoroutineScope()

    // Derivar a fase visual
    val phase = when (val state = uiState) {
        is CorridaUiState.Cockpit -> {
            val cockpit = state.cockpitData
            when {
                cockpit.active_order != null -> {
                    if (cockpit.active_order.next_stop_type == "DELIVERY") "EmRota" else "Aceito"
                }
                !cockpit.active_orders.isNullOrEmpty() -> "Proposta"
                else -> "Idle"
            }
        }
        else -> "Loading"
    }

    val driverName = (uiState as? CorridaUiState.Cockpit)?.cockpitData?.driver?.name ?: "Carregando..."
    val driverStatus = (uiState as? CorridaUiState.Cockpit)?.cockpitData?.driver?.status ?: "OFFLINE"
    isOnline = driverStatus == "ONLINE"

    Scaffold(
        bottomBar = { NevesGoBottomNav(activeTab = if (phase == "Proposta") "inicio" else "entregas", modifier = Modifier.navigationBarsPadding()) },
        modifier = Modifier.fillMaxSize().navigationBarsPadding()
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(MaterialTheme.colorScheme.surface)
        ) {
                // Background Map (Placeholder)
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(MaterialTheme.colorScheme.surfaceContainerLowest)
                )

                // Overlays based on state
                if (phase == "Aceito") {
                    Column(
                        modifier = Modifier
                            .align(Alignment.TopEnd)
                            .padding(top = 100.dp, end = 16.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Surface(
                            shape = NevesGoShapes.medium,
                            color = MaterialTheme.colorScheme.surfaceContainerLowest.copy(alpha = 0.85f),
                            shadowElevation = 8.dp,
                            onClick = { /* TODO */ },
                            modifier = Modifier.size(48.dp)
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Icon(Icons.Outlined.MyLocation, contentDescription = "My location", tint = MaterialTheme.colorScheme.primary)
                            }
                        }
                        Surface(
                            shape = NevesGoShapes.medium,
                            color = MaterialTheme.colorScheme.surfaceContainerLowest.copy(alpha = 0.85f),
                            shadowElevation = 8.dp,
                            onClick = { /* TODO */ },
                            modifier = Modifier.size(48.dp)
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Icon(Icons.Outlined.Layers, contentDescription = "Layers", tint = MaterialTheme.colorScheme.primary)
                            }
                        }
                    }
                } else if (phase == "Proposta") {
                    // Map Controls
                    MapControls(
                        modifier = Modifier
                            .align(Alignment.BottomEnd)
                            .padding(end = 16.dp, bottom = 440.dp)
                    )
                }

                // Floating Header Card
                FloatingHeaderCard(
                    driverName = driverName,
                    isOnline = isOnline,
                    onOnlineChange = { isOnline = it },
                    modifier = Modifier
                        .align(Alignment.TopCenter)
                        .padding(16.dp)
                )

                // Wallet FAB
            val walletBottomPadding = when(phase) {
                "Proposta" -> 380.dp
                "Aceito" -> 360.dp
                "EmRota" -> 340.dp
                else -> 100.dp
            }
            WalletFab(
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(end = 16.dp, bottom = walletBottomPadding)
            )

            // Fixed Bottom Content
            Box(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(16.dp)
            ) {
                when (phase) {
                    "Proposta" -> {
                        val activeOrders = (uiState as? CorridaUiState.Cockpit)?.cockpitData?.active_orders
                        val orderId = activeOrders?.firstOrNull()?.order_id ?: "123"
                        OrdersBottomArea(
                            onAcceptClick = { viewModel.aceitarPedido(orderId) },
                            onRejectClick = { viewModel.recusarPedido(orderId, "Tempo Esgotado") }
                        )
                    }
                    "Aceito" -> {
                        val activeOrder = (uiState as? CorridaUiState.Cockpit)?.cockpitData?.active_order
                        val orderId = activeOrder?.order_id ?: "123"
                        DeliveryInfoCard(
                            isStarting = isStarting,
                            onStartClick = {
                                coroutineScope.launch {
                                    isStarting = true
                                    delay(1200)
                                    isStarting = false
                                    viewModel.iniciarEntrega(orderId)
                                }
                            }
                        )
                    }
                    "EmRota" -> {
                        val activeOrder = (uiState as? CorridaUiState.Cockpit)?.cockpitData?.active_order
                        val stopId = activeOrder?.next_stop_id ?: "456"
                        DeliveryCompletionCard(
                            isConfirming = isConfirming,
                            isFinished = isFinished,
                            onConfirmClick = { otp ->
                                if (otp == "1234") {
                                    if (!isFinished) {
                                        coroutineScope.launch {
                                            isConfirming = true
                                            delay(1200)
                                            isConfirming = false
                                            isFinished = true
                                            viewModel.confirmarEntregaComOtp(stopId, otp)
                                        }
                                    }
                                    true
                                } else {
                                    false
                                }
                            }
                        )
                    }
                }
            }
        }
    }
}


@Composable
private fun FloatingHeaderCard(driverName: String, isOnline: Boolean, onOnlineChange: (Boolean) -> Unit, modifier: Modifier = Modifier) {
    Surface(
        shape = NevesGoShapes.large,
        color = MaterialTheme.colorScheme.surfaceContainerLow,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.2f)),
        shadowElevation = 8.dp,
        modifier = modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp, vertical = 16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Box(
                    modifier = Modifier
                        .size(40.dp)
                        .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.1f), CircleShape)
                        .border(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.05f), CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(imageVector = Icons.Outlined.AccountCircle, contentDescription = "Perfil", tint = MaterialTheme.colorScheme.primary)
                }
                
                Column {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(
                            text = driverName,
                            style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold),
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Surface(
                            shape = PillShape,
                            color = TertiaryFixed,
                            contentColor = OnTertiaryFixed
                        ) {
                            Text(
                                text = "Premium",
                                style = MaterialTheme.typography.labelSmall,
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                            )
                        }
                    }
                    Text(
                        text = if (isOnline) "ONLINE E DISPONÍVEL" else "OFFLINE",
                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, letterSpacing = 0.05.em),
                        color = MaterialTheme.colorScheme.secondary
                    )
                }
            }
            
            Switch(
                checked = isOnline,
                onCheckedChange = onOnlineChange,
                colors = SwitchDefaults.colors(
                    checkedThumbColor = MaterialTheme.colorScheme.onPrimary,
                    checkedTrackColor = MaterialTheme.colorScheme.primary,
                    uncheckedThumbColor = MaterialTheme.colorScheme.surface,
                    uncheckedTrackColor = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f)
                )
            )
        }
    }
}


@Composable
private fun MapControls(modifier: Modifier = Modifier) {
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Surface(
            shape = NevesGoShapes.medium,
            color = MaterialTheme.colorScheme.surfaceContainerLowest.copy(alpha = 0.9f),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f)),
            shadowElevation = 8.dp
        ) {
            Column {
                IconButton(onClick = { /* TODO */ }, modifier = Modifier.size(44.dp)) {
                    Icon(Icons.Outlined.Add, contentDescription = "Zoom in")
                }
                Box(
                    modifier = Modifier
                        .width(24.dp)
                        .height(1.dp)
                        .background(MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.2f))
                        .align(Alignment.CenterHorizontally)
                )
                IconButton(onClick = { /* TODO */ }, modifier = Modifier.size(44.dp)) {
                    Icon(Icons.Outlined.Remove, contentDescription = "Zoom out")
                }
            }
        }
        
        Surface(
            shape = NevesGoShapes.medium,
            color = MaterialTheme.colorScheme.surfaceContainerLowest.copy(alpha = 0.9f),
            shadowElevation = 8.dp,
            onClick = { /* TODO */ },
            modifier = Modifier.size(44.dp)
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(Icons.Outlined.MyLocation, contentDescription = "My location")
            }
        }
    }
}


@Composable
private fun WalletFab(modifier: Modifier = Modifier) {
    Surface(
        shape = CircleShape,
        color = MaterialTheme.colorScheme.primary,
        contentColor = MaterialTheme.colorScheme.onPrimary,
        shadowElevation = 12.dp,
        onClick = { /* TODO */ },
        modifier = modifier.size(56.dp)
    ) {
        Box(contentAlignment = Alignment.Center) {
            Icon(Icons.Outlined.AccountBalanceWallet, contentDescription = "Carteira", modifier = Modifier.size(28.dp))
        }
    }
}


@Composable
private fun OrdersBottomArea(onAcceptClick: () -> Unit, onRejectClick: () -> Unit, modifier: Modifier = Modifier) {
    var timeLeft by remember { mutableStateOf(30) }
    
    LaunchedEffect(Unit) {
        while (timeLeft > 0) {
            delay(1000L)
            timeLeft--
        }
        if (timeLeft == 0) onRejectClick()
    }

    Surface(
        shape = NevesGoShapes.large,
        color = MaterialTheme.colorScheme.surfaceContainerLowest,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f)),
        shadowElevation = 16.dp,
        modifier = modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(24.dp)) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Surface(
                        shape = PillShape,
                        color = MaterialTheme.colorScheme.primary,
                        contentColor = MaterialTheme.colorScheme.onPrimary
                    ) {
                        Text(
                            text = "2 PEDIDOS",
                            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, letterSpacing = 0.05.em),
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
                        )
                    }
                    Text(
                        text = "#ORD-8829",
                        style = DataMono.copy(fontSize = 10.sp),
                        color = MaterialTheme.colorScheme.outline
                    )
                }
                
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
                    val alpha by infiniteTransition.animateFloat(initialValue = 0.2f, targetValue = 1f, animationSpec = infiniteRepeatable(animation = tween(500, easing = LinearEasing), repeatMode = RepeatMode.Reverse), label = "alpha")
                    Icon(Icons.Outlined.Timer, contentDescription = "Timer", tint = MaterialTheme.colorScheme.error.copy(alpha = alpha), modifier = Modifier.size(16.dp))
                    Text(
                        text = "${timeLeft}s",
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                        color = MaterialTheme.colorScheme.error.copy(alpha = alpha)
                    )
                }
            }
            
            // Timer Bar
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(PillShape)
                    .background(MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.2f))
                    .padding(bottom = 16.dp)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth(timeLeft / 30f)
                        .fillMaxHeight()
                        .background(MaterialTheme.colorScheme.error)
                )
            }
            Spacer(modifier = Modifier.height(16.dp))

            // Primary Metrics
            Surface(
                shape = NevesGoShapes.medium,
                color = MaterialTheme.colorScheme.surfaceContainerLow,
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f)),
                modifier = Modifier.fillMaxWidth().padding(bottom = 24.dp)
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text("GANHOS ESTIMADOS", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, letterSpacing = 0.05.em, fontSize = 10.sp), color = MaterialTheme.colorScheme.outline)
                        Text("R$ 28,90", style = MaterialTheme.typography.headlineLarge, color = MaterialTheme.colorScheme.onSurface)
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text("6.8 km • 25 min", style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.primary)
                        Text("TOTAL ESTIMADO", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, letterSpacing = 0.05.em, fontSize = 10.sp), color = MaterialTheme.colorScheme.outline)
                    }
                }
            }

            // Orders Area (Scrollable)
            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 220.dp)
                    .padding(bottom = 24.dp),
                verticalArrangement = Arrangement.spacedBy(24.dp)
            ) {
                item { OrderItem("Ana Beatriz S. • #ORD-8829", "4.2 km • 17 min", "Restaurante Sabor Real", "Rua das Flores, 123 - Apt 42") }
                item { HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.1f)) }
                item { OrderItem("Marcos Oliveira • #ORD-8830", "2.6 km • 11 min", "Burger House Premium", "Al. Santos, 450 - Bloco B") }
            }
            
            // Controls
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(
                    onClick = onRejectClick,
                    modifier = Modifier.weight(1f).height(56.dp),
                    shape = NevesGoShapes.medium,
                    colors = ButtonDefaults.buttonColors(containerColor = Color.Transparent, contentColor = MaterialTheme.colorScheme.onSurface),
                    border = BorderStroke(2.dp, MaterialTheme.colorScheme.outlineVariant)
                ) {
                    Text("Recusar", style = MaterialTheme.typography.labelLarge)
                }
                
                Button(
                    onClick = onAcceptClick,
                    modifier = Modifier.weight(2.5f).height(56.dp),
                    shape = NevesGoShapes.medium,
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary, contentColor = MaterialTheme.colorScheme.onPrimary),
                    elevation = ButtonDefaults.buttonElevation(defaultElevation = 4.dp)
                ) {
                    Text("Aceitar Pedidos", style = MaterialTheme.typography.labelLarge)
                }
            }
        }
    }
}


@Composable
private fun DeliveryInfoCard(isStarting: Boolean, onStartClick: () -> Unit, modifier: Modifier = Modifier) {
    Surface(
        shape = NevesGoShapes.medium,
        color = MaterialTheme.colorScheme.surfaceContainerLowest,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f)),
        shadowElevation = 8.dp,
        modifier = modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(24.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(bottom = 24.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top
            ) {
                Column {
                    Text("Entregas Atuais", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.onSurface, modifier = Modifier.padding(bottom = 4.dp))
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Icon(Icons.Outlined.LocalShipping, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(16.dp))
                        Text("2 Pedidos Pendentes", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text("R$ 18,50", style = MaterialTheme.typography.headlineMedium.copy(fontSize = 20.sp), color = MaterialTheme.colorScheme.secondary)
                    Text("Ganhos Estimados", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.8f))
                }
            }

            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))

            Column(modifier = Modifier.padding(top = 24.dp, bottom = 32.dp), verticalArrangement = Arrangement.spacedBy(24.dp)) {
                // Coleta
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(Icons.Outlined.TripOrigin, contentDescription = null, tint = MaterialTheme.colorScheme.secondary, modifier = Modifier.size(20.dp))
                        Box(modifier = Modifier.width(2.dp).height(48.dp).padding(vertical = 4.dp).background(MaterialTheme.colorScheme.outlineVariant))
                    }
                    Column {
                        Text("COLETA", style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.05.em), color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("Central Gourmet - Unidade Centro", style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurface)
                        Text("Rua Augusta, 1200", style = MaterialTheme.typography.bodyMedium.copy(fontSize = 14.sp), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }

                // Pedido 1
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(Icons.Outlined.LocationOn, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                        Box(modifier = Modifier.width(2.dp).height(48.dp).padding(vertical = 4.dp).background(MaterialTheme.colorScheme.outlineVariant))
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                        Column {
                            Text("PEDIDO #F8921", style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.05.em), color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("Ana Silva", style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurface)
                            Text("Rua Augusta, 1500", style = MaterialTheme.typography.bodyMedium.copy(fontSize = 14.sp), color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text("2.5 km", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, fontSize = 12.sp), color = MaterialTheme.colorScheme.primary)
                            Text("12 min", style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp), color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }

                // Pedido 2
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(Icons.Outlined.LocationOn, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                        Column {
                            Text("PEDIDO #G4432", style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.05.em), color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("Marcos Souza", style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurface)
                            Text("Rua Peixoto Gomide, 800", style = MaterialTheme.typography.bodyMedium.copy(fontSize = 14.sp), color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text("3.8 km", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, fontSize = 12.sp), color = MaterialTheme.colorScheme.primary)
                            Text("18 min", style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp), color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }

            // Start Button
            Button(
                onClick = onStartClick,
                enabled = !isStarting,
                modifier = Modifier.fillMaxWidth().height(56.dp),
                shape = NevesGoShapes.medium,
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.secondary,
                    contentColor = MaterialTheme.colorScheme.onSecondary,
                    disabledContainerColor = MaterialTheme.colorScheme.secondary.copy(alpha = 0.8f),
                    disabledContentColor = MaterialTheme.colorScheme.onSecondary
                ),
                elevation = ButtonDefaults.buttonElevation(defaultElevation = 4.dp)
            ) {
                if (isStarting) {
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                        CircularProgressIndicator(color = MaterialTheme.colorScheme.onSecondary, strokeWidth = 2.dp, modifier = Modifier.size(20.dp))
                        Text("Iniciando...", style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold))
                    }
                } else {
                    Row(modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Text("Iniciar Entrega", style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            val infiniteTransition = rememberInfiniteTransition(label = "pulse")
                            val alpha by infiniteTransition.animateFloat(initialValue = 0.2f, targetValue = 1f, animationSpec = infiniteRepeatable(animation = tween(1000, easing = LinearEasing), repeatMode = RepeatMode.Reverse), label = "alpha")
                            Icon(Icons.Outlined.KeyboardArrowRight, contentDescription = null, modifier = Modifier.alpha(alpha))
                            Icon(Icons.Outlined.KeyboardArrowRight, contentDescription = null)
                        }
                    }
                }
            }
        }
    }
}


@Composable
private fun DeliveryCompletionCard(isConfirming: Boolean, isFinished: Boolean, onConfirmClick: (String) -> Boolean, modifier: Modifier = Modifier) {
    var otpCode by remember { mutableStateOf("") }
    var isError by remember { mutableStateOf(false) }
    
    val shakeOffset = remember { Animatable(0f) }
    
    LaunchedEffect(isError) {
        if (isError) {
            for (i in 0..5) {
                shakeOffset.animateTo(10f, animationSpec = tween(50))
                shakeOffset.animateTo(-10f, animationSpec = tween(50))
            }
            shakeOffset.animateTo(0f, animationSpec = tween(50))
            isError = false
        }
    }

    Surface(
        shape = NevesGoShapes.medium,
        color = MaterialTheme.colorScheme.surfaceContainerLowest,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f)),
        shadowElevation = 8.dp,
        modifier = modifier.fillMaxWidth().offset(x = shakeOffset.value.dp)
    ) {
        Column {
            Row(
                modifier = Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.surfaceContainerLow).padding(horizontal = 24.dp, vertical = 16.dp).border(BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f))),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text("Finalizar Entrega", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary)
                    Text("Ganhos Estimados", style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.05.em), color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Text("R$ 18,50", style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.secondary)
            }

            Row(modifier = Modifier.padding(24.dp), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(top = 4.dp)) {
                    Box(modifier = Modifier.size(8.dp).background(MaterialTheme.colorScheme.outline, CircleShape))
                    Box(modifier = Modifier.width(2.dp).height(32.dp).background(MaterialTheme.colorScheme.outlineVariant))
                    Box(modifier = Modifier.size(24.dp).background(MaterialTheme.colorScheme.secondary, CircleShape).border(4.dp, MaterialTheme.colorScheme.secondaryContainer, CircleShape), contentAlignment = Alignment.Center) {
                        Icon(Icons.Outlined.LocationOn, contentDescription = null, tint = MaterialTheme.colorScheme.onSecondary, modifier = Modifier.size(14.dp))
                    }
                }
                Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    Column(modifier = Modifier.alpha(0.5f)) {
                        Text("Ponto de Coleta", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("Restaurante Sabor Urbano", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface)
                    }

                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Surface(shape = NevesGoShapes.extraSmall, color = MaterialTheme.colorScheme.secondaryContainer, contentColor = MaterialTheme.colorScheme.onSecondaryContainer) {
                            Text("DESTINO ATUAL", style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp, fontWeight = FontWeight.Bold), modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp))
                        }
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                            Column {
                                Text("Ana Silva", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary)
                                Text("#F8921", style = DataMono, color = MaterialTheme.colorScheme.secondary)
                            }
                            Surface(shape = CircleShape, color = MaterialTheme.colorScheme.surfaceContainerHigh, contentColor = MaterialTheme.colorScheme.primary, onClick = { /* TODO */ }, modifier = Modifier.size(40.dp)) {
                                Box(contentAlignment = Alignment.Center) { Icon(Icons.Outlined.Call, contentDescription = "Ligar") }
                            }
                        }
                        Text("Rua das Palmeiras, 1420 - Apt 82B\nJardins, São Paulo - SP", style = MaterialTheme.typography.bodyMedium.copy(lineHeight = 20.sp), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }

                    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f), modifier = Modifier.padding(vertical = 8.dp))

                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                            Column {
                                Text("Carlos Mendes", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary)
                                Text("#F8922", style = DataMono, color = MaterialTheme.colorScheme.secondary)
                            }
                            Surface(shape = CircleShape, color = MaterialTheme.colorScheme.surfaceContainerHigh, contentColor = MaterialTheme.colorScheme.primary, onClick = { /* TODO */ }, modifier = Modifier.size(40.dp)) {
                                Box(contentAlignment = Alignment.Center) { Icon(Icons.Outlined.Call, contentDescription = "Ligar") }
                            }
                        }
                        Text("Av. Paulista, 2000 - Conj 41\nBela Vista, São Paulo - SP", style = MaterialTheme.typography.bodyMedium.copy(lineHeight = 20.sp), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }

            // OTP Input
            if (!isFinished) {
                Column(modifier = Modifier.padding(horizontal = 24.dp).padding(top = 16.dp)) {
                    Text("CÓDIGO DE CONFIRMAÇÃO (OTP)", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold), color = if (isError) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant)
                    OutlinedTextField(
                        value = otpCode,
                        onValueChange = { if (it.length <= 4) otpCode = it },
                        modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                        textStyle = MaterialTheme.typography.headlineMedium.copy(textAlign = androidx.compose.ui.text.style.TextAlign.Center, letterSpacing = 8.sp),
                        isError = isError,
                        shape = NevesGoShapes.medium,
                        keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number),
                        singleLine = true,
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = MaterialTheme.colorScheme.primary,
                            unfocusedBorderColor = MaterialTheme.colorScheme.outlineVariant,
                            errorBorderColor = MaterialTheme.colorScheme.error
                        )
                    )
                }
            }

            Box(modifier = Modifier.padding(24.dp).padding(top = 8.dp)) {
                Button(
                    onClick = { 
                        if (otpCode.length == 4) {
                            val success = onConfirmClick(otpCode)
                            if (!success) isError = true
                        }
                    },
                    enabled = !isConfirming && (isFinished || otpCode.length == 4),
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    shape = NevesGoShapes.medium,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (isFinished) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.secondary,
                        contentColor = if (isFinished) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSecondary,
                        disabledContainerColor = MaterialTheme.colorScheme.secondary.copy(alpha = 0.8f),
                        disabledContentColor = MaterialTheme.colorScheme.onSecondary
                    ),
                    elevation = ButtonDefaults.buttonElevation(defaultElevation = 4.dp)
                ) {
                    if (isConfirming) {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                            CircularProgressIndicator(color = MaterialTheme.colorScheme.onSecondary, strokeWidth = 2.dp, modifier = Modifier.size(20.dp))
                            Text("Processando...", style = MaterialTheme.typography.labelLarge)
                        }
                    } else if (isFinished) {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Outlined.DoneAll, contentDescription = null)
                            Text("Entrega Finalizada!", style = MaterialTheme.typography.labelLarge)
                        }
                    } else {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Outlined.CheckCircle, contentDescription = null)
                            Text("Confirmar Entrega", style = MaterialTheme.typography.labelLarge)
                        }
                    }
                }
            }
        }
    }
}


@Composable
private fun OrderItem(headerTitle: String, distanceTime: String, pickup: String, delivery: String) {
    Column {
        Row(
            modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(text = headerTitle, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurface)
            Text(text = distanceTime.uppercase(), style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, fontSize = 10.sp), color = MaterialTheme.colorScheme.secondary)
        }
        
        Row(modifier = Modifier.height(IntrinsicSize.Min)) {
            Box(modifier = Modifier.padding(start = 9.dp).width(1.dp).fillMaxHeight().background(MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f)))
            
            Column(verticalArrangement = Arrangement.spacedBy(16.dp), modifier = Modifier.padding(start = 12.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    Box(modifier = Modifier.size(20.dp).offset(x = (-22).dp).background(MaterialTheme.colorScheme.secondary, CircleShape), contentAlignment = Alignment.Center) {
                        Box(modifier = Modifier.size(6.dp).background(MaterialTheme.colorScheme.onSecondary, CircleShape))
                    }
                    Column(modifier = Modifier.offset(x = (-22).dp)) {
                        Text("RETIRADA", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, letterSpacing = 0.05.em, fontSize = 10.sp), color = MaterialTheme.colorScheme.secondary)
                        Text(pickup, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold), color = MaterialTheme.colorScheme.onSurface)
                    }
                }
                
                Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    Box(modifier = Modifier.size(20.dp).offset(x = (-22).dp).background(MaterialTheme.colorScheme.error, CircleShape), contentAlignment = Alignment.Center) {
                        Icon(Icons.Outlined.LocationOn, contentDescription = null, tint = MaterialTheme.colorScheme.onError, modifier = Modifier.size(12.dp))
                    }
                    Column(modifier = Modifier.offset(x = (-22).dp)) {
                        Text("ENTREGA", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, letterSpacing = 0.05.em, fontSize = 10.sp), color = MaterialTheme.colorScheme.error)
                        Text(delivery, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold), color = MaterialTheme.colorScheme.onSurface)
                    }
                }
            }
        }
    }
}

