package com.nevesgo.app.presentation.perfil

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
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
import com.nevesgo.app.ui.theme.*
import androidx.compose.ui.unit.em
import androidx.compose.foundation.BorderStroke

@Composable
fun PerfilScreen() {
    Scaffold(
        topBar = {
            Surface(color = MaterialTheme.colorScheme.surface, shadowElevation = 1.dp) {
                Row(
                    modifier = Modifier.fillMaxWidth().height(64.dp).padding(horizontal = 16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconButton(onClick = { /* TODO */ }, modifier = Modifier.size(48.dp)) {
                        Icon(Icons.Outlined.ArrowBack, contentDescription = "Voltar", tint = MaterialTheme.colorScheme.onSurface)
                    }
                    Text("Perfil", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.onSurface, modifier = Modifier.weight(1f).padding(start = 8.dp))
                    IconButton(onClick = { /* TODO */ }, modifier = Modifier.size(48.dp)) {
                        Icon(Icons.Outlined.Notifications, contentDescription = "Notificações", tint = MaterialTheme.colorScheme.secondary)
                    }
                }
            }
        },
        bottomBar = { NevesGoBottomNav(activeTab = "perfil") },
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
            // Profile Header Section
            item {
                Surface(
                    shape = NevesGoShapes.medium,
                    color = MaterialTheme.colorScheme.surfaceContainerLowest,
                    shadowElevation = 2.dp,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                        Box(modifier = Modifier.padding(bottom = 16.dp)) {
                            Box(modifier = Modifier.size(96.dp).border(4.dp, MaterialTheme.colorScheme.secondaryContainer, CircleShape).padding(4.dp).background(MaterialTheme.colorScheme.surfaceContainer, CircleShape), contentAlignment = Alignment.Center) {
                                Icon(Icons.Outlined.Person, contentDescription = null, modifier = Modifier.size(48.dp), tint = MaterialTheme.colorScheme.outline)
                            }
                            Box(modifier = Modifier.align(Alignment.BottomEnd).background(MaterialTheme.colorScheme.secondary, CircleShape).border(2.dp, Color.White, CircleShape).padding(4.dp)) {
                                Icon(Icons.Outlined.Verified, contentDescription = "Verificado", tint = Color.White, modifier = Modifier.size(16.dp))
                            }
                        }
                        
                        Text("Ricardo Oliveira", style = MaterialTheme.typography.headlineLarge, color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(bottom = 4.dp))
                        
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(bottom = 16.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(end = 4.dp)) {
                                Icon(Icons.Outlined.Star, contentDescription = null, tint = MaterialTheme.colorScheme.onTertiaryContainer, modifier = Modifier.size(18.dp))
                                Text("4.95", style = DataMono, color = MaterialTheme.colorScheme.onTertiaryContainer, modifier = Modifier.padding(start = 4.dp))
                            }
                            Text("•", color = MaterialTheme.colorScheme.outline)
                            Text("Nível Diamante", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        
                        HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant)
                        
                        Row(modifier = Modifier.fillMaxWidth().padding(top = 16.dp)) {
                            Column(modifier = Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                                Text("2,481", style = DataMono.copy(fontSize = 20.sp), color = MaterialTheme.colorScheme.secondary)
                                Text("ENTREGAS", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            Box(modifier = Modifier.width(1.dp).height(40.dp).background(MaterialTheme.colorScheme.surfaceVariant))
                            Column(modifier = Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                                Text("3 anos", style = DataMono.copy(fontSize = 20.sp), color = MaterialTheme.colorScheme.secondary)
                                Text("NA NEVESGO", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                }
            }

            // Vehicle & Stats
            item {
                Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    Text("VEÍCULO E DADOS", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(start = 8.dp))
                    
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        Surface(
                            shape = NevesGoShapes.medium,
                            color = MaterialTheme.colorScheme.primaryContainer,
                            contentColor = MaterialTheme.colorScheme.onPrimary,
                            modifier = Modifier.weight(7f).height(128.dp)
                        ) {
                            Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.SpaceBetween) {
                                Icon(Icons.Outlined.ElectricMoped, contentDescription = null, tint = MaterialTheme.colorScheme.secondaryContainer, modifier = Modifier.size(24.dp))
                                Column {
                                    Text("Veículo Atual", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onPrimaryContainer)
                                    Text("Honda Biz 125", style = MaterialTheme.typography.headlineMedium)
                                    Text("Placa: ABC-1234", style = DataMono.copy(fontSize = 12.sp), color = MaterialTheme.colorScheme.onPrimaryContainer, modifier = Modifier.padding(top = 4.dp))
                                }
                            }
                        }
                        
                        Surface(
                            shape = NevesGoShapes.medium,
                            color = MaterialTheme.colorScheme.surfaceContainerLowest,
                            border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                            modifier = Modifier.weight(5f).height(128.dp)
                        ) {
                            Column(modifier = Modifier.padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                                Box(modifier = Modifier.size(48.dp).background(MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.2f), CircleShape), contentAlignment = Alignment.Center) {
                                    Icon(Icons.Outlined.Payments, contentDescription = null, tint = MaterialTheme.colorScheme.secondary)
                                }
                                Text("Ganhos Mês", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(top = 8.dp))
                                Text("R$ 4.820", style = DataMono.copy(fontSize = 18.sp), color = MaterialTheme.colorScheme.primary)
                            }
                        }
                    }
                }
            }

            // Navigation Menu
            item {
                Surface(
                    shape = NevesGoShapes.medium,
                    color = MaterialTheme.colorScheme.surfaceContainerLowest,
                    border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                    shadowElevation = 1.dp,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column {
                        MenuListItem(icon = Icons.Outlined.ManageAccounts, title = "Dados Pessoais", onClick = { /* TODO */ })
                        MenuListItem(icon = Icons.Outlined.Security, title = "Segurança e Senha", onClick = { /* TODO */ })
                        MenuListItem(icon = Icons.Outlined.HistoryEdu, title = "Histórico de Documentos", onClick = { /* TODO */ })
                        
                        HorizontalDivider(modifier = Modifier.padding(horizontal = 16.dp), color = MaterialTheme.colorScheme.surfaceVariant)
                        
                        MenuListItem(icon = Icons.Outlined.Help, title = "Central de Ajuda", titleColor = MaterialTheme.colorScheme.secondary, iconColor = MaterialTheme.colorScheme.secondary, onClick = { /* TODO */ }, bold = true)
                        MenuListItem(icon = Icons.Outlined.SupportAgent, title = "Suporte em Tempo Real", onClick = { /* TODO */ })
                    }
                }
            }

            // Logout
            item {
                TextButton(
                    onClick = { /* TODO */ },
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                    colors = ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.error)
                ) {
                    Row(horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Outlined.Logout, contentDescription = null, modifier = Modifier.size(20.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Sair da Conta", style = MaterialTheme.typography.labelLarge)
                    }
                }
            }
        }
    }
}

@Composable
private fun MenuListItem(icon: androidx.compose.ui.graphics.vector.ImageVector, title: String, onClick: () -> Unit, titleColor: Color = MaterialTheme.colorScheme.onSurface, iconColor: Color = MaterialTheme.colorScheme.onSurfaceVariant, bold: Boolean = false) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Icon(icon, contentDescription = null, tint = iconColor, modifier = Modifier.size(24.dp))
            Text(title, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = if (bold) FontWeight.Bold else FontWeight.Normal), color = titleColor)
        }
        Icon(Icons.Outlined.ChevronRight, contentDescription = null, tint = MaterialTheme.colorScheme.outline)
    }
}
