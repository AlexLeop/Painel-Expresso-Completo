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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import com.nevesgo.app.ui.theme.*
import androidx.compose.foundation.BorderStroke

@Composable
fun CarteiraScreen() {
    Scaffold(
        topBar = {
            Surface(color = MaterialTheme.colorScheme.surface, shadowElevation = 1.dp) {
                Row(
                    modifier = Modifier.fillMaxWidth().height(56.dp).padding(horizontal = 16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconButton(onClick = { /* TODO */ }, modifier = Modifier.size(48.dp)) {
                        Icon(Icons.Outlined.ArrowBack, contentDescription = "Voltar", tint = MaterialTheme.colorScheme.onSurface)
                    }
                    Text("Carteira", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.onSurface, modifier = Modifier.weight(1f))
                    IconButton(onClick = { /* TODO */ }, modifier = Modifier.size(48.dp)) {
                        Icon(Icons.Outlined.Notifications, contentDescription = "Notificações", tint = MaterialTheme.colorScheme.secondary)
                    }
                }
            }
        },
        bottomBar = { NevesGoBottomNav(activeTab = "ganhos") }, // Using 'ganhos' to match the HTML layout bottom nav
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
            // Balance Hero Card
            item {
                Surface(
                    shape = NevesGoShapes.medium,
                    color = MaterialTheme.colorScheme.primary, // Black background as requested
                    contentColor = MaterialTheme.colorScheme.onPrimary,
                    shadowElevation = 8.dp,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Box {
                        // Decorative blur
                        Box(
                            modifier = Modifier
                                .align(Alignment.TopEnd)
                                .size(120.dp)
                                .offset(x = 20.dp, y = (-20).dp)
                                .background(MaterialTheme.colorScheme.secondary.copy(alpha = 0.2f), CircleShape)
                        )
                        
                        Column(modifier = Modifier.padding(24.dp)) {
                            Text("SALDO DISPONÍVEL", style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.1.em), color = MaterialTheme.colorScheme.onPrimary)
                            Row(verticalAlignment = Alignment.Bottom, modifier = Modifier.padding(top = 8.dp)) {
                                Text("R$", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.7f))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("1.248,50", style = MaterialTheme.typography.displaySmall.copy(fontWeight = FontWeight.ExtraBold, letterSpacing = (-0.02).em), color = MaterialTheme.colorScheme.onPrimary)
                            }
                            
                            Button(
                                onClick = { /* TODO */ },
                                modifier = Modifier.fillMaxWidth().padding(top = 32.dp).height(56.dp),
                                shape = NevesGoShapes.medium,
                                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary, contentColor = MaterialTheme.colorScheme.onSecondary)
                            ) {
                                Row(horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                                    Text("Solicitar Saque", style = MaterialTheme.typography.labelLarge)
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Icon(Icons.Outlined.ArrowForward, contentDescription = null, modifier = Modifier.size(20.dp))
                                }
                            }
                        }
                    }
                }
            }

            // Earnings Mini Chart (Bento Style)
            item {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    // Filters
                    Row(
                        modifier = Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.surfaceContainerHigh, NevesGoShapes.medium).padding(4.dp)
                    ) {
                        FilterButton(text = "Dia", selected = false, modifier = Modifier.weight(1f))
                        FilterButton(text = "Semana", selected = true, modifier = Modifier.weight(1f))
                        FilterButton(text = "Mês", selected = false, modifier = Modifier.weight(1f))
                    }
                    
                    // Chart Card
                    Surface(
                        shape = NevesGoShapes.medium,
                        color = MaterialTheme.colorScheme.surfaceContainerLowest,
                        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(20.dp)) {
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                Text("Entradas Recentes", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.onSurface)
                                Text("Últimos 7 dias", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            
                            Spacer(modifier = Modifier.height(24.dp))
                            
                            // Bar chart visualization
                            Row(
                                modifier = Modifier.fillMaxWidth().height(120.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.Bottom
                            ) {
                                val heights = listOf(0.4f, 0.65f, 0.9f, 0.3f, 0.75f, 1f, 0.55f)
                                heights.forEach { fraction ->
                                    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.weight(1f)) {
                                        Box(
                                            modifier = Modifier
                                                .fillMaxWidth(0.6f)
                                                .fillMaxHeight(fraction)
                                                .background(
                                                    Brush.verticalGradient(
                                                        colors = listOf(MaterialTheme.colorScheme.secondary, MaterialTheme.colorScheme.secondary.copy(alpha = 0.8f))
                                                    ),
                                                    shape = androidx.compose.foundation.shape.RoundedCornerShape(topStart = 4.dp, topEnd = 4.dp)
                                                )
                                        )
                                        Spacer(modifier = Modifier.height(4.dp))
                                        Text("SEG", style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp), color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Recent Transactions
            item {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Text("Transações Recentes", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.onSurface)
                    Text("Ver tudo", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.secondary)
                }
            }

            item {
                TransactionItem(
                    title = "Entrega #8921",
                    date = "Hoje, 14:35",
                    amount = "+ R$ 24,90",
                    isPositive = true,
                    status = "Concluído",
                    icon = Icons.Outlined.Payments
                )
            }
            
            item {
                TransactionItem(
                    title = "Saque Solicitado",
                    date = "Ontem, 09:12",
                    amount = "- R$ 450,00",
                    isPositive = false,
                    status = "Processando",
                    icon = Icons.Outlined.AccountBalanceWallet
                )
            }
            
            item {
                TransactionItem(
                    title = "Entrega #8915",
                    date = "Ontem, 18:45",
                    amount = "+ R$ 18,50",
                    isPositive = true,
                    status = "Concluído",
                    icon = Icons.Outlined.Payments
                )
            }
            
            item {
                TransactionItem(
                    title = "Entrega #8912",
                    date = "22 Out, 11:20",
                    amount = "+ R$ 32,00",
                    isPositive = true,
                    status = "Concluído",
                    icon = Icons.Outlined.Payments
                )
            }
        }
    }
}

@Composable
private fun FilterButton(text: String, selected: Boolean, modifier: Modifier = Modifier) {
    Surface(
        color = if (selected) MaterialTheme.colorScheme.secondary else Color.Transparent,
        contentColor = if (selected) MaterialTheme.colorScheme.onSecondary else MaterialTheme.colorScheme.onSurfaceVariant,
        shape = NevesGoShapes.small,
        modifier = modifier
    ) {
        Box(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp), contentAlignment = Alignment.Center) {
            Text(text, style = MaterialTheme.typography.labelSmall)
        }
    }
}

@Composable
private fun TransactionItem(title: String, date: String, amount: String, isPositive: Boolean, status: String, icon: androidx.compose.ui.graphics.vector.ImageVector) {
    Surface(
        shape = NevesGoShapes.medium,
        color = MaterialTheme.colorScheme.surfaceContainerLow,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(modifier = Modifier.padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(modifier = Modifier.size(48.dp).background(MaterialTheme.colorScheme.surfaceContainerHighest, CircleShape), contentAlignment = Alignment.Center) {
                    Icon(icon, contentDescription = null, tint = if (isPositive) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.primary)
                }
                Column {
                    Text(title, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurface)
                    Text(date, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(amount, style = DataMono, color = if (isPositive) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.onSurface)
                Surface(
                    shape = PillShape,
                    color = if (status == "Concluído") MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.surfaceContainerHigh,
                    modifier = Modifier.padding(top = 4.dp)
                ) {
                    Text(
                        status,
                        style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp),
                        color = if (status == "Concluído") MaterialTheme.colorScheme.onSecondary else MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
                    )
                }
            }
        }
    }
}
