package com.example.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.BuildConfig
import com.example.ui.theme.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody

private val Red = Color(0xFFE53935)

private val fieldColors
    @Composable get() = OutlinedTextFieldDefaults.colors(
        unfocusedBorderColor = Color(0xFFE0E0E0),
        focusedBorderColor = Red,
        unfocusedContainerColor = Color(0xFFF5F5F5),
        focusedContainerColor = Color(0xFFFFF8F8)
    )

@Composable
private fun SectionTitle(text: String) {
    Text(
        text = text,
        fontSize = 18.sp,
        fontWeight = FontWeight.Bold,
        color = Color(0xFF1A1A1A),
        modifier = Modifier.padding(top = 16.dp, bottom = 8.dp)
    )
}

@Composable
private fun FieldLabel(text: String) {
    Text(
        text = text,
        fontSize = 13.sp,
        fontWeight = FontWeight.Medium,
        color = Color(0xFF757575),
        modifier = Modifier.padding(bottom = 4.dp)
    )
}

@Composable
private fun StyledField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    keyboardOptions: androidx.compose.foundation.text.KeyboardOptions = androidx.compose.foundation.text.KeyboardOptions.Default
) {
    val localFieldColors = OutlinedTextFieldDefaults.colors(
        unfocusedBorderColor = Color(0xFFE0E0E0),
        focusedBorderColor = ExpressoRed,
        unfocusedContainerColor = Color(0xFFF9F9F9),
        focusedContainerColor = Color.White,
        focusedTextColor = Color(0xFF1A1A1A),
        unfocusedTextColor = Color(0xFF1A1A1A)
    )
    Column(modifier = modifier) {
        FieldLabel(label)
        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            shape = RoundedCornerShape(16.dp),
            colors = localFieldColors,
            keyboardOptions = keyboardOptions
        )
    }
}

@Composable
private fun DropdownField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    options: List<String>,
    modifier: Modifier = Modifier
) {
    var expanded by remember { mutableStateOf(false) }
    val localFieldColors = OutlinedTextFieldDefaults.colors(
        unfocusedBorderColor = Color(0xFFE0E0E0),
        focusedBorderColor = ExpressoRed,
        unfocusedContainerColor = Color(0xFFF9F9F9),
        focusedContainerColor = Color.White,
        focusedTextColor = Color(0xFF1A1A1A),
        unfocusedTextColor = Color(0xFF1A1A1A)
    )
    Column(modifier = modifier) {
        FieldLabel(label)
        Box {
            OutlinedTextField(
                value = value,
                onValueChange = {},
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { expanded = true },
                readOnly = true,
                singleLine = true,
                shape = RoundedCornerShape(16.dp),
                colors = localFieldColors,
                trailingIcon = {
                    Icon(Icons.Default.ArrowDropDown, contentDescription = null, tint = Color(0xFF757575))
                },
                placeholder = { Text("Selecione", color = Color(0xFF999999)) }
            )
            DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                options.forEach { option ->
                    DropdownMenuItem(
                        text = { Text(option) },
                        onClick = { onValueChange(option); expanded = false }
                    )
                }
            }
        }
    }
}

@Composable
private fun DocumentUploadField(label: String, selectedUri: android.net.Uri?, onUriSelected: (android.net.Uri?) -> Unit) {
    val pickerLauncher = androidx.activity.compose.rememberLauncherForActivityResult(
        contract = androidx.activity.result.contract.ActivityResultContracts.PickVisualMedia()
    ) { uri ->
        onUriSelected(uri)
    }

    Column(modifier = Modifier.fillMaxWidth()) {
        FieldLabel(label)
        OutlinedButton(
            onClick = {
                pickerLauncher.launch(
                    androidx.activity.result.PickVisualMediaRequest(
                        androidx.activity.result.contract.ActivityResultContracts.PickVisualMedia.ImageOnly
                    )
                )
            },
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp),
            shape = RoundedCornerShape(12.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, if (selectedUri != null) Color(0xFF4CAF50) else Color(0xFFE0E0E0)),
            colors = androidx.compose.material3.ButtonDefaults.outlinedButtonColors(
                containerColor = if (selectedUri != null) Color(0xFF4CAF50).copy(alpha = 0.1f) else Color.Transparent
            )
        ) {
            if (selectedUri != null) {
                Icon(Icons.Default.Check, contentDescription = null, tint = Color(0xFF4CAF50), modifier = Modifier.size(20.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text("Foto Selecionada", color = Color(0xFF4CAF50), fontWeight = androidx.compose.ui.text.font.FontWeight.Bold)
            } else {
                Icon(Icons.Default.CameraAlt, contentDescription = null, tint = Red, modifier = Modifier.size(20.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text("Enviar foto", color = Color(0xFF666666))
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RegisterScreen(
    onNavigateBack: () -> Unit
) {
    val scope = rememberCoroutineScope()
    var currentStep by rememberSaveable { mutableIntStateOf(0) }
    val totalSteps = 6

    val fieldColors = OutlinedTextFieldDefaults.colors(
        unfocusedBorderColor = Color(0xFFE0E0E0),
        focusedBorderColor = ExpressoRed,
        unfocusedContainerColor = Color(0xFFF9F9F9),
        focusedContainerColor = Color.White,
        focusedTextColor = Color(0xFF1A1A1A),
        unfocusedTextColor = Color(0xFF1A1A1A)
    )

    // Step 0: Dados Pessoais
    var nome by rememberSaveable { mutableStateOf("") }
    var sexo by rememberSaveable { mutableStateOf("") }
    var dataNascimento by rememberSaveable { mutableStateOf("") }
    var email by rememberSaveable { mutableStateOf("") }
    var telefone by rememberSaveable { mutableStateOf("") }
    var cpf by rememberSaveable { mutableStateOf("") }
    var cnpjMei by rememberSaveable { mutableStateOf("") }
    var senha by rememberSaveable { mutableStateOf("") }
    var confirmarSenha by rememberSaveable { mutableStateOf("") }
    var senhaVisible by rememberSaveable { mutableStateOf(false) }

    // Step 1: Endereço
    var cep by rememberSaveable { mutableStateOf("") }
    var logradouro by rememberSaveable { mutableStateOf("") }
    var numero by rememberSaveable { mutableStateOf("") }
    var complemento by rememberSaveable { mutableStateOf("") }
    var bairro by rememberSaveable { mutableStateOf("") }
    var cidade by rememberSaveable { mutableStateOf("") }
    var uf by rememberSaveable { mutableStateOf("") }
    var pontoReferencia by rememberSaveable { mutableStateOf("") }

    // Step 2: Veículo e CNH
    var tipoVeiculo by rememberSaveable { mutableStateOf("") }
    var numeroCnh by rememberSaveable { mutableStateOf("") }
    var validadeCnh by rememberSaveable { mutableStateOf("") }
    var placa by rememberSaveable { mutableStateOf("") }
    var modelo by rememberSaveable { mutableStateOf("") }
    var anoFabricacao by rememberSaveable { mutableStateOf("") }
    var anoExercicio by rememberSaveable { mutableStateOf("") }
    var ufEmplacamento by rememberSaveable { mutableStateOf("") }
    var renavam by rememberSaveable { mutableStateOf("") }
    var corVeiculo by rememberSaveable { mutableStateOf("") }

    // Step 3: Documentos (upload placeholders)
    var cnhUri by remember { mutableStateOf<android.net.Uri?>(null) }
    var crlvUri by remember { mutableStateOf<android.net.Uri?>(null) }
    var autonomiaUri by remember { mutableStateOf<android.net.Uri?>(null) }
    var residenciaUri by remember { mutableStateOf<android.net.Uri?>(null) }
    // Step 4: Pagamento
    var tipoChavePix by rememberSaveable { mutableStateOf("") }
    var chavePix by rememberSaveable { mutableStateOf("") }
    var cpfTitular by rememberSaveable { mutableStateOf("") }
    var nomeTitular by rememberSaveable { mutableStateOf("") }
    var numeroBanco by rememberSaveable { mutableStateOf("") }
    var numeroAgencia by rememberSaveable { mutableStateOf("") }
    var numeroConta by rememberSaveable { mutableStateOf("") }
    var tipoConta by rememberSaveable { mutableStateOf("") }

    // Step 5: Resumo
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var successMessage by remember { mutableStateOf<String?>(null) }
    var isSubmitting by remember { mutableStateOf(false) }

    val stepTitles = listOf(
        "Dados Pessoais", "Endereço", "Veículo", "Documentos", "Pagamento", "Resumo"
    )

    Scaffold(
        containerColor = Color.Transparent,
        topBar = {
            TopAppBar(
                title = { Text("Criar Conta", fontWeight = FontWeight.Bold, color = Color(0xFF1A1A1A)) },
                navigationIcon = {
                    IconButton(onClick = {
                        if (currentStep > 0) currentStep-- else onNavigateBack()
                    }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Voltar", tint = Color(0xFF1A1A1A))
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.White)
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.White)
                .padding(paddingValues)
                .imePadding()
        ) {
            // Progress bar
            val animatedProgress by animateFloatAsState(
                targetValue = (currentStep + 1).toFloat() / totalSteps,
                animationSpec = tween(durationMillis = 300)
            )
            LinearProgressIndicator(
                progress = { animatedProgress },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(4.dp),
                color = ExpressoRed,
                trackColor = Color(0xFF333333)
            )

            // Step indicator
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    "Etapa ${currentStep + 1} de $totalSteps",
                    fontSize = 12.sp,
                    color = Color(0xFF757575)
                )
                Text(
                    stepTitles[currentStep],
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = ExpressoRed
                )
            }

            Column(
                modifier = Modifier
                    .weight(1f)
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 24.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                when (currentStep) {
                    0 -> {
                        SectionTitle("Dados Pessoais")
                        StyledField(nome, { nome = it }, "Nome Completo")
                        DropdownField(
                            sexo, { sexo = it }, "Sexo",
                            listOf("Masculino", "Feminino", "Outro", "Prefiro não responder")
                        )
                        StyledField(
                            dataNascimento, 
                            { if (it.length <= 8) dataNascimento = it.filter { char -> char.isDigit() } }, 
                            "Data de Nascimento (Somente Números)",
                            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number)
                        )
                        StyledField(
                            email, 
                            { email = it }, 
                            "E-mail",
                            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Email)
                        )
                        StyledField(
                            telefone, 
                            { if (it.length <= 11) telefone = it.filter { char -> char.isDigit() } }, 
                            "Telefone (DDD + Número)",
                            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number)
                        )
                        StyledField(
                            cpf, 
                            { if (it.length <= 11) cpf = it.filter { char -> char.isDigit() } }, 
                            "CPF (Somente Números)",
                            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number)
                        )
                        StyledField(
                            cnpjMei, 
                            { if (it.length <= 14) cnpjMei = it.filter { char -> char.isDigit() } }, 
                            "CNPJ (Opcional - Somente Números)",
                            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number)
                        )

                        Spacer(modifier = Modifier.height(8.dp))
                        SectionTitle("Senha de Acesso")
                        Column {
                            FieldLabel("Senha")
                            OutlinedTextField(
                                value = senha,
                                onValueChange = { senha = it },
                                modifier = Modifier.fillMaxWidth(),
                                singleLine = true,
                                shape = RoundedCornerShape(16.dp),
                                colors = fieldColors,
                                visualTransformation = if (senhaVisible) VisualTransformation.None else PasswordVisualTransformation(),
                                trailingIcon = {
                                    IconButton(onClick = { senhaVisible = !senhaVisible }) {
                                        Icon(
                                            if (senhaVisible) Icons.Default.Visibility else Icons.Default.VisibilityOff,
                                            contentDescription = null,
                                            tint = Color(0xFF999999)
                                        )
                                    }
                                }
                            )
                        }

                        // Password strength indicator
                        if (senha.isNotEmpty()) {
                            val strength = when {
                                senha.length < 6 -> 0
                                senha.length < 8 -> 1
                                senha.any { it.isDigit() } && senha.any { it.isLetter() } -> 3
                                else -> 2
                            }
                            val strengthColors = listOf(Red, Color(0xFFFF9800), Color(0xFF4CAF50), Color(0xFF2E7D32))
                            val strengthLabels = listOf("Fraca", "Média", "Boa", "Forte")
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
                                horizontalArrangement = Arrangement.spacedBy(4.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                repeat(4) { i ->
                                    Box(
                                        modifier = Modifier
                                            .weight(1f)
                                            .height(4.dp)
                                            .background(
                                                if (i <= strength) strengthColors[strength] else Color(0xFFE0E0E0),
                                                RoundedCornerShape(2.dp)
                                            )
                                    )
                                }
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(strengthLabels[strength], fontSize = 12.sp, color = strengthColors[strength])
                            }
                        }

                        Column {
                            FieldLabel("Confirmar Senha")
                            OutlinedTextField(
                                value = confirmarSenha,
                                onValueChange = { confirmarSenha = it },
                                modifier = Modifier.fillMaxWidth(),
                                singleLine = true,
                                shape = RoundedCornerShape(16.dp),
                                colors = fieldColors,
                                visualTransformation = PasswordVisualTransformation()
                            )
                        }
                        if (confirmarSenha.isNotEmpty() && senha != confirmarSenha) {
                            Text("⚠ Senhas não conferem", color = Red, fontSize = 12.sp)
                        } else if (confirmarSenha.isNotEmpty() && senha == confirmarSenha) {
                            Text("✓ Senhas coincidem", color = Color(0xFF4CAF50), fontSize = 12.sp)
                        }
                    }

                    1 -> {
                        SectionTitle("Endereço")
                        StyledField(
                            cep, 
                            { if (it.length <= 8) cep = it.filter { char -> char.isDigit() } }, 
                            "CEP (Somente Números)",
                            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number)
                        )
                        StyledField(logradouro, { logradouro = it }, "Logradouro")
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            StyledField(numero, { numero = it }, "Número", Modifier.weight(1f), keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number))
                            StyledField(complemento, { complemento = it }, "Complemento", Modifier.weight(1f))
                        }
                        StyledField(bairro, { bairro = it }, "Bairro")
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            StyledField(cidade, { cidade = it }, "Cidade", Modifier.weight(2f))
                            DropdownField(
                                uf, { uf = it }, "UF",
                                listOf("AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"),
                                Modifier.weight(1f)
                            )
                        }
                        StyledField(pontoReferencia, { pontoReferencia = it }, "Ponto de Referência")
                    }

                    2 -> {
                        SectionTitle("Veículo e CNH")
                        DropdownField(
                            tipoVeiculo, { tipoVeiculo = it }, "Tipo de Veículo",
                            listOf("Moto", "Bike", "Carro", "Caminhão")
                        )
                        StyledField(numeroCnh, { numeroCnh = it }, "Número da CNH")
                        StyledField(validadeCnh, { validadeCnh = it }, "Validade da CNH (DD/MM/AAAA)")

                        Spacer(modifier = Modifier.height(8.dp))
                        SectionTitle("Dados do Veículo")
                        StyledField(placa, { placa = it }, "Placa")
                        StyledField(modelo, { modelo = it }, "Modelo")
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            StyledField(anoFabricacao, { anoFabricacao = it }, "Ano Fabricação", Modifier.weight(1f))
                            StyledField(anoExercicio, { anoExercicio = it }, "Ano Exercício", Modifier.weight(1f))
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            DropdownField(
                                ufEmplacamento, { ufEmplacamento = it }, "UF Emplacamento",
                                listOf("AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"),
                                Modifier.weight(1f)
                            )
                            StyledField(corVeiculo, { corVeiculo = it }, "Cor", Modifier.weight(1f))
                        }
                        StyledField(renavam, { renavam = it }, "Código RENAVAM")
                    }

                    3 -> {
                        SectionTitle("Documentos do Entregador")
                        Text("Passo 4: Documentos do Entregador", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = Color(0xFF1A1A1A), modifier = Modifier.padding(bottom = 16.dp))
                        DocumentUploadField("CNH", cnhUri) { cnhUri = it }
                        Spacer(modifier = Modifier.height(12.dp))
                        DocumentUploadField("CRLV", crlvUri) { crlvUri = it }
                        Spacer(modifier = Modifier.height(12.dp))
                        DocumentUploadField("Autonomia (Frente e Verso)", autonomiaUri) { autonomiaUri = it }
                        Spacer(modifier = Modifier.height(12.dp))
                        DocumentUploadField("Comprovante de Residência", residenciaUri) { residenciaUri = it }
                    }

                    4 -> {
                        SectionTitle("PIX")
                        DropdownField(
                            tipoChavePix, { tipoChavePix = it }, "Tipo de Chave",
                            listOf("CPF", "CNPJ", "E-mail", "Telefone", "Aleatória")
                        )
                        StyledField(chavePix, { chavePix = it }, "Chave PIX")

                        Spacer(modifier = Modifier.height(8.dp))
                        SectionTitle("Conta Corrente (Opcional)")
                        StyledField(
                            cpfTitular, 
                            { if (it.length <= 11) cpfTitular = it.filter { char -> char.isDigit() } }, 
                            "CPF do Titular (Somente Números)",
                            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number)
                        )
                        StyledField(nomeTitular, { nomeTitular = it }, "Nome do Titular")
                        StyledField(numeroBanco, { numeroBanco = it }, "Número do Banco", keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number))
                        StyledField(numeroAgencia, { numeroAgencia = it }, "Número da Agência", keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number))
                        StyledField(numeroConta, { numeroConta = it }, "Número da Conta", keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number))
                        DropdownField(
                            tipoConta, { tipoConta = it }, "Tipo de Conta",
                            listOf("Corrente", "Poupança")
                        )
                    }

                    5 -> {
                        SectionTitle("Resumo do Cadastro")

                        @Composable
                        fun SummaryItem(label: String, value: String) {
                            if (value.isNotBlank()) {
                                Row(
                                    modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Text(label, fontSize = 13.sp, color = Color(0xFF888888))
                                    Text(value, fontSize = 13.sp, fontWeight = FontWeight.Medium, color = Color(0xFF333333))
                                }
                            }
                        }

                        Text("Dados Pessoais", fontWeight = FontWeight.Bold, fontSize = 14.sp, color = Color(0xFF333333))
                        SummaryItem("Nome", nome)
                        SummaryItem("Sexo", sexo)
                        SummaryItem("Data Nasc.", dataNascimento)
                        SummaryItem("E-mail", email)
                        SummaryItem("Telefone", telefone)
                        SummaryItem("CPF", cpf)
                        SummaryItem("CNPJ (MEI)", cnpjMei)

                        Spacer(modifier = Modifier.height(8.dp))
                        Text("Endereço", fontWeight = FontWeight.Bold, fontSize = 14.sp, color = Color(0xFF333333))
                        SummaryItem("Endereço", "$logradouro, $numero - $bairro")
                        SummaryItem("Cidade/UF", "$cidade/$uf")
                        SummaryItem("CEP", cep)

                        Spacer(modifier = Modifier.height(8.dp))
                        Text("Veículo", fontWeight = FontWeight.Bold, fontSize = 14.sp, color = Color(0xFF333333))
                        SummaryItem("Tipo", tipoVeiculo)
                        SummaryItem("Placa", placa)
                        SummaryItem("Modelo", modelo)
                        SummaryItem("CNH", numeroCnh)

                        Spacer(modifier = Modifier.height(8.dp))
                        Text("Pagamento", fontWeight = FontWeight.Bold, fontSize = 14.sp, color = Color(0xFF333333))
                        SummaryItem("PIX ($tipoChavePix)", chavePix)

                        errorMessage?.let {
                            Text("⚠ $it", color = Red, fontSize = 13.sp, modifier = Modifier.padding(top = 8.dp))
                        }
                        successMessage?.let {
                            Text("✓ $it", color = Color(0xFF4CAF50), fontSize = 14.sp, modifier = Modifier.padding(top = 8.dp))
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))
            }

            // Bottom navigation buttons
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color.White)
                    .padding(horizontal = 24.dp, vertical = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                if (currentStep > 0) {
                    OutlinedButton(
                        onClick = { currentStep-- },
                        modifier = Modifier.weight(1f).height(48.dp),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text("Voltar", color = Color(0xFF1A1A1A))
                    }
                }

                Button(
                    onClick = {
                        // Validation logic before advancing step
                        var canAdvance = true
                        errorMessage = null
                        
                        when (currentStep) {
                            0 -> if (nome.isBlank() || cpf.length < 11 || telefone.length < 10) { errorMessage = "Preencha corretamente: Nome, CPF e Telefone"; canAdvance = false }
                            1 -> if (cep.length < 8 || logradouro.isBlank() || numero.isBlank()) { errorMessage = "Preencha corretamente o Endereço"; canAdvance = false }
                            2 -> if (tipoVeiculo.isBlank() || placa.isBlank()) { errorMessage = "Preencha o Tipo de Veículo e Placa"; canAdvance = false }
                        }

                        if (canAdvance) {
                            if (currentStep < totalSteps - 1) {
                                currentStep++
                            } else {
                                // Submit
                            scope.launch {
                                isSubmitting = true
                                errorMessage = null
                                successMessage = null
                                val supabaseUrl = BuildConfig.API_BASE_URL
                                try {
                                    val success = withContext(Dispatchers.IO) {
                                        val client = OkHttpClient()
                                        val body = """{
                                            "email": "$email",
                                            "password": "$senha",
                                            "data": {
                                                "name": "$nome",
                                                "phone": "$telefone",
                                                "cpf": "$cpf",
                                                "cnpj_mei": "$cnpjMei",
                                                "sexo": "$sexo",
                                                "data_nascimento": "$dataNascimento",
                                                "cep": "$cep",
                                                "logradouro": "$logradouro",
                                                "numero": "$numero",
                                                "complemento": "$complemento",
                                                "bairro": "$bairro",
                                                "cidade": "$cidade",
                                                "uf": "$uf",
                                                "ponto_referencia": "$pontoReferencia",
                                                "tipo_veiculo": "$tipoVeiculo",
                                                "cnh_numero": "$numeroCnh",
                                                "cnh_validade": "$validadeCnh",
                                                "placa": "$placa",
                                                "modelo_veiculo": "$modelo",
                                                "ano_fabricacao": "$anoFabricacao",
                                                "ano_exercicio": "$anoExercicio",
                                                "uf_emplacamento": "$ufEmplacamento",
                                                "renavam": "$renavam",
                                                "cor_veiculo": "$corVeiculo",
                                                "pix_tipo_chave": "$tipoChavePix",
                                                "pix_chave": "$chavePix",
                                                "conta_tipo": "$tipoConta"
                                        }
                                    }""".trimIndent().toRequestBody("application/json".toMediaTypeOrNull())
                                        val request = Request.Builder()
                                            .url("$supabaseUrl/auth/v1/signup")
                                            .post(body)
                                            .addHeader("Content-Type", "application/json")
                                            .build()
                                        val response = client.newCall(request).execute()
                                        response.isSuccessful
                                    }
                                    if (success) {
                                        successMessage = "Cadastro realizado! Aguarde a aprovação."
                                        delay(2000)
                                        onNavigateBack()
                                    } else {
                                        errorMessage = "Não foi possível criar a conta. Verifique os dados."
                                    }
                                } catch (e: Exception) {
                                    errorMessage = "Erro de conexão com o servidor."
                                } finally {
                                    isSubmitting = false
                                }
                            }
                        }
                        }
                    },
                    modifier = Modifier
                        .weight(if (currentStep > 0) 1f else 2f)
                        .height(56.dp)
                        .shadow(elevation = 2.dp, shape = RoundedCornerShape(12.dp), ambientColor = ExpressoRed, spotColor = ExpressoRed),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = ExpressoRed),
                    enabled = !isSubmitting && (currentStep < 5 || (senha.isNotBlank() && senha == confirmarSenha))
                ) {
                    if (isSubmitting) {
                        CircularProgressIndicator(modifier = Modifier.size(24.dp), color = Color.White)
                    } else {
                        Text(
                            if (currentStep < totalSteps - 1) "Continuar" else "Cadastrar",
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                    }
                }
            }
        }
    }
}
