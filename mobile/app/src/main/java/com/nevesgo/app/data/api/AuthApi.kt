package com.nevesgo.app.data.api

import retrofit2.Response
import retrofit2.http.POST

interface AuthApi {
    /**
     * Callback de login que invalida tokens antigos da fast lane.
     * O header de Autorização com o JWT do Supabase deve ser enviado
     * através de um Interceptor.
     */
    @POST("accounts/auth/login")
    suspend fun loginCallback(): Response<Unit>
}
