package com.nevesgo.app.presentation.financeiro

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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nevesgo.app.ui.theme.*
import androidx.compose.ui.unit.em
import androidx.compose.foundation.BorderStroke

@Composable
fun SolicitarSaqueScreen(uiState: SaqueUiState = SaqueUiState.Formulario) {
    var withdrawAmount by remember { mutableStateOf("500.00") }

    Scaffold(
        topBar = {
            if (uiState == SaqueUiState.Formulario) {
                Surface(color = MaterialTheme.colorScheme.surface, shadowElevation = 1.dp) {
                    Row(
                        modifier = Modifier.fillMaxWidth().height(56.dp).padding(horizontal = 16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        IconButton(onClick = { /* TODO */ }, modifier = Modifier.size(48.dp)) {
                            Icon(Icons.Outlined.ArrowBack, contentDescription = "Voltar", tint = MaterialTheme.colorScheme.primary)
                        }
                        Text("Solicitar Saque", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary, modifier = Modifier.weight(1f))
                        Box(modifier = Modifier.size(40.dp).background(MaterialTheme.colorScheme.outlineVariant, CircleShape).border(1.dp, MaterialTheme.colorScheme.outlineVariant, CircleShape), contentAlignment = Alignment.Center) {
                            Icon(Icons.Outlined.Person, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        },
        bottomBar = {
            Surface(
                color = MaterialTheme.colorScheme.surface,
                shadowElevation = 8.dp,
                modifier = Modifier.fillMaxWidth()
            ) {
                Box(modifier = Modifier.padding(16.dp)) {
                    if (uiState == SaqueUiState.Formulario) {
                        Button(
                            onClick = { /* TODO: Change state to Sucesso via ViewModel */ },
                            modifier = Modifier.fillMaxWidth().height(56.dp),
                            shape = NevesGoShapes.medium,
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary, contentColor = MaterialTheme.colorScheme.onSecondary)
                        ) {
                            Row(horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Outlined.Lock, contentDescription = null, modifier = Modifier.size(20.dp))
                                Spacer(modifier = Modifier.width(8.dp))
                                Text("Confirmar Saque", style = MaterialTheme.typography.headlineMedium)
                            }
                        }
                    } else {
                        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            Button(
                                onClick = { /* TODO: Reset to Formulario or Go back */ },
                                modifier = Modifier.fillMaxWidth().height(56.dp),
                                shape = NevesGoShapes.medium,
                                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary, contentColor = MaterialTheme.colorScheme.onPrimary)
                            ) {
                                Text("Voltar para Carteira", style = MaterialTheme.typography.labelLarge)
                            }
                            OutlinedButton(
                                onClick = { /* TODO */ },
                                modifier = Modifier.fillMaxWidth().height(56.dp),
                                shape = NevesGoShapes.medium,
                                border = androidx.compose.foundation.BorderStroke(2.dp, MaterialTheme.colorScheme.outline),
                                colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.secondary)
                            ) {
                                Row(horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Outlined.Share, contentDescription = null, modifier = Modifier.size(20.dp))
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text("Compartilhar Comprovante", style = MaterialTheme.typography.labelLarge)
                                }
                            }
                        }
                    }
                }
            }
        },
        modifier = Modifier.fillMaxSize()
    ) { innerPadding ->
        when (uiState) {
            is SaqueUiState.Formulario -> {
                FormularioContent(
                    withdrawAmount = withdrawAmount,
                    onAmountChange = { withdrawAmount = it },
                    innerPadding = innerPadding
                )
            }
            is SaqueUiState.Sucesso -> {
                SucessoContent(innerPadding = innerPadding)
            }
        }
    }
}

@Composable
private fun FormularioContent(withdrawAmount: String, onAmountChange: (String) -> Unit, innerPadding: PaddingValues) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(innerPadding),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(24.dp)
    ) {
        // Available Balance Card
        item {
            Surface(
                shape = NevesGoShapes.medium,
                color = MaterialTheme.colorScheme.primaryContainer,
                contentColor = MaterialTheme.colorScheme.onPrimaryContainer,
                shadowElevation = 8.dp,
                modifier = Modifier.fillMaxWidth()
            ) {
                Box {
                    Box(
                        modifier = Modifier
                            .align(Alignment.TopEnd)
                            .size(120.dp)
                            .offset(x = 20.dp, y = (-20).dp)
                            .background(MaterialTheme.colorScheme.secondary.copy(alpha = 0.2f), CircleShape)
                    )
                    
                    Column(modifier = Modifier.padding(24.dp)) {
                        Text("Saldo Disponível", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f))
                        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = 4.dp)) {
                            Text("R$ 1.248,50", style = MaterialTheme.typography.headlineLarge, color = Color.White)
                            Spacer(modifier = Modifier.width(8.dp))
                            Icon(Icons.Outlined.TrendingUp, contentDescription = null, tint = MaterialTheme.colorScheme.secondary, modifier = Modifier.size(20.dp))
                        }
                    }
                }
            }
        }

        // Input Section
        item {
            Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                Text("Valor do Saque", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                
                Surface(
                    shape = NevesGoShapes.medium,
                    color = Color.White,
                    border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                    modifier = Modifier.fillMaxWidth().height(64.dp)
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(horizontal = 16.dp)) {
                        Text("R$", style = MaterialTheme.typography.headlineLarge, color = MaterialTheme.colorScheme.outline)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(withdrawAmount, style = MaterialTheme.typography.headlineLarge, color = MaterialTheme.colorScheme.onSurface)
                    }
                }
                
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    QuickAmountButton(text = "R$ 100", onClick = { onAmountChange("100.00") }, modifier = Modifier.weight(1f))
                    QuickAmountButton(text = "R$ 500", onClick = { onAmountChange("500.00") }, modifier = Modifier.weight(1f), isHighlighted = true)
                    QuickAmountButton(text = "Tudo", onClick = { onAmountChange("1248.50") }, modifier = Modifier.weight(1f))
                }
            }
        }

        // Bank Account Summary
        item {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("Destino do saque", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                
                Surface(
                    shape = NevesGoShapes.medium,
                    color = Color.White,
                    border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        Box(modifier = Modifier.size(48.dp).background(MaterialTheme.colorScheme.surfaceContainer, CircleShape), contentAlignment = Alignment.Center) {
                            Icon(Icons.Outlined.AccountBalance, contentDescription = null, tint = MaterialTheme.colorScheme.secondary)
                        }
                        Column(modifier = Modifier.weight(1f)) {
                            Text("Itaú Unibanco", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurface)
                            Text("Agência 0442 • Conta •••• 4821", style = MaterialTheme.typography.bodyMedium.copy(fontSize = 12.sp), color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("PIX: 123.***.***-01", style = DataMono.copy(fontSize = 10.sp), color = MaterialTheme.colorScheme.outline, modifier = Modifier.padding(top = 4.dp))
                        }
                        IconButton(onClick = { /* TODO */ }) {
                            Icon(Icons.Outlined.Edit, contentDescription = "Editar", tint = MaterialTheme.colorScheme.secondary)
                        }
                    }
                }
            }
        }

        // Transaction Details
        item {
            Surface(
                shape = NevesGoShapes.medium,
                color = MaterialTheme.colorScheme.surfaceContainerLow,
                border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Text("Taxa de transferência", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("Grátis", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.secondary)
                    }
                    HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp), color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f))
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Text("Valor Líquido", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurface)
                        Text("R$ $withdrawAmount", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.secondary)
                    }
                }
            }
        }
        
        // Security Note
        item {
            Row(modifier = Modifier.padding(horizontal = 8.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Top) {
                Icon(Icons.Outlined.Info, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(20.dp))
                Text("O valor será creditado em sua conta em até 24h úteis. Certifique-se de que os dados do Pix estão corretos antes de confirmar.", style = MaterialTheme.typography.bodyMedium.copy(fontSize = 12.sp), color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun SucessoContent(innerPadding: PaddingValues) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(innerPadding),
        contentPadding = PaddingValues(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        item { Spacer(modifier = Modifier.height(32.dp)) }

        // Success Icon
        item {
            Box(contentAlignment = Alignment.Center, modifier = Modifier.padding(bottom = 32.dp)) {
                Box(modifier = Modifier.size(144.dp).background(Color(0xFFC8E6C9).copy(alpha = 0.4f), CircleShape))
                Box(modifier = Modifier.size(96.dp).background(Color(0xFFE8F5E9), CircleShape), contentAlignment = Alignment.Center) {
                    Icon(Icons.Outlined.Check, contentDescription = null, tint = Color(0xFF2E7D32), modifier = Modifier.size(48.dp))
                }
            }
        }

        // Headers
        item {
            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(bottom = 40.dp)) {
                Text("Solicitação de Saque Realizada", style = MaterialTheme.typography.headlineLarge, color = MaterialTheme.colorScheme.onBackground, textAlign = TextAlign.Center)
                Text("Seu dinheiro está a caminho!", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(top = 8.dp))
            }
        }

        // Transaction Details Card
        item {
            Surface(
                shape = NevesGoShapes.medium,
                color = Color.White,
                border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.surfaceContainerLow),
                shadowElevation = 2.dp,
                modifier = Modifier.fillMaxWidth()
            ) {
                Column {
                    Row(
                        modifier = Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.surfaceContainerLowest).padding(horizontal = 24.dp, vertical = 16.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("STATUS DA TRANSAÇÃO", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Surface(shape = PillShape, color = TertiaryFixed.copy(alpha = 0.2f)) {
                            Row(modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Box(modifier = Modifier.size(8.dp).background(OnTertiaryContainer, CircleShape))
                                Text("Processando", style = MaterialTheme.typography.labelSmall, color = OnTertiaryContainer)
                            }
                        }
                    }
                    
                    HorizontalDivider(color = MaterialTheme.colorScheme.surfaceContainer)
                    
                    Column(modifier = Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                            Text("Valor solicitado", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("R$ 500,00", style = DataMono, color = MaterialTheme.colorScheme.onBackground)
                        }
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                            Text("Taxa de serviço", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("Grátis", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.secondary)
                        }
                        HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp), color = MaterialTheme.colorScheme.outlineVariant)
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                            Text("Valor líquido", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.onBackground)
                            Text("R$ 500,00", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.secondary)
                        }
                    }
                    
                    Column(modifier = Modifier.padding(horizontal = 24.dp).padding(bottom = 24.dp)) {
                        Surface(shape = NevesGoShapes.medium, color = MaterialTheme.colorScheme.surfaceContainerLow) {
                            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Top) {
                                    Icon(Icons.Outlined.AccountBalance, contentDescription = null, tint = MaterialTheme.colorScheme.outline)
                                    Column {
                                        Text("Itaú Unibanco", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onBackground)
                                        Text("Agência 0442 • Conta **** 4821", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    }
                                }
                                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f))
                                Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Outlined.Schedule, contentDescription = null, tint = MaterialTheme.colorScheme.outline)
                                    Column {
                                        Text("Estimativa de chegada", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                        Text("Até 24h úteis", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onBackground)
                                    }
                                }
                            }
                        }
                    }
                    
                    HorizontalDivider(color = MaterialTheme.colorScheme.surfaceContainer)
                    
                    Column(modifier = Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.surfaceContainerLowest).padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("ID da Transação", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline)
                        Text("FL-99283-XP-041", style = DataMono.copy(fontSize = 12.sp), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }

        // Info Tip
        item {
            Surface(
                shape = NevesGoShapes.medium,
                color = PrimaryFixed.copy(alpha = 0.2f),
                modifier = Modifier.fillMaxWidth().padding(top = 32.dp)
            ) {
                Row(modifier = Modifier.padding(16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Outlined.Info, contentDescription = null, tint = OnPrimaryFixedVariant)
                    Text("Você receberá uma notificação push assim que o valor for creditado.", style = MaterialTheme.typography.labelSmall, color = OnPrimaryFixedVariant)
                }
            }
        }
    }
}

@Composable
private fun QuickAmountButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier, isHighlighted: Boolean = false) {
    Surface(
        shape = NevesGoShapes.small,
        color = if (isHighlighted) MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.2f) else MaterialTheme.colorScheme.surfaceContainerLow,
        border = androidx.compose.foundation.BorderStroke(1.dp, if (isHighlighted) MaterialTheme.colorScheme.secondary.copy(alpha = 0.3f) else MaterialTheme.colorScheme.outlineVariant),
        onClick = onClick,
        modifier = modifier.height(48.dp)
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text(text, style = MaterialTheme.typography.labelLarge, color = if (isHighlighted) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.onSurface)
        }
    }
}
