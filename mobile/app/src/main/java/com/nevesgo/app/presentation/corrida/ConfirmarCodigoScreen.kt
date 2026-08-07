package com.nevesgo.app.presentation.corrida

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import com.nevesgo.app.ui.theme.*
import androidx.compose.foundation.clickable
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun ConfirmarCodigoScreen() {
    var isProcessing by remember { mutableStateOf(false) }
    var isSuccess by remember { mutableStateOf(false) }
    val coroutineScope = rememberCoroutineScope()

    Scaffold(
        topBar = {
            Surface(
                color = MaterialTheme.colorScheme.surfaceContainerLowest,
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconButton(onClick = { /* TODO */ }, modifier = Modifier.padding(end = 8.dp)) {
                        Icon(Icons.Outlined.ArrowBack, contentDescription = "Voltar", tint = MaterialTheme.colorScheme.onSurface)
                    }
                    Text("Confirmação de Entrega", style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurface)
                }
            }
        },
        bottomBar = {
            // Excluding BottomNavBar as it is a Focused View (Form-heavy/Process screen) per Rule 2
            Box(
                modifier = Modifier.fillMaxWidth().padding(16.dp),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = "Localização rastreada para segurança da entrega",
                    style = MaterialTheme.typography.labelSmall.copy(fontStyle = androidx.compose.ui.text.font.FontStyle.Italic),
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        },
        modifier = Modifier.fillMaxSize()
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.surfaceContainerLowest)
                .padding(innerPadding)
                .padding(horizontal = 24.dp)
                .padding(top = 40.dp, bottom = 80.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Delivery Visual Context
            Box(
                modifier = Modifier
                    .size(96.dp)
                    .background(SecondaryFixed, CircleShape)
                    .padding(bottom = 32.dp),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Outlined.Inventory2, contentDescription = null, tint = MaterialTheme.colorScheme.secondary, modifier = Modifier.size(48.dp))
            }
            Spacer(modifier = Modifier.height(32.dp))

            // Order Identification
            Text("Pedido #F8921", style = MaterialTheme.typography.headlineLarge, color = MaterialTheme.colorScheme.primary)
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "Solicite o código ao cliente para finalizar a entrega com segurança.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
                modifier = Modifier.widthIn(max = 280.dp)
            )
            Spacer(modifier = Modifier.height(32.dp))

            // Verification Code Input (OTP)
            OtpInputRow()
            Spacer(modifier = Modifier.height(24.dp))
            Text(
                text = "Problemas com o código?",
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.secondary,
                modifier = Modifier.clickable { /* TODO */ }
            )
            Spacer(modifier = Modifier.height(48.dp))

            // Customer Preview Card
            Surface(
                shape = NevesGoShapes.medium,
                color = MaterialTheme.colorScheme.surfaceContainer,
                modifier = Modifier.fillMaxWidth().padding(bottom = 40.dp)
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .size(48.dp)
                            .background(MaterialTheme.colorScheme.surfaceContainerHighest, CircleShape)
                            .border(2.dp, MaterialTheme.colorScheme.surfaceContainerHighest, CircleShape),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(Icons.Outlined.Person, contentDescription = "Cliente", tint = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Text("CLIENTE", style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 0.05.em), color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("Juliana Martins", style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurface)
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Surface(shape = CircleShape, color = MaterialTheme.colorScheme.surfaceContainerHighest, onClick = { /* TODO */ }, modifier = Modifier.size(40.dp)) {
                            Box(contentAlignment = Alignment.Center) { Icon(Icons.Outlined.Chat, contentDescription = "Chat", tint = MaterialTheme.colorScheme.primary) }
                        }
                        Surface(shape = CircleShape, color = MaterialTheme.colorScheme.surfaceContainerHighest, onClick = { /* TODO */ }, modifier = Modifier.size(40.dp)) {
                            Box(contentAlignment = Alignment.Center) { Icon(Icons.Outlined.Call, contentDescription = "Ligar", tint = MaterialTheme.colorScheme.primary) }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.weight(1f))

            // Primary Action
            Button(
                onClick = {
                    if (!isSuccess) {
                        coroutineScope.launch {
                            isProcessing = true
                            delay(1500)
                            isProcessing = false
                            isSuccess = true
                        }
                    }
                },
                enabled = !isProcessing,
                modifier = Modifier.fillMaxWidth().height(56.dp),
                shape = NevesGoShapes.medium,
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isSuccess) Success else MaterialTheme.colorScheme.primary,
                    contentColor = if (isSuccess) OnSuccess else MaterialTheme.colorScheme.onPrimary,
                    disabledContainerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.8f),
                    disabledContentColor = MaterialTheme.colorScheme.onPrimary
                ),
                elevation = ButtonDefaults.buttonElevation(defaultElevation = 8.dp)
            ) {
                if (isProcessing) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                        CircularProgressIndicator(color = MaterialTheme.colorScheme.onPrimary, strokeWidth = 2.dp, modifier = Modifier.size(20.dp))
                        Text("Processando...", style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold))
                    }
                } else if (isSuccess) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Outlined.DoneAll, contentDescription = null)
                        Text("Sucesso!", style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold))
                    }
                } else {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                        Text("Confirmar Entrega", style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold))
                        Icon(Icons.Outlined.CheckCircle, contentDescription = null)
                    }
                }
            }
        }
    }
}

@Composable
fun OtpInputRow() {
    val otpValues = remember { mutableStateListOf("", "", "", "") }
    val focusRequesters = List(4) { FocusRequester() }

    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        for (i in 0..3) {
            OutlinedTextField(
                value = otpValues[i],
                onValueChange = { newValue ->
                    if (newValue.length <= 1) {
                        otpValues[i] = newValue
                        if (newValue.isNotEmpty() && i < 3) {
                            focusRequesters[i + 1].requestFocus()
                        }
                    }
                },
                modifier = Modifier
                    .width(56.dp)
                    .height(64.dp)
                    .focusRequester(focusRequesters[i]),
                textStyle = DataMono.copy(fontSize = 24.sp, textAlign = TextAlign.Center),
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = MaterialTheme.colorScheme.surfaceContainerLow,
                    unfocusedContainerColor = MaterialTheme.colorScheme.surfaceContainerLow,
                    focusedBorderColor = MaterialTheme.colorScheme.secondary,
                    unfocusedBorderColor = MaterialTheme.colorScheme.outlineVariant,
                    focusedTextColor = MaterialTheme.colorScheme.onSurface,
                    unfocusedTextColor = MaterialTheme.colorScheme.onSurface
                ),
                shape = androidx.compose.foundation.shape.RoundedCornerShape(topStart = 8.dp, topEnd = 8.dp, bottomStart = 0.dp, bottomEnd = 0.dp) // rounded-t-lg
            )
        }
    }
}
