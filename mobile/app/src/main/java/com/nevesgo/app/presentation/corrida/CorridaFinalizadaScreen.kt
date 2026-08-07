package com.nevesgo.app.presentation.corrida

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
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
fun CorridaFinalizadaScreen() {
    Scaffold(
        modifier = Modifier.fillMaxSize()
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.surface) // Will simulate success bg by using surface
                .padding(innerPadding)
                .padding(horizontal = 16.dp)
                .padding(top = 40.dp, bottom = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            // Success Animation & Icon
            Box(
                modifier = Modifier.padding(bottom = 32.dp),
                contentAlignment = Alignment.Center
            ) {
                // Atmospheric blur elements simulated with simple circles
                Box(modifier = Modifier.offset(x = 60.dp, y = (-20).dp).size(32.dp).background(TertiaryFixedDim.copy(alpha = 0.2f), CircleShape))
                Box(modifier = Modifier.offset(x = (-40).dp, y = 40.dp).size(48.dp).background(SecondaryFixedDim.copy(alpha = 0.2f), CircleShape))
                
                Surface(
                    shape = CircleShape,
                    color = MaterialTheme.colorScheme.secondaryContainer,
                    contentColor = MaterialTheme.colorScheme.onSecondaryContainer,
                    shadowElevation = 8.dp,
                    modifier = Modifier.size(128.dp)
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(Icons.Outlined.CheckCircle, contentDescription = null, modifier = Modifier.size(64.dp))
                    }
                }
            }

            // Success Text
            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(bottom = 48.dp)) {
                Text("Entrega Finalizada!", style = MaterialTheme.typography.headlineLarge, color = MaterialTheme.colorScheme.onSurface, modifier = Modifier.padding(bottom = 8.dp))
                Text(
                    text = "Excelente trabalho! Seu trajeto foi concluído com sucesso e o cliente recebeu o pedido.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                    modifier = Modifier.widthIn(max = 280.dp)
                )
            }

            // Earnings Card (Bento-style Glassmorphism)
            Surface(
                shape = NevesGoShapes.medium,
                color = MaterialTheme.colorScheme.surfaceContainerLowest.copy(alpha = 0.8f),
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f)),
                shadowElevation = 2.dp,
                modifier = Modifier.fillMaxWidth().widthIn(max = 384.dp).padding(bottom = 48.dp)
            ) {
                Column(modifier = Modifier.padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("VALOR RECEBIDO", style = MaterialTheme.typography.labelLarge.copy(letterSpacing = 0.05.em), color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(bottom = 16.dp))
                    Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("R$", style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.secondary)
                        Text("18,50", style = MaterialTheme.typography.headlineLarge.copy(fontSize = 64.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = (-0.05).em), color = MaterialTheme.colorScheme.secondary)
                    }
                    
                    Surface(
                        shape = PillShape,
                        color = MaterialTheme.colorScheme.secondaryContainer,
                        contentColor = MaterialTheme.colorScheme.onSecondaryContainer,
                        modifier = Modifier.padding(top = 16.dp)
                    ) {
                        Row(modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Icon(Icons.Outlined.AccountBalanceWallet, contentDescription = null, modifier = Modifier.size(16.dp))
                            Text("Adicionado à sua carteira", style = MaterialTheme.typography.labelSmall)
                        }
                    }

                    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f), modifier = Modifier.padding(top = 40.dp, bottom = 24.dp))

                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceAround) {
                        Column {
                            Text("Distância", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("4.2 km", style = DataMono, color = MaterialTheme.colorScheme.onSurface)
                        }
                        Column {
                            Text("Tempo", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("18 min", style = DataMono, color = MaterialTheme.colorScheme.onSurface)
                        }
                    }
                }
            }
            
            Spacer(modifier = Modifier.weight(1f))

            // Action Button
            Button(
                onClick = { /* TODO */ },
                modifier = Modifier.fillMaxWidth().widthIn(max = 384.dp).height(56.dp),
                shape = NevesGoShapes.medium,
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    contentColor = MaterialTheme.colorScheme.onPrimary
                ),
                elevation = ButtonDefaults.buttonElevation(defaultElevation = 8.dp)
            ) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("Voltar ao Início", style = MaterialTheme.typography.labelLarge)
                    Icon(Icons.Outlined.ArrowForward, contentDescription = null)
                }
            }
        }
    }
}
