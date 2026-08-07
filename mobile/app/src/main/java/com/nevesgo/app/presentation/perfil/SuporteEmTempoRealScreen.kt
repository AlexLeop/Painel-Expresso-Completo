package com.nevesgo.app.presentation.perfil

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.nevesgo.app.ui.theme.*
import androidx.compose.ui.unit.em
import androidx.compose.foundation.BorderStroke

@Composable
fun SuporteEmTempoRealScreen() {
    Scaffold(
        topBar = {
            Surface(color = MaterialTheme.colorScheme.surfaceContainerLowest, shadowElevation = 1.dp) {
                Row(
                    modifier = Modifier.fillMaxWidth().height(64.dp).padding(horizontal = 16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                        IconButton(onClick = { /* TODO */ }, modifier = Modifier.size(40.dp)) {
                            Icon(Icons.Outlined.ArrowBack, contentDescription = "Voltar", tint = MaterialTheme.colorScheme.onSurface)
                        }
                        Column(modifier = Modifier.padding(start = 8.dp)) {
                            Text("Suporte em Tempo Real", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurface)
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                Box(modifier = Modifier.size(8.dp).background(Color(0xFF4AE176), CircleShape))
                                Text("Atendente Online", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                    Box(modifier = Modifier.size(40.dp).background(MaterialTheme.colorScheme.surfaceContainer, CircleShape).border(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f), CircleShape), contentAlignment = Alignment.Center) {
                        Icon(Icons.Outlined.SupportAgent, contentDescription = null, tint = MaterialTheme.colorScheme.outline)
                    }
                }
            }
        },
        bottomBar = {
            Surface(color = MaterialTheme.colorScheme.surfaceContainerLowest, border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.2f))) {
                Row(modifier = Modifier.fillMaxWidth().padding(16.dp).navigationBarsPadding(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    IconButton(onClick = { /* TODO */ }) {
                        Icon(Icons.Outlined.Add, contentDescription = "Anexar", tint = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    OutlinedTextField(
                        value = "",
                        onValueChange = {},
                        modifier = Modifier.weight(1f),
                        placeholder = { Text("Escreva sua mensagem...", style = MaterialTheme.typography.bodyMedium) },
                        shape = CircleShape,
                        colors = OutlinedTextFieldDefaults.colors(
                            unfocusedContainerColor = MaterialTheme.colorScheme.surfaceContainerLow,
                            focusedContainerColor = MaterialTheme.colorScheme.surfaceContainerLowest,
                            unfocusedBorderColor = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f),
                            focusedBorderColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.3f)
                        ),
                        singleLine = true
                    )
                    IconButton(
                        onClick = { /* TODO */ },
                        modifier = Modifier.size(40.dp).background(MaterialTheme.colorScheme.primary, CircleShape)
                    ) {
                        Icon(Icons.Outlined.Send, contentDescription = "Enviar", tint = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.size(20.dp))
                    }
                }
            }
        },
        modifier = Modifier.fillMaxSize()
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.surfaceBright)
                .padding(innerPadding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                    Surface(shape = PillShape, color = MaterialTheme.colorScheme.surfaceContainerHigh) {
                        Text("HOJE", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.outline, modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp))
                    }
                }
            }

            // Agent Message
            item {
                Row(modifier = Modifier.fillMaxWidth(0.85f), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Bottom) {
                    Box(modifier = Modifier.size(32.dp).background(MaterialTheme.colorScheme.surfaceContainer, CircleShape).border(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f), CircleShape), contentAlignment = Alignment.Center) {
                        Icon(Icons.Outlined.SupportAgent, contentDescription = null, tint = MaterialTheme.colorScheme.outline, modifier = Modifier.size(20.dp))
                    }
                    Column(horizontalAlignment = Alignment.Start, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Surface(shape = RoundedCornerShape(topStart = 16.dp, topEnd = 16.dp, bottomEnd = 16.dp, bottomStart = 4.dp), color = MaterialTheme.colorScheme.surfaceContainerHigh) {
                            Text("Olá! Sou o Ricardo da Velocity. Como posso ajudar com sua entrega hoje?", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp))
                        }
                        Text("14:20", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline, modifier = Modifier.padding(start = 4.dp))
                    }
                }
            }

            // User Message
            item {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    Row(modifier = Modifier.fillMaxWidth(0.85f), horizontalArrangement = Arrangement.End, verticalAlignment = Alignment.Bottom) {
                        Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Surface(shape = RoundedCornerShape(topStart = 16.dp, topEnd = 16.dp, bottomStart = 16.dp, bottomEnd = 4.dp), color = MaterialTheme.colorScheme.primary, shadowElevation = 2.dp) {
                                Text("Oi Ricardo, gostaria de saber o status atual do meu pedido #78921. O rastreio diz que está parado.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp))
                            }
                            Text("14:22", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline, modifier = Modifier.padding(end = 4.dp))
                        }
                    }
                }
            }

            // Agent Message
            item {
                Row(modifier = Modifier.fillMaxWidth(0.85f), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Bottom) {
                    Box(modifier = Modifier.size(32.dp).background(MaterialTheme.colorScheme.surfaceContainer, CircleShape).border(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f), CircleShape), contentAlignment = Alignment.Center) {
                        Icon(Icons.Outlined.SupportAgent, contentDescription = null, tint = MaterialTheme.colorScheme.outline, modifier = Modifier.size(20.dp))
                    }
                    Column(horizontalAlignment = Alignment.Start, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Surface(shape = RoundedCornerShape(topStart = 16.dp, topEnd = 16.dp, bottomEnd = 16.dp, bottomStart = 4.dp), color = MaterialTheme.colorScheme.surfaceContainerHigh) {
                            Text("Vou verificar agora mesmo para você no sistema de roteirização. Um momento, por favor.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp))
                        }
                        Text("14:23", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline, modifier = Modifier.padding(start = 4.dp))
                    }
                }
            }
        }
    }
}
