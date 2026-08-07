package com.nevesgo.app.presentation.entregas

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import com.nevesgo.app.ui.theme.*
import androidx.compose.foundation.BorderStroke

@Composable
fun MinhasEntregasScreen() {
    var selectedTabIndex by remember { mutableStateOf(0) }
    val tabs = listOf("Em curso", "Em espera", "Agendadas")

    Scaffold(
        topBar = {
            Surface(color = MaterialTheme.colorScheme.surface, shadowElevation = 1.dp) {
                Column {
                    Row(
                        modifier = Modifier.fillMaxWidth().height(56.dp).padding(horizontal = 16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        IconButton(onClick = { /* TODO */ }, modifier = Modifier.size(48.dp)) {
                            Icon(Icons.Outlined.ArrowBack, contentDescription = "Voltar", tint = MaterialTheme.colorScheme.primary)
                        }
                        Text("Entregas", style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.primary, modifier = Modifier.weight(1f))
                        IconButton(onClick = { /* TODO */ }, modifier = Modifier.size(48.dp)) {
                            Icon(Icons.Outlined.Search, contentDescription = "Pesquisar", tint = MaterialTheme.colorScheme.primary)
                        }
                        Box(modifier = Modifier.size(32.dp).background(MaterialTheme.colorScheme.outlineVariant, CircleShape).border(1.dp, MaterialTheme.colorScheme.outlineVariant, CircleShape), contentAlignment = Alignment.Center) {
                            Icon(Icons.Outlined.Person, contentDescription = null, modifier = Modifier.size(20.dp))
                        }
                    }
                    // TabRow for switching
                    TabRow(
                        selectedTabIndex = selectedTabIndex,
                        containerColor = MaterialTheme.colorScheme.surface,
                        contentColor = MaterialTheme.colorScheme.primary,
                        divider = { HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f)) }
                    ) {
                        tabs.forEachIndexed { index, title ->
                            Tab(
                                selected = selectedTabIndex == index,
                                onClick = { selectedTabIndex = index },
                                text = { Text(title, style = MaterialTheme.typography.labelLarge) },
                                unselectedContentColor = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            }
        },
        bottomBar = { NevesGoBottomNav(activeTab = "entregas") },
        modifier = Modifier.fillMaxSize()
    ) { innerPadding ->
        when (selectedTabIndex) {
            0 -> EmCursoContent(innerPadding)
            1 -> EmEsperaContent(innerPadding)
            2 -> AgendadasContent(innerPadding)
        }
    }
}

@Composable
private fun EmCursoContent(innerPadding: PaddingValues) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(innerPadding),
        contentPadding = PaddingValues(bottom = 24.dp)
    ) {
        item {
            Text("ENTREGA ATUAL", style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.05.em), color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(start = 16.dp, top = 16.dp, bottom = 8.dp))
        }
        item {
            OrderInProgressCard(
                orderNumber = "#8842",
                address = "Rua das Flores, 123 - Centro",
                price = "18,50",
                distance = "5.2 km",
                eta = "14:45 (8 min)"
            )
        }
        item {
            OrderInProgressCard(
                orderNumber = "#8843",
                address = "Av. Paulista, 1500 - Bela Vista",
                price = "12,20",
                distance = "2.8 km",
                eta = "15:10 (25 min)"
            )
        }
        item {
            Text("HISTÓRICO RECENTE", style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.05.em), color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(start = 16.dp, top = 24.dp, bottom = 8.dp))
        }
        item {
            Surface(
                shape = NevesGoShapes.medium,
                color = MaterialTheme.colorScheme.surfaceContainerLow,
                border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f)),
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp)
            ) {
                Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    Box(modifier = Modifier.size(40.dp).background(MaterialTheme.colorScheme.surfaceContainerHighest, CircleShape), contentAlignment = Alignment.Center) {
                        Icon(Icons.Outlined.CheckCircle, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Text("Pedido #8839", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurface)
                        Text("Entregue há 25 min", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Text("R$ 12,50", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.secondary)
                }
            }
        }
    }
}

@Composable
private fun EmEsperaContent(innerPadding: PaddingValues) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.surface)
            .padding(innerPadding),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Surface(
                shape = NevesGoShapes.medium,
                color = MaterialTheme.colorScheme.primaryContainer,
                contentColor = MaterialTheme.colorScheme.onPrimaryContainer,
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(modifier = Modifier.padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Column {
                        Text("AGUARDANDO COLETA", style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.05.em), color = Color.White.copy(alpha = 0.8f))
                        Text("4 Pedidos", style = MaterialTheme.typography.headlineLarge, color = Color.White)
                    }
                    Icon(Icons.Outlined.HourglassTop, contentDescription = null, tint = Color.White.copy(alpha = 0.2f), modifier = Modifier.size(40.dp))
                }
            }
        }

        item {
            Text("LISTA DE ESPERA", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }

        item {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.surfaceContainerHighest.copy(alpha = 0.3f), NevesGoShapes.medium)
                    .border(2.dp, MaterialTheme.colorScheme.outlineVariant, NevesGoShapes.medium)
                    .padding(16.dp),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Outlined.Radar, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(32.dp))
                    Text("Buscando novas ofertas...", style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurface)
                    Text("Fique nesta tela para receber pedidos prioritários na sua região.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center)
                }
            }
        }

        item { WaitingOrderCard(orderNumber = "#8845", price = "22,50", distance = "3.2 km", opacity = 1f) }
        item { WaitingOrderCard(orderNumber = "#8912", price = "15,20", distance = "1.8 km", opacity = 0.9f) }
        item { WaitingOrderCard(orderNumber = "#8950", price = "18,90", distance = "2.5 km", opacity = 0.8f) }
    }
}

@Composable
private fun AgendadasContent(innerPadding: PaddingValues) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(innerPadding),
        contentPadding = PaddingValues(bottom = 80.dp)
    ) {
        item {
            Column(modifier = Modifier.padding(16.dp).padding(top = 8.dp)) {
                Text("Entregas Agendadas", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(bottom = 4.dp))
                Text("Gerencie suas próximas rotas reservadas", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        item {
            ScheduledDeliveryCard(
                orderNumber = "#9120",
                dateText = "Hoje, 18:30",
                price = "42,50",
                pickup = "Restaurante Gourmet Central - Av. Paulista, 1000",
                dropoff = "Condomínio Sky View - R. Augusta, 2500",
                distance = "8.4 km total",
                info = "Médio (2 itens)",
                infoIcon = Icons.Outlined.Inventory2
            )
        }
        item {
            ScheduledDeliveryCard(
                orderNumber = "#9245",
                dateText = "Amanhã, 09:00",
                price = "115,00",
                pickup = "Distribuidora LogiX - Via Anhanguera, KM 18",
                dropoff = "Multi-pontos (4 paradas) - Setor Sul",
                distance = "32.1 km total",
                info = "Alta Prioridade",
                infoIcon = Icons.Outlined.Stars,
                infoColor = MaterialTheme.colorScheme.secondary
            )
        }
        item {
            Box(modifier = Modifier.fillMaxWidth().padding(32.dp).padding(top = 16.dp), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.alpha(0.6f)) {
                    Icon(Icons.Outlined.EventAvailable, contentDescription = null, modifier = Modifier.size(48.dp).padding(bottom = 16.dp), tint = MaterialTheme.colorScheme.outlineVariant)
                    Text("Não há mais agendamentos para esta semana. Explore as outras abas para garantir mais lucros!", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center)
                }
            }
        }
    }
}

@Composable
private fun OrderInProgressCard(orderNumber: String, address: String, price: String, distance: String, eta: String) {
    Surface(
        shape = NevesGoShapes.medium,
        color = MaterialTheme.colorScheme.surfaceContainerLowest,
        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f)),
        shadowElevation = 2.dp,
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                Column(modifier = Modifier.weight(1f)) {
                    Surface(shape = PillShape, color = MaterialTheme.colorScheme.secondaryContainer, contentColor = MaterialTheme.colorScheme.onSecondaryContainer) {
                        Text("Entregando", style = MaterialTheme.typography.labelSmall, modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp))
                    }
                    Text("Pedido $orderNumber", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.onSurface, modifier = Modifier.padding(top = 8.dp, bottom = 4.dp))
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Icon(Icons.Outlined.LocationOn, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(16.dp))
                        Text(address, style = MaterialTheme.typography.bodyMedium.copy(fontSize = 14.sp), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text("R$ $price", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.secondary)
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp), modifier = Modifier.padding(top = 4.dp)) {
                        Icon(Icons.Outlined.DirectionsCar, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(16.dp))
                        Text(distance, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f), modifier = Modifier.padding(vertical = 12.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column {
                    Text("Estimativa de chegada", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(eta, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurface)
                }
                Button(
                    onClick = { /* TODO */ },
                    shape = NevesGoShapes.medium,
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary, contentColor = MaterialTheme.colorScheme.onPrimary),
                    modifier = Modifier.defaultMinSize(minWidth = 120.dp).height(40.dp)
                ) {
                    Text("Ver Rota", style = MaterialTheme.typography.labelLarge)
                }
            }
        }
    }
}

@Composable
private fun WaitingOrderCard(orderNumber: String, price: String, distance: String, opacity: Float) {
    Surface(
        shape = NevesGoShapes.medium,
        color = MaterialTheme.colorScheme.surfaceContainerLowest,
        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.surfaceVariant),
        shadowElevation = 2.dp,
        modifier = Modifier.fillMaxWidth().alpha(opacity)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                Surface(shape = PillShape, color = TertiaryFixed, contentColor = OnTertiaryFixed) {
                    Row(modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        Icon(Icons.Outlined.PauseCircle, contentDescription = null, modifier = Modifier.size(14.dp))
                        Text("Em espera", style = MaterialTheme.typography.labelSmall)
                    }
                }
                Text("R$ $price", style = DataMono, color = MaterialTheme.colorScheme.secondary)
            }
            Text("Pedido $orderNumber", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(bottom = 8.dp))
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(bottom = 16.dp)) {
                Icon(Icons.Outlined.DirectionsCar, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(18.dp))
                Text("$distance do local atual", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Row(modifier = Modifier.fillMaxWidth().padding(bottom = 24.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(top = 4.dp)) {
                    Box(modifier = Modifier.size(8.dp).background(MaterialTheme.colorScheme.secondary, CircleShape))
                    Box(modifier = Modifier.width(1.dp).height(32.dp).background(MaterialTheme.colorScheme.outlineVariant))
                    Box(modifier = Modifier.size(8.dp).background(Color.Transparent, CircleShape).border(2.dp, MaterialTheme.colorScheme.primary, CircleShape))
                }
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Column {
                        Text("Coleta", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("Restaurante Gourmet Plaza, Av. Paulista, 1000", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface)
                    }
                    Column {
                        Text("Entrega", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("Rua Bela Cintra, 450 - Apto 12", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface)
                    }
                }
            }
            Button(
                onClick = { /* TODO */ },
                modifier = Modifier.fillMaxWidth().height(56.dp),
                shape = NevesGoShapes.medium,
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary, contentColor = MaterialTheme.colorScheme.onPrimary)
            ) {
                Text("Aceitar", style = MaterialTheme.typography.labelLarge)
            }
        }
    }
}

@Composable
private fun ScheduledDeliveryCard(orderNumber: String, dateText: String, price: String, pickup: String, dropoff: String, distance: String, info: String, infoIcon: androidx.compose.ui.graphics.vector.ImageVector, infoColor: Color = MaterialTheme.colorScheme.onSurfaceVariant) {
    Surface(
        shape = NevesGoShapes.medium,
        color = MaterialTheme.colorScheme.surfaceContainerLowest,
        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        shadowElevation = 2.dp,
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                Column {
                    Text(orderNumber, style = DataMono, color = MaterialTheme.colorScheme.primary)
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp), modifier = Modifier.padding(top = 4.dp)) {
                        Icon(Icons.Outlined.Event, contentDescription = null, tint = if(dateText.contains("Hoje")) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(20.dp))
                        Text(dateText, style = MaterialTheme.typography.headlineMedium, color = if(dateText.contains("Hoje")) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                Column(horizontalAlignment = Alignment.End) {
                    Surface(shape = NevesGoShapes.small, color = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.2f)) {
                        Text("R$ $price", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.secondary, modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp))
                    }
                    Text("Valor da Entrega", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(top = 4.dp))
                }
            }
            Row(modifier = Modifier.fillMaxWidth().padding(bottom = 24.dp)) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(top = 4.dp, end = 16.dp)) {
                    Box(modifier = Modifier.size(16.dp).background(MaterialTheme.colorScheme.primary, CircleShape).border(4.dp, MaterialTheme.colorScheme.surfaceContainerLowest, CircleShape))
                    Box(modifier = Modifier.width(2.dp).height(48.dp).background(MaterialTheme.colorScheme.outlineVariant))
                    Box(modifier = Modifier.size(16.dp).background(MaterialTheme.colorScheme.secondary, CircleShape).border(4.dp, MaterialTheme.colorScheme.surfaceContainerLowest, CircleShape))
                }
                Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    Column {
                        Text("COLETA", style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.05.em), color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(pickup, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary, maxLines = 1, overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis)
                    }
                    Column {
                        Text("ENTREGA", style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.05.em), color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(dropoff, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary, maxLines = 1, overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis)
                    }
                }
            }
            Row(modifier = Modifier.fillMaxWidth().padding(bottom = 24.dp), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    Icon(Icons.Outlined.Route, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(18.dp))
                    Text(distance, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    Icon(infoIcon, contentDescription = null, tint = infoColor, modifier = Modifier.size(18.dp))
                    Text(info, style = MaterialTheme.typography.labelLarge, color = infoColor)
                }
            }
            Button(
                onClick = { /* TODO */ },
                modifier = Modifier.fillMaxWidth().height(48.dp),
                shape = NevesGoShapes.medium,
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary, contentColor = MaterialTheme.colorScheme.onPrimary)
            ) {
                Text("Ver Detalhes", style = MaterialTheme.typography.labelLarge)
            }
        }
    }
}
