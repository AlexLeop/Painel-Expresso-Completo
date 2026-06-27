package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.LocalShipping
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.example.BuildConfig
import com.example.data.local.SecureStorage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import retrofit2.Response

@Composable
fun LoginScreen(
    onNavigateToHome: () -> Unit,
    onNavigateToRegister: () -> Unit,
    onValidateSession: suspend () -> Response<*>
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var email by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var isSubmitting by remember { mutableStateOf(false) }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
        contentAlignment = Alignment.Center
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            // Identity
            Icon(
                imageVector = Icons.Default.LocalShipping,
                contentDescription = "Logo",
                modifier = Modifier.size(80.dp),
                tint = MaterialTheme.colorScheme.primary
            )
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = "Expresso Neves",
                style = MaterialTheme.typography.headlineMedium,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = "Portal do Entregador",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            
            Spacer(modifier = Modifier.height(32.dp))

            OutlinedTextField(
                value = email,
                onValueChange = {
                    email = it
                    errorMessage = null
                },
                label = { Text("E-mail") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
            
            Spacer(modifier = Modifier.height(8.dp))

            OutlinedTextField(
                value = password,
                onValueChange = {
                    password = it
                    errorMessage = null
                },
                label = { Text("Senha") },
                visualTransformation = PasswordVisualTransformation(),
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            errorMessage?.let {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = it,
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall
                )
            }
            
            Spacer(modifier = Modifier.height(24.dp))

            Button(
                enabled = email.isNotBlank() && password.isNotBlank() && !isSubmitting,
                onClick = {
                    scope.launch {
                        isSubmitting = true
                        errorMessage = null

                        val supabaseUrl = BuildConfig.API_BASE_URL
                        val supabaseKey = "" // Usually handled by API or environment. Let's assume we have a way to authenticate.
                        // For Supabase email login:
                        try {
                            val tokens = withContext(Dispatchers.IO) {
                                val client = OkHttpClient()
                                val body = """{"email": "$email", "password": "$password"}"""
                                    .toRequestBody("application/json".toMediaTypeOrNull())
                                val request = Request.Builder()
                                    .url("$supabaseUrl/auth/v1/token?grant_type=password")
                                    .post(body)
                                    .addHeader("apikey", supabaseKey) // You might need the ANON KEY here
                                    .addHeader("Content-Type", "application/json")
                                    .build()
                                val response = client.newCall(request).execute()
                                if (response.isSuccessful) {
                                    response.body?.string()?.let { json ->
                                        val jsonObject = JSONObject(json)
                                        val access = jsonObject.optString("access_token")
                                        val refresh = jsonObject.optString("refresh_token")
                                        Pair(access, refresh)
                                    }
                                } else null
                            }
                            
                            if (tokens != null && tokens.first.isNotEmpty()) {
                                SecureStorage.saveToken(context, tokens.first)
                                SecureStorage.saveRefreshToken(context, tokens.second)

                                val sessionIsValid = try {
                                    onValidateSession().isSuccessful
                                } catch (_: Exception) {
                                    false
                                }

                                if (sessionIsValid) {
                                    onNavigateToHome()
                                } else {
                                    SecureStorage.clearToken(context)
                                    errorMessage = "Sessão inválida ou motorista não aprovado."
                                }
                            } else {
                                errorMessage = "Credenciais incorretas."
                            }
                        } catch (e: Exception) {
                            errorMessage = "Erro de conexão."
                        } finally {
                            isSubmitting = false
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.primary
                )
            ) {
                if (isSubmitting) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(24.dp),
                        color = Color.White
                    )
                } else {
                    Text("Entrar")
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            TextButton(
                onClick = onNavigateToRegister
            ) {
                Text("Ainda não tem conta? Cadastre-se", color = MaterialTheme.colorScheme.primary)
            }
        }
    }
}
