package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.ChatBubble
import androidx.compose.material.icons.filled.LocalShipping
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Storefront
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
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.example.MyApplication
import com.example.domain.models.CommunicationMessageItem
import com.example.domain.models.CommunicationMessageRequest
import com.example.domain.models.CommunicationThreadItem
import kotlinx.coroutines.launch
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NotificationsScreen(navController: NavController) {
    val context = LocalContext.current
    val apiService = remember { (context.applicationContext as MyApplication).container.driverApiService }
    val scope = rememberCoroutineScope()

    var threads by remember { mutableStateOf<List<CommunicationThreadItem>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    fun refresh() {
        scope.launch {
            isLoading = true
            errorMessage = null
            try {
                val response = apiService.getCommunicationThreads()
                if (response.isSuccessful) {
                    threads = response.body().orEmpty()
                } else {
                    errorMessage = "Nao foi possivel carregar a caixa de comunicacao."
                }
            } catch (_: Exception) {
                errorMessage = "Falha ao sincronizar as conversas com o backend."
            } finally {
                isLoading = false
            }
        }
    }

    LaunchedEffect(Unit) {
        refresh()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Comunicacao", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Voltar")
                    }
                },
                actions = {
                    IconButton(onClick = { refresh() }) {
                        Icon(Icons.Filled.Refresh, contentDescription = "Atualizar")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Threads", fontSize = 24.sp, fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.width(8.dp))
                    Surface(
                        shape = CircleShape,
                        color = Color(0xFFFA1414).copy(alpha = 0.12f)
                    ) {
                        Text(
                            "${threads.size} ativa(s)",
                            color = Color(0xFFFA1414),
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
                TextButton(onClick = { refresh() }) {
                    Text("Atualizar")
                }
            }

            when {
                isLoading -> {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(24.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator()
                    }
                }

                !errorMessage.isNullOrBlank() -> {
                    Text(
                        text = errorMessage.orEmpty(),
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp)
                    )
                }

                threads.isEmpty() -> {
                    Text(
                        text = "Nenhuma thread operacional encontrada para este entregador.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp)
                    )
                }

                else -> {
                    LazyColumn(contentPadding = PaddingValues(vertical = 8.dp)) {
                        items(threads, key = { it.threadId }) { thread ->
                            CommunicationThreadCard(
                                thread = thread,
                                onClick = { navController.navigate("chat/${thread.threadId}") }
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun CommunicationThreadCard(
    thread: CommunicationThreadItem,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .background(MaterialTheme.colorScheme.surface)
            .padding(16.dp)
    ) {
        Surface(
            shape = RoundedCornerShape(8.dp),
            color = MaterialTheme.colorScheme.surfaceVariant,
            modifier = Modifier.size(48.dp)
        ) {
            Icon(
                imageVector = thread.toThreadIcon(),
                contentDescription = null,
                modifier = Modifier.padding(12.dp)
            )
        }
        Spacer(modifier = Modifier.width(16.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = thread.subject?.ifBlank { null }
                    ?: thread.orderId?.let { "Thread da ordem ${it.take(8)}" }
                    ?: "Canal operacional",
                fontWeight = FontWeight.Bold,
                fontSize = 16.sp
            )
            Text(
                text = buildString {
                    append(thread.sourceType.uppercase())
                    append(" • ")
                    append(thread.status.uppercase())
                    thread.updatedAt?.let {
                        append(" • ")
                        append(it.toDisplayDateTime())
                    }
                },
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontSize = 14.sp
            )
        }
        Icon(
            Icons.Filled.ChatBubble,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.primary
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    navController: NavController,
    threadId: String?
) {
    val context = LocalContext.current
    val apiService = remember { (context.applicationContext as MyApplication).container.driverApiService }
    val scope = rememberCoroutineScope()

    var message by remember { mutableStateOf("") }
    var messages by remember { mutableStateOf<List<CommunicationMessageItem>>(emptyList()) }
    var thread by remember { mutableStateOf<CommunicationThreadItem?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var isSending by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    fun refresh() {
        if (threadId.isNullOrBlank()) {
            isLoading = false
            errorMessage = "Thread de comunicacao nao informada."
            return
        }
        scope.launch {
            isLoading = true
            errorMessage = null
            try {
                val threadsResponse = apiService.getCommunicationThreads()
                if (threadsResponse.isSuccessful) {
                    thread = threadsResponse.body().orEmpty().firstOrNull { it.threadId == threadId }
                }
                val messagesResponse = apiService.getThreadMessages(threadId)
                if (messagesResponse.isSuccessful) {
                    messages = messagesResponse.body().orEmpty()
                } else {
                    errorMessage = "Nao foi possivel carregar as mensagens da thread."
                }
            } catch (_: Exception) {
                errorMessage = "Falha ao sincronizar a conversa com o backend."
            } finally {
                isLoading = false
            }
        }
    }

    fun sendMessage() {
        val payload = message.trim()
        if (threadId.isNullOrBlank() || payload.isBlank()) return
        scope.launch {
            isSending = true
            errorMessage = null
            val response = try {
                apiService.sendThreadMessage(
                    threadId = threadId,
                    payload = CommunicationMessageRequest(message = payload)
                )
            } catch (_: Exception) {
                null
            }
            if (response?.isSuccessful == true) {
                message = ""
                refresh()
            } else {
                errorMessage = "Falha ao enviar mensagem para a thread."
            }
            isSending = false
        }
    }

    LaunchedEffect(threadId) {
        refresh()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            thread?.subject?.ifBlank { null }
                                ?: thread?.orderId?.let { "Ordem ${it.take(8)}" }
                                ?: "Conversa operacional",
                            fontWeight = FontWeight.Bold,
                            fontSize = 16.sp
                        )
                        Text(
                            thread?.status?.uppercase() ?: "SEM STATUS",
                            color = Color(0xFF28A745),
                            fontSize = 12.sp
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Voltar")
                    }
                },
                actions = {
                    IconButton(onClick = { refresh() }) {
                        Icon(Icons.Filled.Refresh, contentDescription = "Atualizar")
                    }
                }
            )
        },
        bottomBar = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
            ) {
                if (!errorMessage.isNullOrBlank()) {
                    Text(
                        text = errorMessage.orEmpty(),
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier.padding(bottom = 8.dp)
                    )
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    OutlinedTextField(
                        value = message,
                        onValueChange = { message = it },
                        placeholder = { Text("Digite sua mensagem...") },
                        modifier = Modifier.weight(1f),
                        shape = CircleShape,
                        enabled = !isSending && !threadId.isNullOrBlank()
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Surface(shape = CircleShape, color = Color(0xFFFA1414)) {
                        IconButton(
                            onClick = { sendMessage() },
                            enabled = !isSending && message.isNotBlank() && !threadId.isNullOrBlank()
                        ) {
                            Icon(
                                Icons.AutoMirrored.Filled.Send,
                                contentDescription = "Enviar",
                                tint = Color.White
                            )
                        }
                    }
                }
            }
        }
    ) { padding ->
        when {
            isLoading -> {
                Box(
                    modifier = Modifier
                        .padding(padding)
                        .fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator()
                }
            }

            messages.isEmpty() -> {
                Column(
                    modifier = Modifier
                        .padding(padding)
                        .fillMaxSize()
                        .padding(16.dp)
                ) {
                    Text(
                        "Nenhuma mensagem encontrada nesta thread.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            else -> {
                LazyColumn(
                    modifier = Modifier
                        .padding(padding)
                        .fillMaxSize()
                        .padding(16.dp),
                    contentPadding = PaddingValues(bottom = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    item {
                        Text(
                            "HISTORICO DE MENSAGENS",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                    items(messages, key = { it.messageId }) { item ->
                        MessageBubble(item)
                    }
                }
            }
        }
    }
}

@Composable
private fun MessageBubble(item: CommunicationMessageItem) {
    val isDriver = item.senderType.uppercase() == "DRIVER"
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (isDriver) Arrangement.End else Arrangement.Start
    ) {
        if (!isDriver) {
            Surface(
                shape = CircleShape,
                color = MaterialTheme.colorScheme.surfaceVariant,
                modifier = Modifier.size(32.dp)
            ) {
                Icon(
                    imageVector = if (item.senderName.contains("loja", ignoreCase = true)) {
                        Icons.Filled.Storefront
                    } else {
                        Icons.Filled.ChatBubble
                    },
                    contentDescription = null,
                    modifier = Modifier.padding(8.dp)
                )
            }
            Spacer(modifier = Modifier.width(8.dp))
        }

        Surface(
            shape = RoundedCornerShape(
                topStart = 12.dp,
                topEnd = 12.dp,
                bottomStart = if (isDriver) 12.dp else 0.dp,
                bottomEnd = if (isDriver) 0.dp else 12.dp
            ),
            color = if (isDriver) Color(0xFFFA1414) else MaterialTheme.colorScheme.surfaceVariant
        ) {
            Column(modifier = Modifier.padding(12.dp)) {
                if (!isDriver) {
                    Text(
                        item.senderName,
                        fontWeight = FontWeight.Bold,
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                }
                Text(
                    item.message,
                    color = if (isDriver) Color.White else MaterialTheme.colorScheme.onSurface
                )
                item.createdAt?.let {
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        it.toDisplayDateTime(),
                        fontSize = 11.sp,
                        color = if (isDriver) Color.White.copy(alpha = 0.8f) else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}

private fun CommunicationThreadItem.toThreadIcon(): ImageVector {
    return when {
        sourceType.equals("STORE", ignoreCase = true) -> Icons.Filled.Storefront
        orderId != null -> Icons.Filled.LocalShipping
        else -> Icons.Filled.ChatBubble
    }
}

private fun String.toDisplayDateTime(): String {
    return try {
        OffsetDateTime.parse(this).format(DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm"))
    } catch (_: Exception) {
        this
    }
}
