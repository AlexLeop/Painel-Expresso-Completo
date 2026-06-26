package com.example.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.*
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.navigation.NavController
import com.example.ui.theme.SuccessGreen
import android.annotation.SuppressLint
import org.osmdroid.views.MapView
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Polyline
import org.osmdroid.config.Configuration
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.DisposableEffect
import com.example.domain.models.OrderDetailResponse
import com.example.domain.models.OrderStop
import com.example.domain.models.SimplePoint
import com.example.ui.DeliveryViewModel
import com.example.services.TrackingService

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DeliveryAcceptedScreen(
    navController: NavController,
    orderId: String?,
    viewModel: DeliveryViewModel = viewModel()
) {
    val orderDetails by viewModel.orderDetails.collectAsStateWithLifecycle()
    val operationError by viewModel.operationError.collectAsStateWithLifecycle()
    val orderDetail = orderId?.let { orderDetails[it] }

    LaunchedEffect(orderId) {
        if (!orderId.isNullOrBlank()) {
            viewModel.loadOrderDetails(orderId)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Corrida Aceita", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(Icons.Filled.Close, contentDescription = "Close")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background)
            )
        },
        containerColor = MaterialTheme.colorScheme.background,
        bottomBar = {
            com.example.ui.components.DriverPrimaryButton(
                text = "INICIAR CORRIDA",
                onClick = {
                    if (!orderId.isNullOrBlank()) {
                        viewModel.startDelivery(
                            orderId = orderId,
                            onSuccess = { navController.navigate("navigation_screen/$orderId") }
                        )
                    }
                },
                modifier = Modifier.padding(horizontal = 24.dp, vertical = 24.dp)
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(32.dp))
            Box(contentAlignment = Alignment.Center) {
                Surface(shape = CircleShape, color = SuccessGreen.copy(alpha = 0.15f), modifier = Modifier.size(120.dp)) {}
                Surface(shape = CircleShape, color = SuccessGreen.copy(alpha = 0.3f), modifier = Modifier.size(80.dp)) {}
                Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = SuccessGreen, modifier = Modifier.size(48.dp))
            }
            Spacer(modifier = Modifier.height(24.dp))
            Text("Corrida Aceita!", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.ExtraBold)
            Text("Prepare-se para o trajeto", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            
            Spacer(modifier = Modifier.height(48.dp))
            
            DeliveryInfoCard(
                Icons.Filled.Payments,
                "Valor da Corrida",
                orderDetail?.let { "R$ ${String.format("%.2f", it.fareValueCents / 100.0)}" } ?: "Carregando valor...",
                emphasized = true
            )
            Spacer(modifier = Modifier.height(16.dp))
            DeliveryInfoCard(
                Icons.Filled.Storefront,
                "Coleta: ${orderDetail?.origin?.storeName ?: "Loja"}",
                orderDetail?.origin?.location?.let { point ->
                    if (point.lat != null && point.lng != null) {
                        resolveAddress(point, context, "Lat ${point.lat}, Lng ${point.lng}")
                    } else {
                        "Origem sem coordenadas no payload"
                    }
                } ?: "Carregando origem..."
            )
            Spacer(modifier = Modifier.height(16.dp))
            DeliveryInfoCard(
                Icons.Filled.HomeRepairService,
                "Entrega: ${orderDetail?.destination?.lastStopId ?: "Destino final"}",
                orderDetail?.destination?.lastStopLocation?.let { point ->
                    if (point.lat != null && point.lng != null) {
                        resolveAddress(point, context, "Lat ${point.lat}, Lng ${point.lng}")
                    } else {
                        "Ultima parada sem coordenadas"
                    }
                } ?: "Carregando destino..."
            )

            if (!orderId.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(20.dp))
                TextButton(
                    onClick = {
                        viewModel.releaseDelivery(orderId, "Liberada pelo app antes do inicio da corrida.")
                        navController.navigate("deliveries")
                    }
                ) {
                    Text("Devolver corrida para a operacao")
                }
            }
            if (!operationError.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = operationError.orEmpty(),
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        }
    }
}

@Composable
fun DeliveryInfoCard(icon: androidx.compose.ui.graphics.vector.ImageVector, title: String, subtitle: String, emphasized: Boolean = false) {
    Card(
        shape = RoundedCornerShape(20.dp), 
        colors = CardDefaults.cardColors(containerColor = if(emphasized) MaterialTheme.colorScheme.primary.copy(alpha=0.05f) else MaterialTheme.colorScheme.surface), 
        border = BorderStroke(1.dp, if(emphasized) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant),
        elevation = CardDefaults.cardElevation(0.dp), 
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(modifier = Modifier.padding(20.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(shape = CircleShape, color = if(emphasized) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant, modifier = Modifier.size(48.dp)) {
                Icon(icon, contentDescription = null, modifier = Modifier.padding(12.dp), tint = if(emphasized) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Spacer(modifier = Modifier.width(16.dp))
            Column {
                Text(title, fontWeight = FontWeight.Bold, fontSize = 16.sp, color = MaterialTheme.colorScheme.onSurface)
                Text(subtitle, color = if(emphasized) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 14.sp, fontWeight = if(emphasized) FontWeight.Bold else FontWeight.Normal)
            }
        }
    }
}


@SuppressLint("SetJavaScriptEnabled")
@Composable
fun RouteNavigationScreen(
    navController: NavController,
    orderId: String?,
    viewModel: DeliveryViewModel = viewModel(),
    driverViewModel: com.example.ui.DriverViewModel = viewModel()
) {
    val context = LocalContext.current
    var isMapReady by androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf(false) }
    val orderDetails by viewModel.orderDetails.collectAsStateWithLifecycle()
    val cockpitState by driverViewModel.uiState.collectAsStateWithLifecycle()
    val orderDetail = orderId?.let { orderDetails[it] }
    val currentShift = (cockpitState as? com.example.ui.CockpitUiState.Success)?.cockpit?.shift
    val hasOpenShift = !currentShift?.sessionId.isNullOrBlank()
    val nextOperationalStop = remember(orderDetail) { orderDetail?.nextOperationalStop() }
    val routeStartPoint = remember(orderDetail, nextOperationalStop) {
        orderDetail?.origin?.location.toGeoPointOrNull()
            ?: nextOperationalStop?.location.toGeoPointOrNull()
            ?: orderDetail?.destination?.lastStopLocation.toGeoPointOrNull()
    }
    val routeEndPoint = remember(orderDetail, nextOperationalStop) {
        nextOperationalStop?.location.toGeoPointOrNull()
            ?: orderDetail?.destination?.lastStopLocation.toGeoPointOrNull()
            ?: orderDetail?.origin?.location.toGeoPointOrNull()
    }
    val routeInstruction = when {
        nextOperationalStop != null && nextOperationalStop.type.uppercase() == "PICKUP" ->
            "Siga para a coleta da parada ${nextOperationalStop.sequence}"
        nextOperationalStop != null ->
            "Siga para a entrega da parada ${nextOperationalStop.sequence}"
        orderDetail != null ->
            "Siga para o destino final"
        else ->
            "Preparando rota operacional"
    }
    val routeSummary = when {
        nextOperationalStop != null -> {
            val distanceKm = (orderDetail?.distanceMeters ?: 0) / 1000.0
            "${String.format("%.1f", distanceKm)} km restantes • ${nextOperationalStop.type}"
        }
        orderDetail != null -> {
            "${orderDetail.stops.count { it.completedAt == null }} parada(s) pendente(s)"
        }
        else -> "Carregando dados do pedido..."
    }

    LaunchedEffect(Unit) {
        Configuration.getInstance().userAgentValue = context.packageName
        isMapReady = true
        driverViewModel.loadCockpit()
    }

    LaunchedEffect(orderId) {
        if (!orderId.isNullOrBlank()) {
            viewModel.loadOrderDetails(orderId)
        }
    }

    var mapViewObserver by androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf<MapView?>(null) }
    val lifecycleOwner = androidx.lifecycle.compose.LocalLifecycleOwner.current

    androidx.compose.runtime.DisposableEffect(lifecycleOwner) {
        val observer = androidx.lifecycle.LifecycleEventObserver { _, event ->
            when (event) {
                androidx.lifecycle.Lifecycle.Event.ON_RESUME -> mapViewObserver?.onResume()
                androidx.lifecycle.Lifecycle.Event.ON_PAUSE -> mapViewObserver?.onPause()
                else -> {}
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
            mapViewObserver?.onDetach()
        }
    }

    Box(modifier = Modifier.fillMaxSize().background(MaterialTheme.colorScheme.surfaceContainer)) {
        if (isMapReady) {
            AndroidView(
                factory = { ctx ->
                    MapView(ctx).apply {
                        mapViewObserver = this
                        setMultiTouchControls(true)
                        controller.setZoom(15.0)
                    }
                },
                update = { mapView ->
                    mapView.overlays.clear()

                    routeStartPoint?.let { start ->
                        val startMarker = Marker(mapView).apply {
                            position = start
                            setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                            title = orderDetail?.origin?.storeName ?: "Origem"
                        }
                        mapView.overlays.add(startMarker)
                        mapView.controller.setCenter(start)
                    }

                    routeEndPoint?.let { end ->
                        val endMarker = Marker(mapView).apply {
                            position = end
                            setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                            title = nextOperationalStop?.let { stop ->
                                if (stop.type.uppercase() == "PICKUP") {
                                    "Coleta ${stop.sequence}"
                                } else {
                                    "Parada ${stop.sequence}"
                                }
                            } ?: "Destino"
                        }
                        mapView.overlays.add(endMarker)
                    }

                    if (routeStartPoint != null && routeEndPoint != null) {
                        // Desenhando de forma assíncrona para não travar a UI Thread
                        kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.IO).launch {
                            try {
                                val roadManager = org.osmdroid.bonuspack.routing.OSRMRoadManager(ctx, "NevesGoApp/1.0")
                                // OSRM default server is sometimes rate limited, but works for PoC/Go-Live
                                val waypoints = java.util.ArrayList<org.osmdroid.util.GeoPoint>()
                                waypoints.add(routeStartPoint)
                                waypoints.add(routeEndPoint)
                                
                                val road = roadManager.getRoad(waypoints)
                                
                                if (road.mStatus == org.osmdroid.bonuspack.routing.Road.STATUS_OK) {
                                    val roadOverlay = org.osmdroid.bonuspack.routing.RoadManager.buildRoadOverlay(road, android.graphics.Color.BLUE, 10f)
                                    
                                    kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.Main) {
                                        mapView.overlays.add(roadOverlay)
                                        mapView.invalidate()
                                    }
                                } else {
                                    // Fallback: Linha reta se o OSRM falhar
                                    kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.Main) {
                                        val routeLine = Polyline().apply {
                                            outlinePaint.color = android.graphics.Color.RED
                                            outlinePaint.strokeWidth = 10f
                                            setPoints(listOf(routeStartPoint, routeEndPoint))
                                        }
                                        mapView.overlays.add(routeLine)
                                        mapView.invalidate()
                                    }
                                }
                            } catch (e: Exception) {
                                e.printStackTrace()
                            }
                        }
                    }

                    mapView.invalidate()
                },
                modifier = Modifier.fillMaxSize()
            )
        }
        
        Column(modifier = Modifier.fillMaxSize()) {
            Spacer(modifier = Modifier.statusBarsPadding().height(16.dp))
            Card(
                shape = RoundedCornerShape(24.dp), 
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp), 
                elevation = CardDefaults.cardElevation(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Row(modifier = Modifier.padding(20.dp), verticalAlignment = Alignment.CenterVertically) {
                    Surface(shape = CircleShape, color = MaterialTheme.colorScheme.primary, modifier = Modifier.size(56.dp)) {
                        Icon(Icons.Filled.TurnLeft, contentDescription = null, tint = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.padding(12.dp))
                    }
                    Spacer(modifier = Modifier.width(16.dp))
                    Column {
                        Text(routeInstruction, fontWeight = FontWeight.ExtraBold, fontSize = 22.sp, color = MaterialTheme.colorScheme.onSurface)
                        Text(routeSummary, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 16.sp)
                    }
                }
            }
            
            Spacer(modifier = Modifier.weight(1f))
            
            Card(
                shape = RoundedCornerShape(topStart = 32.dp, topEnd = 32.dp), 
                elevation = CardDefaults.cardElevation(24.dp), 
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(24.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                         Surface(shape = CircleShape, color = MaterialTheme.colorScheme.primaryContainer, modifier = Modifier.size(56.dp)) {
                             Icon(Icons.Filled.Flag, contentDescription = null, tint = MaterialTheme.colorScheme.onPrimaryContainer, modifier = Modifier.padding(16.dp))
                         }
                         Spacer(modifier = Modifier.width(16.dp))
                         Column(modifier = Modifier.weight(1f)) {
                             Text(
                                 nextOperationalStop?.let { stop ->
                                     if (stop.type.uppercase() == "PICKUP") {
                                         "Coleta em ${orderDetail?.origin?.storeName ?: "andamento"}"
                                     } else {
                                         "Parada ${stop.sequence} em execucao"
                                     }
                                 } ?: (orderDetail?.origin?.storeName ?: "Entrega em andamento"),
                                 fontWeight = FontWeight.Black,
                                 fontSize = 20.sp,
                                 color = MaterialTheme.colorScheme.onSurface
                             )
                             Text(
                                 routeSummary,
                                 color = MaterialTheme.colorScheme.onSurfaceVariant
                             )
                         }
                    }
                    Spacer(modifier = Modifier.height(24.dp))
                    if (!hasOpenShift) {
                        Text(
                            text = "Abra uma sessao de turno antes de iniciar o rastreamento desta corrida.",
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodyMedium
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                    } else if (currentShift != null) {
                        Text(
                            text = "Jornada aberta em ${currentShift.storeName ?: "loja"} • ${currentShift.turnoName ?: "turno"}",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            style = MaterialTheme.typography.bodyMedium
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                    }
                    if (routeEndPoint != null) {
                        Row(modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp), horizontalArrangement = Arrangement.Center) {
                            OutlinedButton(onClick = {
                                val lat = routeEndPoint.latitude
                                val lng = routeEndPoint.longitude
                                val uri = android.net.Uri.parse("geo:$lat,$lng?q=$lat,$lng")
                                val mapIntent = android.content.Intent(android.content.Intent.ACTION_VIEW, uri)
                                try {
                                    context.startActivity(android.content.Intent.createChooser(mapIntent, "Navegar com"))
                                } catch (e: Exception) {
                                    android.widget.Toast.makeText(context, "Nenhum aplicativo de mapas encontrado", android.widget.Toast.LENGTH_SHORT).show()
                                }
                            }) {
                                Icon(Icons.Filled.Map, contentDescription = null)
                                Spacer(Modifier.width(8.dp))
                                Text("Abrir em Mapa Externo (Waze/Google Maps)")
                            }
                        }
                    }
                    com.example.ui.components.DriverSwipeButton(
                        text = if (hasOpenShift) "CHEGUEI A PROXIMA PARADA" else "IR PARA TURNOS",
                        onSwipeComplete = {
                            if (hasOpenShift) {
                                navController.navigate("confirmar_entrega/${orderId ?: ""}")
                            } else {
                                navController.navigate("escalas")
                            }
                        },
                        containerColor = MaterialTheme.colorScheme.primary,
                        contentColor = MaterialTheme.colorScheme.onPrimary
                    )
                    Spacer(modifier = Modifier.navigationBarsPadding())
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConfirmDeliveryScreen(
    navController: NavController,
    orderId: String?,
    viewModel: DeliveryViewModel = viewModel()
) {
    var pin by remember { mutableStateOf("") }
    val orderDetails by viewModel.orderDetails.collectAsStateWithLifecycle()
    val operationError by viewModel.operationError.collectAsStateWithLifecycle()
    val orderDetail = orderId?.let { orderDetails[it] }
    val pendingStops = remember(orderDetail) {
        orderDetail?.stops?.filter { it.completedAt == null && it.type.uppercase() != "PICKUP" } ?: emptyList()
    }
    var selectedStopId by remember(orderDetail?.id) { mutableStateOf<String?>(null) }
    LaunchedEffect(pendingStops.firstOrNull()?.id) {
        if (selectedStopId == null) {
            selectedStopId = pendingStops.firstOrNull()?.id
        }
    }
    val selectedStop = pendingStops.firstOrNull { it.id == selectedStopId } ?: pendingStops.firstOrNull()

    LaunchedEffect(orderId) {
        if (!orderId.isNullOrBlank()) {
            viewModel.loadOrderDetails(orderId)
        }
    }
    
    Scaffold(
        topBar = {
            Column {
                TopAppBar(
                    title = { Text("Entregue o pedido", fontWeight = FontWeight.Bold, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center) },
                    actions = {
                        IconButton(
                            onClick = {
                                navController.navigate(
                                    "reportar_problema/${orderId ?: "sem-ordem"}/${selectedStop?.id ?: "sem-stop"}"
                                )
                            }
                        ) { Icon(Icons.Filled.ReportProblem, contentDescription = "Intercorrência") }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
                )
                HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant)
            }
        },
        containerColor = MaterialTheme.colorScheme.surface
    ) { padding ->
        Column(modifier = Modifier.padding(padding).fillMaxSize()) {
            
            // Address & "Ir" Button row
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 24.dp, vertical = 20.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = selectedStop?.location?.let { point ->
                        if (point.lat != null && point.lng != null) {
                            resolveAddress(point, LocalContext.current, "Lat ${point.lat}\nLng ${point.lng}")
                        } else {
                            "Destino sem coordenadas"
                        }
                    } ?: orderDetail?.destination?.lastStopLocation?.let { point ->
                        if (point.lat != null && point.lng != null) {
                            resolveAddress(point, LocalContext.current, "Lat ${point.lat}\nLng ${point.lng}")
                        } else {
                            "Destino sem coordenadas"
                        }
                    } ?: "Carregando destino...",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.weight(1f)
                )
                Spacer(modifier = Modifier.width(16.dp))
                Button(
                    onClick = { navController.navigate("navigation_screen/${orderId ?: ""}") },
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp)
                ) {
                    Icon(Icons.AutoMirrored.Filled.DirectionsWalk, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Ir", fontWeight = FontWeight.Bold)
                }
            }
            
            Text(
                text = "Ver rota completa >",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.fillMaxWidth().clickable { navController.navigate("navigation_screen/${orderId ?: ""}") }.padding(bottom = 20.dp),
                textAlign = TextAlign.Center,
                fontWeight = FontWeight.Bold,
                fontSize = 14.sp
            )

            HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant)
            
            Spacer(modifier = Modifier.height(24.dp))
            if (pendingStops.isNotEmpty()) {
                Text(
                    text = "Selecione a parada que sera concluida",
                    textAlign = TextAlign.Center,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontSize = 14.sp,
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 24.dp)
                )
                Spacer(modifier = Modifier.height(12.dp))
                LazyRow(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    contentPadding = PaddingValues(horizontal = 24.dp)
                ) {
                    items(pendingStops.size) { index ->
                        val stop = pendingStops[index]
                        FilterChip(
                            selected = selectedStop?.id == stop.id,
                            onClick = { selectedStopId = stop.id },
                            label = { Text("Parada ${stop.sequence}") }
                        )
                    }
                }
                Spacer(modifier = Modifier.height(24.dp))
            }
            Text(
                "Solicite ao cliente o código de entrega e\ninsira no campo abaixo.",
                textAlign = TextAlign.Center, 
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontSize = 14.sp,
                modifier = Modifier.fillMaxWidth().padding(horizontal = 24.dp)
            )
            Spacer(modifier = Modifier.height(16.dp))
            
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                for (i in 0 until 4) {
                    val char = pin.getOrNull(i)?.toString() ?: ""
                    Box(
                        modifier = Modifier
                            .padding(horizontal = 6.dp)
                            .size(56.dp)
                            .border(1.dp, if (i == pin.length) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(12.dp)),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(char, style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.onSurface)
                        if (i == pin.length) {
                             Box(modifier = Modifier.width(2.dp).height(24.dp).background(MaterialTheme.colorScheme.primary)) // cursor
                        }
                    }
                }
            }
            
            Spacer(modifier = Modifier.height(32.dp))
            HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant)
            
            Column(modifier = Modifier.fillMaxWidth().padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = "A prova digital e enviada automaticamente antes da conclusao da parada.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontSize = 13.sp,
                    modifier = Modifier.padding(bottom = 12.dp)
                )
                OutlinedButton(
                    onClick = {},
                    enabled = false,
                    modifier = Modifier.fillMaxWidth().height(52.dp),
                    shape = RoundedCornerShape(12.dp),
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
                ) {
                    Icon(Icons.Filled.PhotoCamera, contentDescription = null, tint = MaterialTheme.colorScheme.onSurface)
                    Spacer(modifier = Modifier.width(12.dp))
                    Text("Comprovante de entrega", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
                }
            }

            if (!operationError.isNullOrBlank()) {
                Text(
                    text = operationError.orEmpty(),
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 24.dp),
                    textAlign = TextAlign.Center
                )
            }

            Spacer(modifier = Modifier.weight(1f))
            
            // Custom Numeric Keypad
            Column(modifier = Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.surfaceContainerLowest)) {
                val padModifier = Modifier.weight(1f).aspectRatio(2f).clickable { }
                val rowModifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp)
                for (row in listOf(listOf("1", "2", "3"), listOf("4", "5", "6"), listOf("7", "8", "9"))) {
                    Row(modifier = rowModifier) {
                        for (key in row) {
                            Box(modifier = padModifier.clickable { if (pin.length < 4) pin += key }, contentAlignment = Alignment.Center) {
                                Text(key, style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.onSurface)
                            }
                        }
                    }
                }
                Row(modifier = rowModifier) {
                    Box(modifier = padModifier.clickable { }, contentAlignment = Alignment.Center) {
                        Text(",", style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.onSurface)
                    }
                    Box(modifier = padModifier.clickable { if (pin.length < 4) pin += "0" }, contentAlignment = Alignment.Center) {
                        Text("0", style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.onSurface)
                    }
                    Box(modifier = padModifier.clickable { }, contentAlignment = Alignment.Center) {
                         if (pin.length == 4) {
                             IconButton(onClick = {
                                 if (!orderId.isNullOrBlank() && selectedStop != null) {
                                     viewModel.finishDelivery(
                                         orderId = orderId,
                                         stopId = selectedStop.id,
                                         deliveryPin = pin,
                                         onSuccess = {
                                             navController.navigate("entrega_finalizada/${orderDetail?.fareValueCents ?: 0}")
                                         }
                                     )
                                 }
                             }) {
                                 Icon(Icons.Filled.Check, contentDescription = "OK", tint = MaterialTheme.colorScheme.primary)
                             }
                         } else {
                             IconButton(onClick = { if (pin.isNotEmpty()) pin = pin.dropLast(1) }) {
                                 Icon(Icons.AutoMirrored.Filled.Backspace, contentDescription = "Delete", tint = MaterialTheme.colorScheme.onSurfaceVariant)
                             }
                         }
                    }
                }
                Spacer(modifier = Modifier.navigationBarsPadding().height(16.dp))
            }
        }
    }
}

@Composable
fun DeliveryFinishedScreen(navController: NavController, fareCents: Int?) {
    Scaffold(
        bottomBar = {
            com.example.ui.components.DriverPrimaryButton(
                text = "VOLTAR PARA HOME",
                onClick = { navController.navigate("home") { popUpTo(0) } },
                modifier = Modifier.padding(horizontal = 24.dp, vertical = 24.dp)
            )
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { padding ->
        Column(
            modifier = Modifier.padding(padding).fillMaxSize().padding(horizontal = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
             Surface(shape = CircleShape, color = SuccessGreen, modifier = Modifier.size(96.dp)) {
                Icon(Icons.Filled.Check, contentDescription = null, tint = Color.White, modifier = Modifier.padding(16.dp))
            }
            Spacer(modifier = Modifier.height(24.dp))
            Text("Missão Cumprida!", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Black)
            Text("Entrega finalizada com sucesso", color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(modifier = Modifier.height(48.dp))
            Card(
                shape = RoundedCornerShape(24.dp), 
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(32.dp).fillMaxWidth()) {
                    Text("Valor recebido", color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 16.sp)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "R$ ${String.format("%.2f", (fareCents ?: 0) / 100.0)}",
                        color = SuccessGreen,
                        style = MaterialTheme.typography.displayMedium,
                        fontWeight = FontWeight.Black
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportProblemScreen(
    navController: NavController,
    orderId: String?,
    stopId: String?,
    viewModel: DeliveryViewModel = viewModel()
) {
    var problemReport by remember { mutableStateOf("") }
    var selectedCategory by remember { mutableStateOf("Não encontrei o cliente") }
    val operationError by viewModel.operationError.collectAsStateWithLifecycle()
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Relatar Problema", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background)
            )
        },
        containerColor = MaterialTheme.colorScheme.background,
        bottomBar = {
            Column(modifier = Modifier.padding(horizontal = 24.dp, vertical = 24.dp)) {
                Button(
                    onClick = {
                        viewModel.reportIncident(
                            orderId = orderId?.takeIf { it != "sem-ordem" },
                            stopId = stopId?.takeIf { it != "sem-stop" },
                            type = selectedCategory.uppercase().replace(' ', '_'),
                            description = problemReport.ifBlank { selectedCategory }
                        ) {
                            navController.popBackStack()
                        }
                    },
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                ) {
                    Text("Enviar Relato", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onError)
                }
                Spacer(modifier = Modifier.height(12.dp))
                OutlinedButton(
                    onClick = { navController.popBackStack() },
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    shape = RoundedCornerShape(16.dp),
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
                ) {
                    Text("Cancelar Relato", color = MaterialTheme.colorScheme.onSurface)
                }
            }
        }
    ) { padding ->
        LazyColumn(modifier = Modifier.padding(padding).fillMaxSize().padding(horizontal = 24.dp)) {
            item {
                Spacer(modifier = Modifier.height(16.dp))
                ProblemCategory("Não encontrei o cliente", selectedCategory == "Não encontrei o cliente") { selectedCategory = "Não encontrei o cliente" }
                Spacer(modifier = Modifier.height(12.dp))
                ProblemCategory("Endereço incorreto ou fechado", selectedCategory == "Endereço incorreto ou fechado") { selectedCategory = "Endereço incorreto ou fechado" }
                Spacer(modifier = Modifier.height(12.dp))
                ProblemCategory("Problema com o veículo", selectedCategory == "Problema com o veículo") { selectedCategory = "Problema com o veículo" }
                Spacer(modifier = Modifier.height(12.dp))
                ProblemCategory("Outros", selectedCategory == "Outros") { selectedCategory = "Outros" }
                
                Spacer(modifier = Modifier.height(32.dp))
                Text("Detalhes Adicionais", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                Spacer(modifier = Modifier.height(12.dp))
                OutlinedTextField(
                    value = problemReport,
                    onValueChange = { problemReport = it },
                    placeholder = { Text("Descreva o que ocorreu...") },
                    modifier = Modifier.fillMaxWidth().height(140.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        unfocusedBorderColor = MaterialTheme.colorScheme.outlineVariant
                    )
                )
                Spacer(modifier = Modifier.height(24.dp))
                if (!operationError.isNullOrBlank()) {
                    Text(
                        text = operationError.orEmpty(),
                        color = MaterialTheme.colorScheme.error,
                        fontSize = 14.sp
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                }
            }
        }
    }
}

@Composable
fun ProblemCategory(text: String, isSelected: Boolean, onClick: () -> Unit = {}) {
    Card(
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, if (isSelected) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.outlineVariant),
        colors = CardDefaults.cardColors(containerColor = if (isSelected) MaterialTheme.colorScheme.error.copy(alpha = 0.05f) else MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(0.dp),
        modifier = Modifier.clickable(onClick = onClick)
    ) {
        Row(modifier = Modifier.padding(20.dp).fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(text, fontWeight = FontWeight.Bold, color = if (isSelected) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface, modifier = Modifier.weight(1f))
            if (isSelected) {
                Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = MaterialTheme.colorScheme.error)
            }
        }
    }
}

private fun OrderDetailResponse.nextOperationalStop(): OrderStop? {
    return stops.firstOrNull { it.completedAt == null }
}

private fun SimplePoint?.toGeoPointOrNull(): GeoPoint? {
    val point = this ?: return null
    val lat = point.lat ?: return null
    val lng = point.lng ?: return null
    return GeoPoint(lat, lng)
}
