package com.nevesgo.app.presentation.entregas

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
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
fun DetalhesDoAgendamentoScreen() {
    Scaffold(
        topBar = {
            Surface(color = MaterialTheme.colorScheme.surface, border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)) {
                Row(
                    modifier = Modifier.fillMaxWidth().height(56.dp).padding(horizontal = 16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconButton(onClick = { /* TODO */ }, modifier = Modifier.size(48.dp)) {
                        Icon(Icons.Outlined.ArrowBack, contentDescription = "Voltar", tint = MaterialTheme.colorScheme.primary)
                    }
                    Text("Detalhes do Agendamento", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary)
                }
            }
        },
        bottomBar = { NevesGoBottomNav(activeTab = "entregas") },
        modifier = Modifier.fillMaxSize()
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.background)
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
        ) {
            // Map Preview Section
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(256.dp)
                    .background(MaterialTheme.colorScheme.surfaceContainerHighest)
            ) {
                // Placeholder for Map, using color
                
                Surface(
                    shape = NevesGoShapes.medium,
                    color = MaterialTheme.colorScheme.primary,
                    contentColor = MaterialTheme.colorScheme.onPrimary,
                    shadowElevation = 8.dp,
                    modifier = Modifier.align(Alignment.BottomEnd).padding(16.dp).size(48.dp),
                    onClick = { /* TODO */ }
                ) {
                    Box(contentAlignment = Alignment.Center) { Icon(Icons.Outlined.MyLocation, contentDescription = null) }
                }
            }

            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                // Status Card
                Surface(
                    shape = NevesGoShapes.medium,
                    color = MaterialTheme.colorScheme.surfaceContainerLowest,
                    border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                    shadowElevation = 2.dp,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(modifier = Modifier.padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Column {
                            Text("PEDIDO", style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.05.em), color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("#9120", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Surface(shape = PillShape, color = MaterialTheme.colorScheme.surfaceContainer, modifier = Modifier.padding(bottom = 4.dp)) {
                                Row(modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                    Icon(Icons.Outlined.CalendarToday, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(18.dp))
                                    Text("Hoje, 18:30", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
                                }
                            }
                            Text("AGENDADO", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.secondary)
                        }
                    }
                }

                // Financial Summary
                Surface(
                    shape = NevesGoShapes.medium,
                    color = MaterialTheme.colorScheme.primaryContainer,
                    contentColor = MaterialTheme.colorScheme.onPrimary,
                    shadowElevation = 8.dp,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(modifier = Modifier.padding(20.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            Box(modifier = Modifier.background(OnPrimaryFixedVariant, NevesGoShapes.small).padding(8.dp)) {
                                Icon(Icons.Outlined.Payments, contentDescription = null, tint = Color.White)
                            }
                            Text("Valor da Entrega", style = MaterialTheme.typography.bodyLarge)
                        }
                        Text("R$ 42,50", style = MaterialTheme.typography.headlineMedium, color = Color.White)
                    }
                }

                // Route Details
                Surface(
                    shape = NevesGoShapes.medium,
                    color = MaterialTheme.colorScheme.surfaceContainerLow,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(20.dp)) {
                        Row(modifier = Modifier.fillMaxWidth().padding(bottom = 24.dp)) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(end = 16.dp)) {
                                Box(modifier = Modifier.size(24.dp).background(MaterialTheme.colorScheme.surfaceContainerLow, CircleShape), contentAlignment = Alignment.Center) {
                                    Icon(Icons.Outlined.RadioButtonChecked, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(24.dp))
                                }
                                Box(modifier = Modifier.width(2.dp).height(48.dp).background(MaterialTheme.colorScheme.outlineVariant)) // Needs dashed
                            }
                            Column {
                                Text("RETIRADA", style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.05.em), color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text("Restaurante Gourmet Central", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary)
                                Text("Av. Paulista, 1000", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                        Row(modifier = Modifier.fillMaxWidth().padding(bottom = 24.dp)) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(end = 16.dp)) {
                                Box(modifier = Modifier.size(24.dp).background(MaterialTheme.colorScheme.surfaceContainerLow, CircleShape), contentAlignment = Alignment.Center) {
                                    Icon(Icons.Outlined.LocationOn, contentDescription = null, tint = MaterialTheme.colorScheme.secondary, modifier = Modifier.size(24.dp))
                                }
                            }
                            Column {
                                Text("ENTREGA", style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.05.em), color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text("Condominio Sky View", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary)
                                Text("R. Augusta, 2500", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                        
                        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant, modifier = Modifier.padding(bottom = 16.dp))
                        
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.weight(1f)) {
                                Icon(Icons.Outlined.Route, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                                Column {
                                    Text("Distância", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    Text("8.4 km total", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurface)
                                }
                            }
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.weight(1f)) {
                                Icon(Icons.Outlined.Schedule, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                                Column {
                                    Text("Tempo Est.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    Text("25 min", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurface)
                                }
                            }
                        }
                    }
                }

                // Package & Requirements Bento Grid
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Surface(shape = NevesGoShapes.medium, color = MaterialTheme.colorScheme.surfaceContainerHighest, modifier = Modifier.weight(1f)) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Icon(Icons.Outlined.Inventory2, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                            Text("Volume", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("Médio • 2 itens", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurface)
                        }
                    }
                    Surface(shape = NevesGoShapes.medium, color = MaterialTheme.colorScheme.surfaceContainerHighest, modifier = Modifier.weight(1f)) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Icon(Icons.Outlined.FitnessCenter, contentDescription = null, tint = MaterialTheme.colorScheme.primary) // Using FitnessCenter as Weight icon
                            Text("Peso", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("3kg (aprox.)", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurface)
                        }
                    }
                }

                Surface(
                    shape = NevesGoShapes.medium,
                    color = MaterialTheme.colorScheme.errorContainer,
                    contentColor = MaterialTheme.colorScheme.onErrorContainer,
                    border = androidx.compose.foundation.BorderStroke(1.dp, SecondaryFixed),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Icon(Icons.Outlined.Warning, contentDescription = null, modifier = Modifier.size(20.dp))
                            Text("Requisitos da Entrega", style = MaterialTheme.typography.labelLarge)
                        }
                        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Icon(Icons.Outlined.CheckCircle, contentDescription = null, modifier = Modifier.size(16.dp))
                                Text("Necessário baú térmico", style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Medium))
                            }
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Icon(Icons.Outlined.CheckCircle, contentDescription = null, modifier = Modifier.size(16.dp))
                                Text("Identificação na portaria", style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Medium))
                            }
                        }
                    }
                }

                // Action Area
                Column(modifier = Modifier.fillMaxWidth().padding(vertical = 24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Button(
                        onClick = { /* TODO */ },
                        modifier = Modifier.fillMaxWidth().height(56.dp),
                        shape = NevesGoShapes.medium,
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary, contentColor = MaterialTheme.colorScheme.onSecondary),
                        elevation = ButtonDefaults.buttonElevation(defaultElevation = 4.dp)
                    ) {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Outlined.Map, contentDescription = null)
                            Text("Ver no Mapa", style = MaterialTheme.typography.headlineMedium)
                        }
                    }
                    Button(
                        onClick = { /* TODO */ },
                        modifier = Modifier.fillMaxWidth().height(56.dp),
                        shape = NevesGoShapes.medium,
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow, contentColor = MaterialTheme.colorScheme.primary),
                        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
                    ) {
                        Text("Voltar", style = MaterialTheme.typography.labelLarge)
                    }
                }
            }
        }
    }
}
