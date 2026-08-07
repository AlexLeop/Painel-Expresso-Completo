package com.nevesgo.app.presentation.perfil

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
import com.nevesgo.app.ui.theme.*

@Composable
fun DadosPessoaisScreen() {
    Scaffold(
        topBar = {
            Surface(color = MaterialTheme.colorScheme.surface, shadowElevation = 1.dp) {
                Row(
                    modifier = Modifier.fillMaxWidth().height(64.dp).padding(horizontal = 16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconButton(onClick = { /* TODO */ }, modifier = Modifier.size(40.dp)) {
                            Icon(Icons.Outlined.ArrowBack, contentDescription = "Voltar", tint = MaterialTheme.colorScheme.onSurface)
                        }
                        Text("Dados Pessoais", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurface, modifier = Modifier.padding(start = 8.dp))
                    }
                    Box(modifier = Modifier.size(36.dp).background(MaterialTheme.colorScheme.surfaceContainer, CircleShape).border(1.dp, MaterialTheme.colorScheme.outlineVariant, CircleShape), contentAlignment = Alignment.Center) {
                        Icon(Icons.Outlined.Person, contentDescription = null, tint = MaterialTheme.colorScheme.outline)
                    }
                }
            }
        },
        bottomBar = { NevesGoBottomNav(activeTab = "perfil") },
        modifier = Modifier.fillMaxSize()
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.background)
                .padding(innerPadding)
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Profile Hero Section
            Column(modifier = Modifier.padding(top = 32.dp, bottom = 40.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Box {
                    Box(modifier = Modifier.size(128.dp).border(4.dp, Color.White, CircleShape).background(MaterialTheme.colorScheme.surfaceContainer, CircleShape), contentAlignment = Alignment.Center) {
                        Icon(Icons.Outlined.Person, contentDescription = null, modifier = Modifier.size(64.dp), tint = MaterialTheme.colorScheme.outline)
                    }
                    IconButton(
                        onClick = { /* TODO */ },
                        modifier = Modifier
                            .align(Alignment.BottomEnd)
                            .size(36.dp)
                            .background(MaterialTheme.colorScheme.secondary, CircleShape)
                            .border(2.dp, Color.White, CircleShape)
                    ) {
                        Icon(Icons.Outlined.PhotoCamera, contentDescription = "Alterar Foto", tint = Color.White, modifier = Modifier.size(18.dp))
                    }
                }
                
                Text("Ricardo Oliveira", style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurface, modifier = Modifier.padding(top = 16.dp))
                
                Surface(
                    shape = PillShape,
                    color = Color(0xFF4AE176).copy(alpha = 0.2f),
                    modifier = Modifier.padding(top = 8.dp)
                ) {
                    Text("Entregador Premium", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold), color = Color(0xFF006E2F), modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp))
                }
            }

            // Form Section
            Surface(
                shape = NevesGoShapes.large,
                color = MaterialTheme.colorScheme.surfaceContainerLowest,
                shadowElevation = 2.dp,
                modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp).padding(bottom = 32.dp)
            ) {
                Column(modifier = Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(24.dp)) {
                    FormField(label = "NOME COMPLETO", value = "Ricardo Oliveira", icon = Icons.Outlined.Person)
                    
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Icon(Icons.Outlined.Badge, contentDescription = null, modifier = Modifier.size(18.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("CPF", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        OutlinedTextField(
                            value = "***.456.789-**",
                            onValueChange = {},
                            enabled = false,
                            modifier = Modifier.fillMaxWidth(),
                            shape = NevesGoShapes.medium,
                            colors = OutlinedTextFieldDefaults.colors(
                                disabledContainerColor = MaterialTheme.colorScheme.surfaceContainerLow,
                                disabledBorderColor = MaterialTheme.colorScheme.outlineVariant,
                                disabledTextColor = MaterialTheme.colorScheme.onSurfaceVariant
                            ),
                            trailingIcon = { Icon(Icons.Outlined.Lock, contentDescription = null, tint = MaterialTheme.colorScheme.outline) }
                        )
                    }

                    FormField(label = "E-MAIL", value = "ricardo.oliveira@email.com", icon = Icons.Outlined.Mail)
                    FormField(label = "TELEFONE", value = "(11) 98765-4321", icon = Icons.Outlined.Call)
                    FormField(label = "DATA DE NASCIMENTO", value = "12/05/1992", icon = Icons.Outlined.CalendarToday)
                }
            }

            // Primary Action
            Button(
                onClick = { /* TODO */ },
                modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp).padding(bottom = 32.dp).height(56.dp),
                shape = NevesGoShapes.medium,
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary, contentColor = MaterialTheme.colorScheme.onSecondary)
            ) {
                Text("Salvar Alterações", style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
            }
        }
    }
}

@Composable
private fun FormField(label: String, value: String, icon: androidx.compose.ui.graphics.vector.ImageVector) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Icon(icon, contentDescription = null, modifier = Modifier.size(18.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(label, style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        OutlinedTextField(
            value = value,
            onValueChange = {},
            modifier = Modifier.fillMaxWidth(),
            shape = NevesGoShapes.medium,
            colors = OutlinedTextFieldDefaults.colors(
                unfocusedContainerColor = MaterialTheme.colorScheme.background,
                focusedContainerColor = MaterialTheme.colorScheme.background,
                unfocusedBorderColor = MaterialTheme.colorScheme.outlineVariant,
                focusedBorderColor = MaterialTheme.colorScheme.secondary
            ),
            singleLine = true
        )
    }
}
