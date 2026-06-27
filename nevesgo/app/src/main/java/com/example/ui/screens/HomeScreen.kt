package com.example.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.expandVertically
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.MyLocation
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PowerSettingsNew
import androidx.compose.material.icons.filled.Flag
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Storefront
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.SportsMotorsports
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.example.ui.CockpitUiState
import com.example.ui.DriverViewModel
import com.example.ui.DeliveryViewModel
import com.example.ui.theme.SuccessGreen

import android.annotation.SuppressLint
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.compose.runtime.DisposableEffect

import org.osmdroid.config.Configuration
import org.osmdroid.views.MapView
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.overlay.Marker
import androidx.compose.ui.viewinterop.AndroidView

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(navController: NavController, viewModel: DeliveryViewModel = viewModel(), driverViewModel: DriverViewModel = viewModel()) {
    val pending by viewModel.pendingDeliveries.collectAsStateWithLifecycle()
    val cockpitState by driverViewModel.uiState.collectAsStateWithLifecycle()
    val statusUpdateInFlight by driverViewModel.statusUpdateInFlight.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val cockpit = (cockpitState as? CockpitUiState.Success)?.cockpit
    val isAvailable = cockpit?.driver?.online == true
    
    var previousPendingSize by remember { mutableIntStateOf(pending.size) }
    var showNewDeliveryAlert by remember { mutableStateOf(false) }
    var newestDelivery by remember { mutableStateOf<com.example.data.local.OrderEntity?>(null) }

    LaunchedEffect(pending.size, isAvailable) {
        if (isAvailable && pending.size > previousPendingSize) {
            newestDelivery = pending.lastOrNull()
            showNewDeliveryAlert = true
        }
        previousPendingSize = pending.size
    }
    
    var mapView by remember { mutableStateOf<MapView?>(null) }
    val lifecycleOwner = LocalLifecycleOwner.current

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                androidx.lifecycle.Lifecycle.Event.ON_RESUME -> {
                    mapView?.onResume()
                    val hasFine = androidx.core.content.ContextCompat.checkSelfPermission(context, android.Manifest.permission.ACCESS_FINE_LOCATION) == android.content.pm.PackageManager.PERMISSION_GRANTED
                    val hasCoarse = androidx.core.content.ContextCompat.checkSelfPermission(context, android.Manifest.permission.ACCESS_COARSE_LOCATION) == android.content.pm.PackageManager.PERMISSION_GRANTED
                    if (hasFine || hasCoarse) {
                        mapView?.overlays?.filterIsInstance<org.osmdroid.views.overlay.mylocation.MyLocationNewOverlay>()?.firstOrNull()?.let { overlay ->
                            if (!overlay.isMyLocationEnabled) {
                                overlay.enableMyLocation()
                                overlay.enableFollowLocation()
                            }
                        }
                    }
                }
                androidx.lifecycle.Lifecycle.Event.ON_PAUSE -> mapView?.onPause()
                else -> {}
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
            mapView?.onDetach()
        }
    }

    Box(modifier = Modifier.fillMaxSize().background(MaterialTheme.colorScheme.surfaceContainer)) {
        // Native Osmdroid Map
        AndroidView(
            factory = { ctx ->
                MapView(ctx).apply {
                    mapView = this
                    setMultiTouchControls(true)
                    controller.setZoom(16.0)
                    controller.setCenter(GeoPoint(-23.5505, -46.6333)) // Default center
                    
                    val locationOverlay = org.osmdroid.views.overlay.mylocation.MyLocationNewOverlay(
                        org.osmdroid.views.overlay.mylocation.GpsMyLocationProvider(ctx), this
                    )
                    
                    val hasFine = androidx.core.content.ContextCompat.checkSelfPermission(ctx, android.Manifest.permission.ACCESS_FINE_LOCATION) == android.content.pm.PackageManager.PERMISSION_GRANTED
                    val hasCoarse = androidx.core.content.ContextCompat.checkSelfPermission(ctx, android.Manifest.permission.ACCESS_COARSE_LOCATION) == android.content.pm.PackageManager.PERMISSION_GRANTED
                    
                    if (hasFine || hasCoarse) {
                        locationOverlay.enableMyLocation()
                        locationOverlay.enableFollowLocation()
                    }
                    
                    overlays.add(locationOverlay)
                }
            },
            modifier = Modifier.fillMaxSize()
        )

        Column(modifier = Modifier.fillMaxSize().statusBarsPadding()) {
            // Elegant Top Header
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 16.dp),
                shape = RoundedCornerShape(100.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.95f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    val driverName = cockpit?.driver?.name ?: "Carregando..."
                    val statusText = cockpit?.driver?.status ?: if (isAvailable) "ONLINE" else "OFFLINE"
                    
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(48.dp)
                                .clip(CircleShape)
                                .background(MaterialTheme.colorScheme.surfaceContainerHighest),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(Icons.Filled.Person, contentDescription = "Profile", tint = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Spacer(modifier = Modifier.width(16.dp))
                        Column {
                            Text(
                                text = driverName,
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.ExtraBold,
                                color = MaterialTheme.colorScheme.onBackground
                            )
                            Text(
                                text = statusText.replace('_', ' '),
                                style = MaterialTheme.typography.bodySmall,
                                color = if (isAvailable) SuccessGreen else MaterialTheme.colorScheme.onSurfaceVariant,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.weight(1f))

                    // Map Controls Location
                    Box(
                        modifier = Modifier
                            .padding(horizontal = 24.dp)
                            .align(Alignment.End)
                            .size(56.dp)
                            .clip(CircleShape)
                            .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.95f))
                            .clickable {
                                mapView?.overlays?.filterIsInstance<org.osmdroid.views.overlay.mylocation.MyLocationNewOverlay>()?.firstOrNull()?.let { overlay ->
                                    val location = overlay.myLocation
                                    if (location != null) {
                                        mapView?.controller?.animateTo(location, 17.0, 1000L)
                                    }
                                }
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(Icons.Filled.MyLocation, contentDescription = "Center", tint = MaterialTheme.colorScheme.primary)
                    }

            // Bottom Cockpit Panel
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                shape = RoundedCornerShape(32.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.95f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 12.dp)
            ) {
                Column(modifier = Modifier.padding(24.dp)) {
                    val todayStats = cockpit?.today
                    val walletBalance = cockpit?.wallet?.balanceCents ?: 0
                    val activeOrdersCount = cockpit?.activeOrdersCount ?: 0
                    val activeOrdersLimit = cockpit?.activeOrdersLimit ?: 0
                    val pendingDocuments = cockpit?.pendingDocuments ?: 0
                    
                    if (todayStats != null) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    text = "Ganhos Hoje",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                Text(
                                    text = "R$ ${String.format("%.2f", todayStats.earningsCents / 100.0)}",
                                    style = MaterialTheme.typography.headlineMedium,
                                    fontWeight = FontWeight.Black,
                                    color = MaterialTheme.colorScheme.onSurface
                                )
                            }
                            
                            Column(horizontalAlignment = Alignment.End) {
                                Text(
                                    text = "Entregas",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                Text(
                                    text = "${todayStats.deliveries}",
                                    style = MaterialTheme.typography.headlineMedium,
                                    fontWeight = FontWeight.Black,
                                    color = MaterialTheme.colorScheme.onSurface
                                )
                            }
                        }
                        
                        Spacer(modifier = Modifier.height(16.dp))
                        
                        Text(
                            text = "Meta Diária: ${todayStats.goalProgressPercent}%",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        LinearProgressIndicator(
                            progress = { todayStats.goalProgressPercent / 100f },
                            modifier = Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)),
                            color = MaterialTheme.colorScheme.primary,
                            trackColor = MaterialTheme.colorScheme.surfaceVariant
                        )
                        Spacer(modifier = Modifier.height(20.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            SummaryChip(
                                label = "Saldo",
                                value = "R$ ${String.format("%.2f", walletBalance / 100.0)}"
                            )
                            SummaryChip(
                                label = "Ativas",
                                value = "$activeOrdersCount/$activeOrdersLimit"
                            )
                            SummaryChip(
                                label = "Docs",
                                value = pendingDocuments.toString()
                            )
                        }
                        Spacer(modifier = Modifier.height(24.dp))
                    }

                    AnimatedVisibility(
                        visible = isAvailable && pending.isNotEmpty(),
                        enter = expandVertically(spring()),
                        exit = shrinkVertically(spring())
                    ) {
                        Surface(
                            shape = RoundedCornerShape(16.dp),
                            color = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp).clickable { navController.navigate("deliveries") }
                        ) {
                            Row(
                                modifier = Modifier.padding(16.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    "${pending.size} novos pedidos",
                                    color = MaterialTheme.colorScheme.onPrimary,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 16.sp
                                )
                                Text("Ver →", color = MaterialTheme.colorScheme.onPrimary, fontWeight = FontWeight.Black)
                            }
                        }
                    }

                    if (isAvailable) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                // Pulsing dot
                                val infiniteTransition = androidx.compose.animation.core.rememberInfiniteTransition(label = "pulse")
                                val alpha by infiniteTransition.animateFloat(
                                    initialValue = 0.3f,
                                    targetValue = 1f,
                                    animationSpec = androidx.compose.animation.core.infiniteRepeatable(
                                        animation = androidx.compose.animation.core.tween<Float>(1000),
                                        repeatMode = androidx.compose.animation.core.RepeatMode.Reverse
                                    ),
                                    label = "alpha"
                                )
                                Box(
                                    modifier = Modifier
                                        .size(12.dp)
                                        .clip(CircleShape)
                                        .background(MaterialTheme.colorScheme.primary.copy(alpha = alpha))
                                )
                                Spacer(modifier = Modifier.width(12.dp))
                                Column {
                                    Text(
                                        text = if (activeOrdersCount > 0) "Voce tem $activeOrdersCount entrega(s) ativa(s)" else "Buscando novas ofertas...",
                                        style = MaterialTheme.typography.titleMedium,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )
                                    Spacer(modifier = Modifier.height(2.dp))
                                    Text(
                                        text = if (activeOrdersCount > 0) "Limite operacional atual: $activeOrdersCount/$activeOrdersLimit" else "Mantenha o app aberto para receber pedidos.",
                                        style = MaterialTheme.typography.bodyMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }
                            
                            // Small subtle offline button
                            FilledTonalButton(
                                onClick = { driverViewModel.setAvailability(false) },
                                enabled = !statusUpdateInFlight,
                                colors = ButtonDefaults.filledTonalButtonColors(
                                    containerColor = MaterialTheme.colorScheme.surfaceVariant,
                                    contentColor = MaterialTheme.colorScheme.onSurfaceVariant
                                ),
                                shape = RoundedCornerShape(16.dp)
                            ) {
                                Icon(Icons.Filled.PowerSettingsNew, contentDescription = "Ficar Offline", modifier = Modifier.size(18.dp))
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(if (statusUpdateInFlight) "Atualizando..." else "Offline", fontWeight = FontWeight.Bold)
                            }
                        }
                    } else {
                        com.example.ui.components.DriverPrimaryButton(
                            text = "FICAR ONLINE",
                            onClick = { driverViewModel.setAvailability(true) },
                            color = SuccessGreen,
                            contentColor = Color.White
                        )
                    }
                }
            }
        }

        AnimatedVisibility(
            visible = showNewDeliveryAlert && newestDelivery != null,
            enter = androidx.compose.animation.slideInVertically(initialOffsetY = { it }) + androidx.compose.animation.fadeIn(),
            exit = androidx.compose.animation.slideOutVertically(targetOffsetY = { it }) + androidx.compose.animation.fadeOut()
        ) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color.Black.copy(alpha = 0.5f))
                    .padding(16.dp),
                contentAlignment = Alignment.BottomCenter
            ) {
                var timeLeft by remember { mutableIntStateOf(10) }

                LaunchedEffect(showNewDeliveryAlert) {
                    if (showNewDeliveryAlert) {
                        timeLeft = 10
                        while (timeLeft > 0) {
                            kotlinx.coroutines.delay(1000)
                            timeLeft--
                        }
                        if (timeLeft == 0) {
                            showNewDeliveryAlert = false
                        }
                    }
                }

                Card(
                    modifier = Modifier.fillMaxWidth().navigationBarsPadding(),
                    shape = RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 12.dp)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "R\$ ${String.format("%.2f", newestDelivery!!.fareCents / 100.0)}",
                            style = MaterialTheme.typography.displaySmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Text(
                            text = "R\$ ${String.format("%.2f", (newestDelivery!!.fareCents / 100.0) / (newestDelivery!!.distanceMeters / 1000.0))} por km",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Medium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        
                        Spacer(modifier = Modifier.height(8.dp))
                        
                        Row(
                            horizontalArrangement = Arrangement.Center,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Filled.Flag, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("${String.format("%.2f", newestDelivery!!.distanceMeters / 1000.0)} Km", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
                            Spacer(modifier = Modifier.width(16.dp))
                            Icon(Icons.Filled.LocationOn, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("1 parada", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
                        }

                        Spacer(modifier = Modifier.height(24.dp))
                        HorizontalDivider()
                        Spacer(modifier = Modifier.height(24.dp))

                        Row(modifier = Modifier.fillMaxWidth()) {
                            Column(
                                horizontalAlignment = Alignment.CenterHorizontally,
                                modifier = Modifier.padding(end = 16.dp)
                            ) {
                                Icon(Icons.Filled.Storefront, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                                androidx.compose.foundation.Canvas(modifier = Modifier.width(2.dp).height(40.dp)) {
                                    drawLine(
                                        color = Color.Gray,
                                        start = androidx.compose.ui.geometry.Offset(size.width / 2, 0f),
                                        end = androidx.compose.ui.geometry.Offset(size.width / 2, size.height),
                                        pathEffect = androidx.compose.ui.graphics.PathEffect.dashPathEffect(floatArrayOf(10f, 10f), 0f)
                                    )
                                }
                                Icon(Icons.Filled.Flag, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = newestDelivery!!.originName,
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onSurface
                                )
                                Text(
                                    text = newestDelivery!!.originAddress,
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                
                                Spacer(modifier = Modifier.height(24.dp))
                                
                                Text(
                                    text = newestDelivery!!.destinationName,
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onSurface
                                )
                                Text(
                                    text = newestDelivery!!.destinationAddress,
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                        
                        Spacer(modifier = Modifier.height(32.dp))

                        Spacer(modifier = Modifier.height(16.dp))

                        com.example.ui.components.DriverSwipeButton(
                            text = "ACEITAR CORRIDA",
                            onSwipeComplete = { 
                                viewModel.acceptDelivery(newestDelivery!!)
                                showNewDeliveryAlert = false
                                navController.navigate("deliveries")
                            },
                            containerColor = SuccessGreen,
                            contentColor = Color.White
                        )
                        
                        Spacer(modifier = Modifier.height(16.dp))
                        
                        com.example.ui.components.DriverSecondaryButton(
                            text = "RECUSAR ($timeLeft" + "s)",
                            onClick = { showNewDeliveryAlert = false },
                            isDestructive = true
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun SummaryChip(label: String, value: String) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f)
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
        }
    }
}
