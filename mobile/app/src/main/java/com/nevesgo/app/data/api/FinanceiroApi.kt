package com.nevesgo.app.data.api

import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.POST
import com.nevesgo.app.domain.model.WalletBalanceResponse

interface FinanceiroApi {
    @GET("finance/wallet/balance")
    suspend fun getWalletBalance(): Response<WalletBalanceResponse>

    @GET("finance/transactions")
    suspend fun getTransactions(): Response<Any>

    @POST("finance/wallet/withdraw")
    suspend fun withdrawWallet(): Response<Unit>
}
