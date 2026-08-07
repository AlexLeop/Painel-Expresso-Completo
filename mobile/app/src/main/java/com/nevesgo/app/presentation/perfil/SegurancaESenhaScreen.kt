package com.nevesgo.app.presentation.perfil

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
import androidx.compose.ui.unit.dp
import com.nevesgo.app.ui.theme.*
import androidx.compose.ui.unit.em
import androidx.compose.ui.graphics.Color

@Composable
fun SegurancaESenhaScreen() {
    var biometricsEnabled by remember { mutableStateOf(true) }

    Scaffold(
        topBar = {
            Surface(color = MaterialTheme.colorScheme.background, shadowElevation = 1.dp) {
                Row(
                    modifier = Modifier.fillMaxWidth().height(56.dp).padding(horizontal = 16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconButton(onClick = { /* TODO */ }, modifier = Modifier.size(40.dp)) {
                            Icon(Icons.Outlined.ArrowBack, contentDescription = "Voltar", tint = MaterialTheme.colorScheme.primary)
                        }
                        Text("Segurança e Senha", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(start = 8.dp))
                    }
                    Box(modifier = Modifier.size(32.dp).background(MaterialTheme.colorScheme.surfaceContainer, CircleShape), contentAlignment = Alignment.Center) {
                        Icon(Icons.Outlined.Person, contentDescription = null, tint = MaterialTheme.colorScheme.outline)
                    }
                }
            }
        },
        bottomBar = {
            Column {
                Surface(
                    color = MaterialTheme.colorScheme.background.copy(alpha = 0.9f),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Box(modifier = Modifier.padding(16.dp)) {
                        Button(
                            onClick = { /* TODO */ },
                            modifier = Modifier.fillMaxWidth().height(56.dp),
                            shape = NevesGoShapes.medium,
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary, contentColor = MaterialTheme.colorScheme.onSecondary)
                        ) {
                            Row(horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Outlined.Save, contentDescription = null, modifier = Modifier.size(20.dp))
                                Spacer(modifier = Modifier.width(8.dp))
                                Text("Salvar Alterações", style = MaterialTheme.typography.labelLarge)
                            }
                        }
                    }
                }
                NevesGoBottomNav(activeTab = "perfil")
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
            // Password Section
            item {
                Surface(
                    shape = NevesGoShapes.medium,
                    color = MaterialTheme.colorScheme.surfaceContainerLowest,
                    shadowElevation = 2.dp,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Icon(Icons.Outlined.LockReset, contentDescription = null, tint = MaterialTheme.colorScheme.secondary)
                            Text("Alterar Senha", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurface)
                        }
                        
                        PasswordField(label = "Senha Atual", placeholder = "Digite sua senha atual")
                        PasswordField(label = "Nova Senha", placeholder = "Mínimo 8 caracteres")
                        PasswordField(label = "Confirmar Nova Senha", placeholder = "Repita a nova senha")
                    }
                }
            }

            // Biometrics Section
            item {
                Surface(
                    shape = NevesGoShapes.medium,
                    color = MaterialTheme.colorScheme.surfaceContainerLowest,
                    shadowElevation = 2.dp,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(modifier = Modifier.padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            Box(modifier = Modifier.size(40.dp).background(MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.2f), CircleShape), contentAlignment = Alignment.Center) {
                                Icon(Icons.Outlined.Fingerprint, contentDescription = null, tint = MaterialTheme.colorScheme.secondary)
                            }
                            Column {
                                Text("Biometria", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurface)
                                Text("Touch ID / Face ID", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                        Switch(
                            checked = biometricsEnabled,
                            onCheckedChange = { biometricsEnabled = it },
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = Color.White,
                                checkedTrackColor = Color(0xFF006E2F)
                            )
                        )
                    }
                }
            }

            // 2FA Section
            item {
                Surface(
                    shape = NevesGoShapes.medium,
                    color = MaterialTheme.colorScheme.surfaceContainerLowest,
                    shadowElevation = 2.dp,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(modifier = Modifier.padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            Box(modifier = Modifier.size(40.dp).background(MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.2f), CircleShape), contentAlignment = Alignment.Center) {
                                Icon(Icons.Outlined.VerifiedUser, contentDescription = null, tint = MaterialTheme.colorScheme.secondary)
                            }
                            Column {
                                Text("Autenticação em duas etapas", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurface)
                                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp), modifier = Modifier.padding(top = 2.dp)) {
                                    Box(modifier = Modifier.size(8.dp).background(MaterialTheme.colorScheme.secondary, CircleShape))
                                    Text("Ativado", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.secondary)
                                }
                            }
                        }
                        IconButton(onClick = { /* TODO */ }) {
                            Icon(Icons.Outlined.ChevronRight, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }

            // Login History
            item {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("ÚLTIMOS ACESSOS", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(start = 4.dp))
                    Surface(
                        shape = NevesGoShapes.medium,
                        color = MaterialTheme.colorScheme.surfaceContainerLowest,
                        shadowElevation = 2.dp,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column {
                            LoginHistoryItem(device = "iPhone 14 Pro", location = "São Paulo, BR • Agora", isCurrent = true, icon = Icons.Outlined.Smartphone)
                            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f))
                            LoginHistoryItem(device = "MacBook Air", location = "São Paulo, BR • 2 horas atrás", isCurrent = false, icon = Icons.Outlined.Laptop)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun PasswordField(label: String, placeholder: String) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
        OutlinedTextField(
            value = "",
            onValueChange = {},
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text(placeholder, style = MaterialTheme.typography.bodyMedium) },
            shape = NevesGoShapes.medium,
            colors = OutlinedTextFieldDefaults.colors(
                unfocusedContainerColor = MaterialTheme.colorScheme.surfaceContainerLow,
                focusedContainerColor = MaterialTheme.colorScheme.surfaceContainerLow,
                unfocusedBorderColor = Color.Transparent,
                focusedBorderColor = MaterialTheme.colorScheme.secondary.copy(alpha = 0.2f)
            ),
            trailingIcon = {
                IconButton(onClick = { /* TODO */ }) {
                    Icon(Icons.Outlined.Visibility, contentDescription = "Mostrar senha", tint = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            },
            singleLine = true
        )
    }
}

@Composable
private fun LoginHistoryItem(device: String, location: String, isCurrent: Boolean, icon: androidx.compose.ui.graphics.vector.ImageVector) {
    Row(modifier = Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
            Column {
                Text(device, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurface)
                Text(location, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        if (isCurrent) {
            Surface(shape = NevesGoShapes.small, color = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.2f)) {
                Text("Este disp.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.secondary, modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp))
            }
        }
    }
}
