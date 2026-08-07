package com.nevesgo.app.presentation.escala

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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nevesgo.app.ui.theme.*
import androidx.compose.ui.unit.em
import androidx.compose.foundation.BorderStroke

enum class EscalaDetalhesUiState {
    Disponivel, Aceita
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DetalhesEscalaScreen(uiState: EscalaDetalhesUiState = EscalaDetalhesUiState.Disponivel) {
    var showCancelSheet by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            Surface(color = MaterialTheme.colorScheme.surface, shadowElevation = 1.dp) {
                Row(
                    modifier = Modifier.fillMaxWidth().height(64.dp).padding(horizontal = 16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconButton(onClick = { /* TODO */ }, modifier = Modifier.size(40.dp)) {
                        Icon(Icons.Outlined.ArrowBack, contentDescription = "Voltar", tint = MaterialTheme.colorScheme.primary)
                    }
                    if (uiState == EscalaDetalhesUiState.Disponivel) {
                        Text("Detalhes da Vaga", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary, modifier = Modifier.weight(1f).padding(start = 16.dp))
                        Text("Velocity Logistics", style = MaterialTheme.typography.headlineLarge.copy(fontSize = 18.sp), color = OnPrimaryFixed)
                    } else {
                        Text("Detalhes da Escala", style = MaterialTheme.typography.headlineLarge.copy(fontSize = 24.sp), color = OnPrimaryFixed, modifier = Modifier.weight(1f).padding(start = 16.dp))
                        IconButton(onClick = { /* TODO */ }) {
                            Icon(Icons.Outlined.Notifications, contentDescription = "Notificações", tint = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        },
        bottomBar = {
            Column {
                Surface(
                    color = MaterialTheme.colorScheme.surface.copy(alpha = 0.9f),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Box(modifier = Modifier.padding(16.dp)) {
                        if (uiState == EscalaDetalhesUiState.Disponivel) {
                            Button(
                                onClick = { /* TODO: Change to Aceita */ },
                                modifier = Modifier.fillMaxWidth().height(56.dp),
                                shape = NevesGoShapes.medium,
                                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary, contentColor = MaterialTheme.colorScheme.onSecondary)
                            ) {
                                Row(horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                                    Text("Aceitar Escala", style = MaterialTheme.typography.headlineMedium)
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Icon(Icons.Outlined.Bolt, contentDescription = null, modifier = Modifier.size(24.dp))
                                }
                            }
                        } else {
                            OutlinedButton(
                                onClick = { showCancelSheet = true },
                                modifier = Modifier.fillMaxWidth().height(56.dp),
                                shape = NevesGoShapes.medium,
                                border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.error),
                                colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error)
                            ) {
                                Row(horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Outlined.Cancel, contentDescription = null, modifier = Modifier.size(24.dp))
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text("Desistir da Escala", style = MaterialTheme.typography.headlineMedium)
                                }
                            }
                        }
                    }
                }
                NevesGoBottomNav(activeTab = "escala")
            }
        },
        modifier = Modifier.fillMaxSize()
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.background)
                .padding(innerPadding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(24.dp)
        ) {
            if (uiState == EscalaDetalhesUiState.Aceita) {
                item {
                    Surface(color = MaterialTheme.colorScheme.secondaryContainer, contentColor = MaterialTheme.colorScheme.onSecondaryContainer, modifier = Modifier.fillMaxWidth()) {
                        Row(modifier = Modifier.padding(horizontal = 16.dp, vertical = 16.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            Box(modifier = Modifier.size(24.dp).background(MaterialTheme.colorScheme.onSecondaryContainer, CircleShape), contentAlignment = Alignment.Center) {
                                Icon(Icons.Outlined.Check, contentDescription = null, tint = MaterialTheme.colorScheme.secondaryContainer, modifier = Modifier.size(16.dp))
                            }
                            Text("Sua presença está confirmada nesta escala", style = MaterialTheme.typography.labelLarge)
                        }
                    }
                }
            }

            // Hero Section
            item {
                Surface(
                    shape = NevesGoShapes.medium,
                    color = MaterialTheme.colorScheme.surfaceContainerLowest,
                    border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f)),
                    shadowElevation = 2.dp,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(modifier = Modifier.padding(20.dp), horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.Top) {
                        if (uiState == EscalaDetalhesUiState.Disponivel) {
                            Box(modifier = Modifier.size(64.dp).background(MaterialTheme.colorScheme.surfaceContainer, NevesGoShapes.small), contentAlignment = Alignment.Center) {
                                Icon(Icons.Outlined.Store, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(32.dp))
                            }
                        }
                        Column(modifier = Modifier.weight(1f)) {
                            Text("Mercado Central", style = MaterialTheme.typography.headlineLarge, color = MaterialTheme.colorScheme.primary)
                            if (uiState == EscalaDetalhesUiState.Aceita) {
                                Text("Hub de Distribuição Urbana • Setor 04", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(top = 8.dp)) {
                                Icon(Icons.Outlined.LocationOn, contentDescription = null, tint = MaterialTheme.colorScheme.secondary, modifier = Modifier.size(18.dp))
                                Text("Rua Haddock Lobo, 1234 - Jardins, São Paulo", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                        if (uiState == EscalaDetalhesUiState.Aceita) {
                            Surface(shape = PillShape, color = MaterialTheme.colorScheme.surfaceContainerHighest, contentColor = MaterialTheme.colorScheme.onSurface) {
                                Row(modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                    Icon(Icons.Outlined.Timer, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Text("Confirmado", style = MaterialTheme.typography.labelSmall)
                                }
                            }
                        }
                    }
                }
            }

            if (uiState == EscalaDetalhesUiState.Aceita) {
                // Map View
                item {
                    Box(
                        modifier = Modifier.fillMaxWidth().aspectRatio(16f/9f).background(MaterialTheme.colorScheme.surfaceContainerHighest, NevesGoShapes.medium).border(1.dp, MaterialTheme.colorScheme.outlineVariant, NevesGoShapes.medium),
                        contentAlignment = Alignment.BottomEnd
                    ) {
                        Box(modifier = Modifier.padding(16.dp).size(48.dp).background(MaterialTheme.colorScheme.primary, CircleShape), contentAlignment = Alignment.Center) {
                            Icon(Icons.Outlined.MyLocation, contentDescription = null, tint = MaterialTheme.colorScheme.onPrimary)
                        }
                    }
                }
            }

            // Financials Bento Grid
            item {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Surface(shape = NevesGoShapes.medium, color = if (uiState == EscalaDetalhesUiState.Disponivel) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.surfaceContainerLow, contentColor = if (uiState == EscalaDetalhesUiState.Disponivel) MaterialTheme.colorScheme.onSecondary else MaterialTheme.colorScheme.onSurface, shadowElevation = 2.dp, modifier = Modifier.weight(1f).height(128.dp)) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.SpaceBetween) {
                            Text("VALOR DA DIÁRIA", style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp), color = if (uiState == EscalaDetalhesUiState.Disponivel) MaterialTheme.colorScheme.onSecondary.copy(alpha = 0.9f) else MaterialTheme.colorScheme.onSurfaceVariant)
                            Column {
                                Text("R$ 180,00", style = MaterialTheme.typography.headlineLarge, color = if (uiState == EscalaDetalhesUiState.Disponivel) MaterialTheme.colorScheme.onSecondary else MaterialTheme.colorScheme.secondary)
                                if (uiState == EscalaDetalhesUiState.Disponivel) {
                                    Text("Garantido Mínimo", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSecondary.copy(alpha = 0.8f))
                                }
                            }
                        }
                    }
                    Surface(shape = NevesGoShapes.medium, color = MaterialTheme.colorScheme.surfaceContainerLow, border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f)), modifier = Modifier.weight(1f).height(128.dp)) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.SpaceBetween) {
                            Text("TAXAS POR ENTREGA", style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp), color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Text("Até 5km", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    Text("R$ 6,00", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.secondary)
                                }
                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Text("Até 9km", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    Text("R$ 8,00", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.secondary)
                                }
                                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.2f), modifier = Modifier.padding(vertical = 4.dp))
                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Text("EXCEDENTE", style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp), color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    Text("+ R$ 1/km", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.secondary)
                                }
                            }
                        }
                    }
                }
            }

            // Logistics Info / Turno
            item {
                Surface(
                    shape = NevesGoShapes.medium,
                    color = MaterialTheme.colorScheme.surfaceContainerLowest,
                    border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                    shadowElevation = 2.dp,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(24.dp)) {
                        // Turno/Duração
                        Column {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(bottom = 12.dp)) {
                                Icon(Icons.Outlined.CalendarToday, contentDescription = null, modifier = Modifier.size(20.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text("TURNO E DURAÇÃO", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                    Text("Hoje, 24 de Maio", style = MaterialTheme.typography.bodyLarge)
                                    Text("08:00 — 14:00 (6h total)", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        }
                        
                        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f))
                        
                        // Requisitos
                        Column {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(bottom = 12.dp)) {
                                Icon(Icons.Outlined.Rule, contentDescription = null, modifier = Modifier.size(20.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text("REQUISITOS", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            if (uiState == EscalaDetalhesUiState.Disponivel) {
                                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    RequirementItem(text = "Possuir baú térmico ou caixa rígida")
                                    RequirementItem(text = "Celular com bateria carregada (mín. 80%)")
                                }
                            } else {
                                @OptIn(ExperimentalLayoutApi::class)
                                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    InfoChip(text = "Moto Elétrica/Combustão", icon = Icons.Outlined.ElectricMoped)
                                    InfoChip(text = "Bauleto 45L", icon = Icons.Outlined.Inventory2)
                                }
                            }
                        }
                        
                        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f))
                        
                        // Descrição
                        Column {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(bottom = 12.dp)) {
                                Icon(Icons.Outlined.Description, contentDescription = null, modifier = Modifier.size(20.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text("DESCRIÇÃO DAS ATIVIDADES", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            Text(
                                "Operação de entregas de última milha (last-mile) para pedidos de mercado. O courier será responsável pela coleta no Hub Mercado Central e distribuição em um raio de até 8km. Fluxo contínuo de pedidos com roteirização inteligente via app. Requer agilidade no manuseio de sacolas e itens frágeis.",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            }

            if (uiState == EscalaDetalhesUiState.Disponivel) {
                // Map View Placeholder for Disponivel
                item {
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Icon(Icons.Outlined.Map, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                                Text("Localização", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary)
                            }
                            Text("Ver no Google Maps", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.secondary)
                        }
                        Box(
                            modifier = Modifier.fillMaxWidth().height(192.dp).background(MaterialTheme.colorScheme.surfaceContainerHighest, NevesGoShapes.medium).border(1.dp, MaterialTheme.colorScheme.outlineVariant, NevesGoShapes.medium),
                            contentAlignment = Alignment.Center
                        ) {
                            Box(modifier = Modifier.size(40.dp).background(MaterialTheme.colorScheme.primary, CircleShape), contentAlignment = Alignment.Center) {
                                Icon(Icons.Outlined.LocationOn, contentDescription = null, tint = Color.White)
                            }
                        }
                    }
                }
            } else {
                // Warning Callout
                item {
                    Surface(
                        shape = NevesGoShapes.medium,
                        color = MaterialTheme.colorScheme.errorContainer,
                        contentColor = MaterialTheme.colorScheme.onErrorContainer,
                        modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp)
                    ) {
                        Row(modifier = Modifier.padding(16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Top) {
                            Icon(Icons.Outlined.Warning, contentDescription = null)
                            Text("O cancelamento desta escala com menos de 2h de antecedência poderá impactar seu Score de Confiabilidade.", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold))
                        }
                    }
                }
            }
        }
    }

    if (showCancelSheet) {
        androidx.compose.ui.window.Dialog(onDismissRequest = { showCancelSheet = false }) {
            Surface(
                shape = NevesGoShapes.medium,
                color = MaterialTheme.colorScheme.surfaceContainerLowest,
                modifier = Modifier.fillMaxWidth().padding(16.dp)
            ) {
                Column(
                    modifier = Modifier.padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(24.dp)
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                        Text("Desistir desta escala?", style = MaterialTheme.typography.headlineLarge, color = MaterialTheme.colorScheme.onSurface, textAlign = TextAlign.Center)
                        Text("Esta ação não pode ser desfeita após a confirmação.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center, modifier = Modifier.padding(top = 8.dp))
                    }

                    Surface(
                        shape = NevesGoShapes.small,
                        color = MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.2f),
                        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.error.copy(alpha = 0.2f)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(modifier = Modifier.padding(16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Top) {
                            Icon(Icons.Outlined.ReportProblem, contentDescription = null, tint = MaterialTheme.colorScheme.error)
                            Text("O cancelamento com menos de 2h de antecedência impactará seu Score de Confiabilidade.", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onErrorContainer)
                        }
                    }

                    Column(verticalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
                        Button(
                            onClick = { showCancelSheet = false },
                            modifier = Modifier.fillMaxWidth().height(56.dp),
                            shape = NevesGoShapes.medium,
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary, contentColor = MaterialTheme.colorScheme.onSecondary)
                        ) {
                            Row(horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Outlined.CheckCircle, contentDescription = null, modifier = Modifier.size(24.dp))
                                Spacer(modifier = Modifier.width(8.dp))
                                Text("Manter Escala", style = MaterialTheme.typography.headlineMedium)
                            }
                        }
                        OutlinedButton(
                            onClick = { showCancelSheet = false; /* TODO: Execute cancel */ },
                            modifier = Modifier.fillMaxWidth().height(56.dp),
                            shape = NevesGoShapes.medium,
                            border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.error.copy(alpha = 0.3f)),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error)
                        ) {
                            Text("Confirmar Desistência", style = MaterialTheme.typography.labelLarge)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun RequirementItem(text: String) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Icon(Icons.Outlined.CheckCircle, contentDescription = null, tint = MaterialTheme.colorScheme.secondary)
        Text(text, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface)
    }
}

@Composable
private fun InfoChip(text: String, icon: androidx.compose.ui.graphics.vector.ImageVector) {
    Surface(shape = PillShape, color = MaterialTheme.colorScheme.surfaceContainerHigh, contentColor = MaterialTheme.colorScheme.onSurface) {
        Row(modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            Icon(icon, contentDescription = null, modifier = Modifier.size(16.dp))
            Text(text, style = MaterialTheme.typography.labelSmall)
        }
    }
}
