package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.*
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun JourneyDetailsScreen(navController: NavController) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Jornada de 25 de Outubro", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = { }) { Icon(Icons.Filled.Share, contentDescription = "Share") }
                }
            )
        },
        bottomBar = {
            Button(
                onClick = { navController.popBackStack() },
                modifier = Modifier.fillMaxWidth().padding(16.dp).height(56.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFFA1414))
            ) {
                Icon(Icons.Filled.PowerSettingsNew, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Finalizar Jornada", fontSize = 16.sp, fontWeight = FontWeight.Bold)
            }
        }
    ) { padding ->
        LazyColumn(modifier = Modifier.padding(padding).fillMaxSize().padding(horizontal = 16.dp)) {
            item {
                Surface(shape = CircleShape, color = Color(0xFF28A745).copy(alpha = 0.2f), modifier = Modifier.padding(vertical = 12.dp)) {
                    Text("Em Andamento", color = Color(0xFF28A745), fontWeight = FontWeight.Bold, modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp), fontSize = 12.sp)
                }
                
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Card(modifier = Modifier.weight(1f), shape = RoundedCornerShape(12.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("Tempo Trabalhado", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("08h 45m", fontWeight = FontWeight.Bold, fontSize = 20.sp)
                        }
                    }
                    Card(modifier = Modifier.weight(1f), shape = RoundedCornerShape(12.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("Total de Entregas", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("12", fontWeight = FontWeight.Bold, fontSize = 20.sp)
                        }
                    }
                }
                Spacer(modifier = Modifier.height(12.dp))
                Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(12.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("Ganhos da Jornada", fontSize = 14.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("R$ 215,50", fontWeight = FontWeight.Bold, fontSize = 32.sp, color = Color(0xFFFA1414))
                    }
                }
                
                Spacer(modifier = Modifier.height(32.dp))
                Text("Lista de Entregas da Jornada", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                Spacer(modifier = Modifier.height(12.dp))
                
                DeliveryListItem("Pedido #BR5491", "Av. Paulista, 1578", "R$ 18,50", "14:32", true)
                Spacer(modifier = Modifier.height(8.dp))
                DeliveryListItem("Pedido #BR5490", "R. Augusta, 900", "R$ 15,00", "13:55", true)
                Spacer(modifier = Modifier.height(8.dp))
                DeliveryListItem("Pedido #BR5489", "Lgo. da Batata", "Cancelado", "13:10", false)
            }
        }
    }
}

@Composable
fun DeliveryListItem(title: String, subtitle: String, value: String, time: String, isSuccess: Boolean) {
    Card(shape = RoundedCornerShape(12.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), modifier = Modifier.fillMaxWidth()) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(shape = CircleShape, color = if(isSuccess) Color(0xFFFA1414).copy(alpha=0.1f) else Color(0xFFDC3545).copy(alpha=0.1f), modifier = Modifier.size(48.dp)) {
                Icon(if(isSuccess) Icons.AutoMirrored.Filled.ReceiptLong else Icons.Filled.Cancel, contentDescription = null, tint = if(isSuccess) Color(0xFFFA1414) else Color(0xFFDC3545), modifier = Modifier.padding(12.dp))
            }
            Spacer(modifier = Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(title, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                Text(subtitle, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 14.sp)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(value, fontWeight = FontWeight.Bold, color = if(isSuccess) Color(0xFF28A745) else Color(0xFFDC3545))
                Text(time, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 12.sp)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PaymentsScreen(navController: NavController) {
    FinanceDashboardScreen(
        title = "Pagamentos",
        showBack = true,
        onBack = { navController.popBackStack() }
    )
}

@Composable
fun PaymentItem(amount: String, status: String, period: String, isPaid: Boolean) {
    Card(shape = RoundedCornerShape(12.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), modifier = Modifier.fillMaxWidth()) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(modifier = Modifier.width(4.dp).height(48.dp).background(if(isPaid) Color(0xFF28A745) else Color(0xFFFFC107), RoundedCornerShape(2.dp)))
            Spacer(modifier = Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                    Text(amount, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                    if (isPaid) {
                        Text("Ver Comprovante", color = Color(0xFFFA1414), fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    } else {
                        Icon(Icons.Filled.ChevronRight, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                Spacer(modifier = Modifier.height(4.dp))
                Text(status, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 14.sp)
                Text(period, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 14.sp)
            }
        }
    }
}
