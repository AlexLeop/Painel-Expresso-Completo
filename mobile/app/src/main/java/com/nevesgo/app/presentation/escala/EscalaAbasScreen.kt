package com.nevesgo.app.presentation.escala

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import com.nevesgo.app.ui.theme.*
import androidx.compose.foundation.BorderStroke

@Composable
fun EscalaAbasScreen() {
    var selectedTabIndex by remember { mutableStateOf(0) }
    val tabs = listOf("Disponíveis", "Minhas Escalas")

    Scaffold(
        topBar = {
            Surface(color = MaterialTheme.colorScheme.surface, shadowElevation = 1.dp) {
                Column {
                    Row(
                        modifier = Modifier.fillMaxWidth().height(56.dp).padding(horizontal = 16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        IconButton(onClick = { /* TODO */ }, modifier = Modifier.size(48.dp)) {
                            Icon(Icons.Outlined.ArrowBack, contentDescription = "Voltar", tint = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Text("Escala", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary, modifier = Modifier.weight(1f))
                        
                        Box {
                            IconButton(onClick = { /* TODO */ }, modifier = Modifier.size(48.dp)) {
                                Icon(Icons.Outlined.Notifications, contentDescription = "Notificações", tint = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            Box(modifier = Modifier.align(Alignment.TopEnd).padding(top = 12.dp, end = 12.dp).size(8.dp).background(MaterialTheme.colorScheme.error, CircleShape))
                        }
                        
                        Box(modifier = Modifier.size(32.dp).background(MaterialTheme.colorScheme.outlineVariant, CircleShape).border(1.dp, MaterialTheme.colorScheme.outlineVariant, CircleShape), contentAlignment = Alignment.Center) {
                            Icon(Icons.Outlined.Person, contentDescription = null, modifier = Modifier.size(20.dp))
                        }
                    }
                    // TabRow
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
        bottomBar = { NevesGoBottomNav(activeTab = "escala") },
        modifier = Modifier.fillMaxSize()
    ) { innerPadding ->
        when (selectedTabIndex) {
            0 -> EscalaDisponiveisContent(innerPadding)
            1 -> MinhasEscalasContent(innerPadding)
        }
    }
}

@Composable
private fun EscalaDisponiveisContent(innerPadding: PaddingValues) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(innerPadding),
        contentPadding = PaddingValues(bottom = 24.dp)
    ) {
        item {
            LazyRow(
                modifier = Modifier.fillMaxWidth().padding(vertical = 16.dp),
                contentPadding = PaddingValues(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                item { DateFilterChip(text = "Hoje, 24 Mai", isSelected = true) }
                item { DateFilterChip(text = "Amanhã, 25 Mai", isSelected = false) }
                item { DateFilterChip(text = "Dom, 26 Mai", isSelected = false) }
                item { DateFilterChip(text = "Seg, 27 Mai", isSelected = false) }
            }
        }
        
        item {
            Surface(
                shape = NevesGoShapes.medium,
                color = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.1f),
                border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.secondary.copy(alpha = 0.2f)),
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(bottom = 16.dp)
            ) {
                Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        Icon(Icons.Outlined.Info, contentDescription = null, tint = MaterialTheme.colorScheme.secondary)
                        Text("12 novas vagas disponíveis para hoje", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
                    }
                    Icon(Icons.Outlined.ChevronRight, contentDescription = null, tint = MaterialTheme.colorScheme.secondary)
                }
            }
        }

        item {
            AvailableShiftCard(
                title = "Mercado Central",
                type = "SUPERMERCADO",
                address = "Av. das Nações Unidas, 12901 - Brooklin Novo, São Paulo",
                shift = "Manhã (08h - 14h)",
                valueLabel = "Garantido Mínimo",
                value = "180,00",
                icon = Icons.Outlined.Store
            )
        }
        item {
            AvailableShiftCard(
                title = "Burger King Express",
                type = "FAST FOOD",
                address = "Rua Oscar Freire, 1050 - Jardim Paulista, São Paulo",
                shift = "Noite (18h - 00h)",
                valueLabel = "Valor da Diária",
                value = "210,00",
                icon = Icons.Outlined.Restaurant
            )
        }
        item {
            AvailableShiftCard(
                title = "Droga Raia 24h",
                type = "FARMÁCIA",
                address = "Al. Rio Negro, 500 - Alphaville Industrial, Barueri",
                shift = "Madrugada (00h - 06h)",
                valueLabel = "Garantido Mínimo",
                value = "245,00",
                icon = Icons.Outlined.LocalPharmacy
            )
        }
    }
}

@Composable
private fun MinhasEscalasContent(innerPadding: PaddingValues) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(innerPadding),
        contentPadding = PaddingValues(bottom = 24.dp)
    ) {
        item {
            LazyRow(
                modifier = Modifier.fillMaxWidth().padding(vertical = 16.dp),
                contentPadding = PaddingValues(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                item { DateFilterChip(text = "Hoje, 24 Mai", isSelected = true) }
                item { DateFilterChip(text = "Amanhã, 25 Mai", isSelected = false) }
                item { DateFilterChip(text = "Dom, 26 Mai", isSelected = false) }
                item { DateFilterChip(text = "Seg, 27 Mai", isSelected = false) }
            }
        }
        
        item {
            MyShiftCard(
                title = "Mercado Central",
                address = "Rua das Flores, 123 - Centro",
                status = "Confirmado",
                statusColor = MaterialTheme.colorScheme.secondaryContainer,
                statusTextColor = MaterialTheme.colorScheme.onSecondaryContainer,
                shift = "Manhã (08h - 14h)",
                date = "Hoje",
                valueLabel = "Garantido Mínimo",
                value = "180,00",
                icon = Icons.Outlined.ShoppingCart,
                buttonText = "Detalhes"
            )
        }
        item {
            MyShiftCard(
                title = "Droga Raia 24h",
                address = "Av. Paulista, 1500 - Bela Vista",
                status = "Agendado",
                statusColor = MaterialTheme.colorScheme.surfaceContainerHigh,
                statusTextColor = MaterialTheme.colorScheme.onSurfaceVariant,
                shift = "Madrugada (00h - 06h)",
                date = "Amanhã",
                valueLabel = "Valor da Diária",
                value = "220,00",
                icon = Icons.Outlined.MedicalServices,
                buttonText = "Ver Escala"
            )
        }
    }
}

@Composable
private fun DateFilterChip(text: String, isSelected: Boolean) {
    Surface(
        shape = PillShape,
        color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceContainer,
        contentColor = if (isSelected) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant,
    ) {
        Text(text, style = MaterialTheme.typography.labelLarge, modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp))
    }
}

@Composable
private fun AvailableShiftCard(title: String, type: String, address: String, shift: String, valueLabel: String, value: String, icon: androidx.compose.ui.graphics.vector.ImageVector) {
    Surface(
        shape = NevesGoShapes.medium,
        color = MaterialTheme.colorScheme.surfaceContainerLowest,
        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f)),
        shadowElevation = 2.dp,
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Box(modifier = Modifier.size(48.dp).background(MaterialTheme.colorScheme.surfaceContainerHigh, NevesGoShapes.small), contentAlignment = Alignment.Center) {
                        Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(24.dp))
                    }
                    Column {
                        Text(title, style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary)
                        Surface(shape = PillShape, color = MaterialTheme.colorScheme.tertiaryContainer.copy(alpha = 0.1f), modifier = Modifier.padding(top = 4.dp)) {
                            Text(type, style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.1.em), color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp))
                        }
                    }
                }
                Icon(Icons.Outlined.BookmarkBorder, contentDescription = "Salvar", tint = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            
            Column(modifier = Modifier.padding(vertical = 16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Outlined.LocationOn, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(20.dp))
                    Text(address, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Outlined.Schedule, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(20.dp))
                    Text("Turno: ", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurface)
                    Text(shift, style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurface)
                }
            }
            
            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f), modifier = Modifier.padding(bottom = 12.dp))
            
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Bottom) {
                Column {
                    Text(valueLabel, style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.1.em), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text("R$ $value", style = MaterialTheme.typography.headlineLarge, color = MaterialTheme.colorScheme.secondary)
                }
            }
            
            OutlinedButton(
                onClick = { /* TODO */ },
                modifier = Modifier.fillMaxWidth().padding(top = 24.dp).height(48.dp),
                shape = NevesGoShapes.medium,
                border = androidx.compose.foundation.BorderStroke(2.dp, MaterialTheme.colorScheme.primary),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.primary)
            ) {
                Text("Ver Detalhes", style = MaterialTheme.typography.labelLarge)
            }
        }
    }
}

@Composable
private fun MyShiftCard(title: String, address: String, status: String, statusColor: Color, statusTextColor: Color, shift: String, date: String, valueLabel: String, value: String, icon: androidx.compose.ui.graphics.vector.ImageVector, buttonText: String) {
    Surface(
        shape = NevesGoShapes.medium,
        color = MaterialTheme.colorScheme.surfaceContainerLowest,
        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f)),
        shadowElevation = 2.dp,
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.weight(1f)) {
                    Box(modifier = Modifier.size(48.dp).background(MaterialTheme.colorScheme.surfaceContainer, NevesGoShapes.small), contentAlignment = Alignment.Center) {
                        Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(24.dp))
                    }
                    Column {
                        Text(title, style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.onSurface)
                        Text(address, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                Surface(shape = PillShape, color = statusColor) {
                    Text(status, style = MaterialTheme.typography.labelSmall, color = statusTextColor, modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp))
                }
            }
            
            Row(modifier = Modifier.fillMaxWidth().padding(vertical = 12.dp), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.weight(1f)) {
                    Icon(Icons.Outlined.Schedule, contentDescription = null, tint = MaterialTheme.colorScheme.outline, modifier = Modifier.size(18.dp))
                    Column {
                        Text("TURNO", style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp, fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(shift, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurface)
                    }
                }
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.weight(1f)) {
                    Icon(Icons.Outlined.CalendarToday, contentDescription = null, tint = MaterialTheme.colorScheme.outline, modifier = Modifier.size(18.dp))
                    Column {
                        Text("DATA", style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp, fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(date, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurface)
                    }
                }
            }
            
            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.2f), modifier = Modifier.padding(bottom = 12.dp))
            
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column {
                    Text(valueLabel, style = MaterialTheme.typography.labelSmall.copy(fontSize = 11.sp), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text("R$ $value", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.secondary)
                }
                Button(
                    onClick = { /* TODO */ },
                    shape = NevesGoShapes.medium,
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh, contentColor = MaterialTheme.colorScheme.onSurface),
                    modifier = Modifier.defaultMinSize(minWidth = 100.dp).height(48.dp)
                ) {
                    Text(buttonText, style = MaterialTheme.typography.labelLarge)
                }
            }
        }
    }
}
