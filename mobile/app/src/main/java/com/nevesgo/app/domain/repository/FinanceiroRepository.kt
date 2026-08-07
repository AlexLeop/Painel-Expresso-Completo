package com.nevesgo.app.domain.repository

import com.nevesgo.app.data.api.FinanceiroApi

class FinanceiroRepository(private val api: FinanceiroApi) {
    suspend fun getWalletBalance() = api.getWalletBalance()
    suspend fun getTransactions() = api.getTransactions()
    suspend fun withdrawWallet() = api.withdrawWallet()
}
