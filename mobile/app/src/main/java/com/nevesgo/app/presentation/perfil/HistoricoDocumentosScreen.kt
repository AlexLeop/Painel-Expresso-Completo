package com.nevesgo.app.presentation.perfil

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.nevesgo.app.ui.theme.*
import androidx.compose.ui.unit.em
import androidx.compose.foundation.BorderStroke

@Composable
fun HistoricoDocumentosScreen() {
    Scaffold(
        topBar = {
            Surface(color = MaterialTheme.colorScheme.surface, shadowElevation = 1.dp) {
                Row(
                    modifier = Modifier.fillMaxWidth().height(56.dp).padding(horizontal = 16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconButton(onClick = { /* TODO */ }, modifier = Modifier.size(40.dp)) {
                        Icon(Icons.Outlined.ArrowBack, contentDescription = "Voltar", tint = MaterialTheme.colorScheme.primary)
                    }
                    Text("Histórico de Documentos", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(start = 16.dp))
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
            verticalArrangement = Arrangement.spacedBy(32.dp)
        ) {
            // Documentos Pessoais
            item {
                Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    Text("Documentos Pessoais", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurface)
                    
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        DocumentCard(
                            icon = Icons.Outlined.Badge,
                            title = "CNH",
                            statusText = "Aprovado em 12/10/2023",
                            badgeText = "Aprovado",
                            badgeIcon = Icons.Outlined.CheckCircle,
                            badgeColor = MaterialTheme.colorScheme.secondaryContainer,
                            badgeTextColor = MaterialTheme.colorScheme.onSecondaryContainer,
                            borderColor = MaterialTheme.colorScheme.secondary
                        )
                        DocumentCard(
                            icon = Icons.Outlined.Badge,
                            title = "RG/CPF",
                            statusText = "Aprovado em 12/10/2023",
                            badgeText = "Aprovado",
                            badgeIcon = Icons.Outlined.CheckCircle,
                            badgeColor = MaterialTheme.colorScheme.secondaryContainer,
                            badgeTextColor = MaterialTheme.colorScheme.onSecondaryContainer,
                            borderColor = MaterialTheme.colorScheme.secondary
                        )
                        DocumentCard(
                            icon = Icons.Outlined.Policy,
                            title = "Antecedentes Criminais",
                            statusText = "Vence em 30 dias",
                            statusTextColor = MaterialTheme.colorScheme.error,
                            badgeText = "Atenção",
                            badgeIcon = Icons.Outlined.Warning,
                            badgeColor = TertiaryFixed,
                            badgeTextColor = MaterialTheme.colorScheme.onTertiaryContainer,
                            borderColor = TertiaryFixedDim
                        )
                    }
                }
            }

            // Documentos do Veículo
            item {
                Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    Text("Documentos do Veículo", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurface)
                    
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        DocumentCard(
                            icon = Icons.Outlined.DirectionsBike,
                            title = "CRLV - Honda Biz 125",
                            statusText = "Enviado em 14/01/2024",
                            badgeText = "Em análise",
                            badgeIcon = Icons.Outlined.Schedule,
                            badgeColor = PrimaryFixed,
                            badgeTextColor = OnPrimaryFixedVariant,
                            borderColor = PrimaryFixedDim
                        )
                        DocumentCard(
                            icon = Icons.Outlined.VerifiedUser,
                            title = "Seguro Obrigatório",
                            statusText = "Aprovado em 05/01/2024",
                            badgeText = "Aprovado",
                            badgeIcon = Icons.Outlined.CheckCircle,
                            badgeColor = MaterialTheme.colorScheme.secondaryContainer,
                            badgeTextColor = MaterialTheme.colorScheme.onSecondaryContainer,
                            borderColor = MaterialTheme.colorScheme.secondary
                        )
                    }
                }
            }
            
            // CTA
            item {
                OutlinedButton(
                    onClick = { /* TODO */ },
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    shape = NevesGoShapes.medium,
                    colors = ButtonDefaults.outlinedButtonColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh, contentColor = MaterialTheme.colorScheme.onSurfaceVariant),
                    border = androidx.compose.foundation.BorderStroke(2.dp, MaterialTheme.colorScheme.outlineVariant) // Dashed border not natively supported, using solid
                ) {
                    Row(horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Outlined.AddCircle, contentDescription = null, modifier = Modifier.size(24.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Enviar Novo Documento", style = MaterialTheme.typography.labelLarge)
                    }
                }
            }
        }
    }
}

@Composable
private fun DocumentCard(icon: androidx.compose.ui.graphics.vector.ImageVector, title: String, statusText: String, badgeText: String, badgeIcon: androidx.compose.ui.graphics.vector.ImageVector, badgeColor: Color, badgeTextColor: Color, borderColor: Color, statusTextColor: Color = MaterialTheme.colorScheme.onSurfaceVariant) {
    Surface(
        shape = NevesGoShapes.medium,
        color = MaterialTheme.colorScheme.surfaceContainerLowest,
        shadowElevation = 2.dp,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier.border(BorderStroke(4.dp, borderColor), shape = RoundedCornerShape(topStart = 12.dp, bottomStart = 12.dp)).padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp), modifier = Modifier.weight(1f)) {
                Box(modifier = Modifier.size(48.dp).background(MaterialTheme.colorScheme.surfaceContainer, NevesGoShapes.small), contentAlignment = Alignment.Center) {
                    Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(24.dp))
                }
                Column {
                    Text(title, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurface)
                    Text(statusText, style = MaterialTheme.typography.labelSmall, color = statusTextColor)
                }
            }
            Surface(shape = PillShape, color = badgeColor, contentColor = badgeTextColor) {
                Row(modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Icon(badgeIcon, contentDescription = null, modifier = Modifier.size(18.dp))
                    Text(badgeText, style = MaterialTheme.typography.labelSmall)
                }
            }
        }
    }
}
