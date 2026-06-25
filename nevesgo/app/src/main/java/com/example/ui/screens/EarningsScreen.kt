package com.example.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ReceiptLong
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.ArrowDownward
import androidx.compose.material.icons.filled.ArrowUpward
import androidx.compose.material.icons.filled.LocalMall
import androidx.compose.material.icons.filled.Paid
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.example.MyApplication
import com.example.domain.models.WalletBalanceResponse
import com.example.domain.models.WalletTransactionItem
import kotlinx.coroutines.launch
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import kotlin.math.absoluteValue

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EarningsScreen(navController: NavController) {
    FinanceDashboardScreen(
        title = "Ganhos",
        showBack = false,
        onBack = { navController.popBackStack() }
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FinanceDashboardScreen(
    title: String,
    showBack: Boolean,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val apiService = remember { (context.applicationContext as MyApplication).container.driverApiService }
    val scope = rememberCoroutineScope()

    var wallet by remember { mutableStateOf<WalletBalanceResponse?>(null) }
    var transactions by remember { mutableStateOf<List<WalletTransactionItem>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var isWithdrawing by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var infoMessage by remember { mutableStateOf<String?>(null) }
    var pixKey by remember { mutableStateOf("") }
    var withdrawAmount by remember { mutableStateOf("") }

    fun refresh() {
        scope.launch {
            isLoading = true
            errorMessage = null
            try {
                val walletResponse = apiService.getWalletBalance()
                val transactionsResponse = apiService.getWalletTransactions(limit = 50, offset = 0)
                if (walletResponse.isSuccessful) {
                    wallet = walletResponse.body()
                } else {
                    errorMessage = "Nao foi possivel carregar o saldo da carteira."
                }
                if (transactionsResponse.isSuccessful) {
                    transactions = transactionsResponse.body()?.items.orEmpty()
                } else if (errorMessage == null) {
                    errorMessage = "Nao foi possivel carregar o historico financeiro."
                }
            } catch (_: Exception) {
                errorMessage = "Falha ao sincronizar os dados financeiros."
            } finally {
                isLoading = false
            }
        }
    }

    fun requestWithdrawal() {
        val amountCents = parseCurrencyInputToCents(withdrawAmount)
        if (pixKey.isBlank() || amountCents <= 0) {
            errorMessage = "Informe uma chave Pix e um valor valido para saque."
            return
        }
        scope.launch {
            isWithdrawing = true
            errorMessage = null
            val response = try {
                apiService.requestWalletWithdrawal(
                    com.example.domain.models.WithdrawalRequestPayload(
                        amountCents = amountCents,
                        pixKey = pixKey
                    )
                )
            } catch (_: Exception) {
                null
            }
            if (response?.isSuccessful == true) {
                val body = response.body()
                infoMessage = "Saque solicitado com status ${body?.status ?: "PENDING"}."
                withdrawAmount = ""
                refresh()
            } else {
                errorMessage = "Falha ao solicitar saque da carteira."
            }
            isWithdrawing = false
        }
    }

    LaunchedEffect(Unit) {
        refresh()
    }

    val credits = transactions.filter { it.isCredit() }.sumOf { it.amountCents }
    val debits = transactions.filterNot { it.isCredit() }.sumOf { it.amountCents }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(title, fontWeight = FontWeight.Bold) },
                navigationIcon = if (showBack) {
                    {
                        IconButton(onClick = onBack) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Voltar")
                        }
                    }
                } else {
                    {}
                },
                actions = {
                    IconButton(onClick = { refresh() }) {
                        Icon(Icons.Filled.Refresh, contentDescription = "Atualizar")
                    }
                }
            )
        }
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                if (!infoMessage.isNullOrBlank() || !errorMessage.isNullOrBlank()) {
                    Text(
                        text = errorMessage ?: infoMessage.orEmpty(),
                        color = if (errorMessage != null) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary
                    )
                }
            }

            if (isLoading) {
                item {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 40.dp),
                        horizontalArrangement = Arrangement.Center
                    ) {
                        CircularProgressIndicator()
                    }
                }
            } else {
                item {
                    SummaryCard(
                        balanceCents = wallet?.balanceCents ?: 0,
                        updatedAt = wallet?.updatedAt
                    )
                }
                item {
                    EarningsBreakdown(
                        creditsCents = credits,
                        debitsCents = debits,
                        balanceCents = wallet?.balanceCents ?: 0
                    )
                }
                item {
                    WithdrawalCard(
                        pixKey = pixKey,
                        withdrawAmount = withdrawAmount,
                        onPixKeyChange = {
                            pixKey = it
                            errorMessage = null
                        },
                        onWithdrawAmountChange = {
                            withdrawAmount = it
                            errorMessage = null
                        },
                        onWithdraw = { requestWithdrawal() },
                        inFlight = isWithdrawing
                    )
                }
                item {
                    Text(
                        "Historico de Transacoes",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                }
                if (transactions.isEmpty()) {
                    item {
                        Text(
                            "Nenhuma transacao encontrada para esta carteira.",
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                } else {
                    items(transactions, key = { it.id }) { transaction ->
                        TransactionItem(transaction = transaction)
                    }
                }
            }
        }
    }
}

@Composable
fun SummaryCard(balanceCents: Int, updatedAt: String?) {
    com.example.ui.components.DriverInfoCard {
        Text("Saldo disponivel na carteira", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(
            formatCurrency(balanceCents),
            style = MaterialTheme.typography.displayMedium,
            fontWeight = FontWeight.Black,
            color = MaterialTheme.colorScheme.primary
        )
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = 8.dp)) {
            Icon(
                Icons.Filled.AccountBalanceWallet,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(16.dp)
            )
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                "Atualizado em ${updatedAt?.toDisplayDateTime() ?: "sincronizacao indisponivel"}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

@Composable
fun EarningsBreakdown(creditsCents: Int, debitsCents: Int, balanceCents: Int) {
    com.example.ui.components.DriverInfoCard {
        Text(
            "Detalhamento financeiro recente",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(bottom = 12.dp)
        )
        BreakdownRow("Entradas", formatCurrency(creditsCents))
        BreakdownRow("Saidas", formatCurrency(debitsCents), isNegative = true)
        HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp))
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("Saldo atual", fontWeight = FontWeight.Bold, fontSize = 18.sp)
            Text(
                formatCurrency(balanceCents),
                fontWeight = FontWeight.Black,
                fontSize = 18.sp,
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}

@Composable
fun WithdrawalCard(
    pixKey: String,
    withdrawAmount: String,
    onPixKeyChange: (String) -> Unit,
    onWithdrawAmountChange: (String) -> Unit,
    onWithdraw: () -> Unit,
    inFlight: Boolean
) {
    com.example.ui.components.DriverInfoCard {
        Text("Solicitar saque", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(12.dp))
        OutlinedTextField(
            value = pixKey,
            onValueChange = onPixKeyChange,
            label = { Text("Chave Pix") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        Spacer(modifier = Modifier.height(12.dp))
        OutlinedTextField(
            value = withdrawAmount,
            onValueChange = onWithdrawAmountChange,
            label = { Text("Valor do saque") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = KeyboardType.Number)
        )
        Spacer(modifier = Modifier.height(12.dp))
        Button(
            onClick = onWithdraw,
            enabled = !inFlight,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(if (inFlight) "Solicitando..." else "Solicitar saque")
        }
    }
}

@Composable
fun BreakdownRow(label: String, value: String, isNegative: Boolean = false) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, color = if (isNegative) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface)
    }
}

@Composable
fun TransactionItem(transaction: WalletTransactionItem) {
    val isCredit = transaction.isCredit()
    val icon = when (transaction.category.uppercase()) {
        "PAYOUT" -> Icons.Filled.ArrowDownward
        "BONUS" -> Icons.Filled.Paid
        "PENALTY" -> Icons.Filled.LocalMall
        else -> Icons.AutoMirrored.Filled.ReceiptLong
    }
    Card(
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 8.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Surface(
                shape = RoundedCornerShape(8.dp),
                color = if (isCredit) {
                    MaterialTheme.colorScheme.secondary.copy(alpha = 0.1f)
                } else {
                    MaterialTheme.colorScheme.error.copy(alpha = 0.1f)
                },
                modifier = Modifier.size(40.dp)
            ) {
                Icon(
                    icon,
                    contentDescription = null,
                    tint = if (isCredit) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.error,
                    modifier = Modifier.padding(8.dp)
                )
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(transaction.category.toDisplayCategory(), fontWeight = FontWeight.Bold)
                Text(
                    "${transaction.createdAt.toDisplayDateTime()} • ${transaction.taxCategory}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Text(
                text = buildString {
                    append(if (isCredit) "+ " else "- ")
                    append(formatCurrency(transaction.amountCents.absoluteValue))
                },
                fontWeight = FontWeight.Bold,
                color = if (isCredit) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.error
            )
        }
    }
}

private fun WalletTransactionItem.isCredit(): Boolean {
    return category.uppercase() !in setOf("PAYOUT", "PENALTY")
}

private fun String.toDisplayCategory(): String {
    return lowercase()
        .split("_")
        .joinToString(" ") { part -> part.replaceFirstChar { it.titlecase() } }
}

private fun String.toDisplayDateTime(): String {
    return try {
        OffsetDateTime.parse(this).format(DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm"))
    } catch (_: Exception) {
        this
    }
}

private fun formatCurrency(amountCents: Int): String {
    return "R$ ${String.format("%.2f", amountCents / 100.0)}"
}

private fun parseCurrencyInputToCents(input: String): Int {
    val sanitized = input
        .replace("R$", "", ignoreCase = true)
        .replace(".", "")
        .replace(",", ".")
        .trim()
    return (sanitized.toDoubleOrNull()?.times(100))?.toInt() ?: 0
}
