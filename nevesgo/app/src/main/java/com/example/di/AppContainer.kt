package com.example.di

import android.content.Context
import com.example.data.local.AppDatabase
import com.example.data.remote.RetrofitClient
import com.example.data.remote.DriverApiService
import com.example.data.repository.OrderRepositoryImpl
import com.example.domain.repository.OrderRepository
import com.example.domain.repository.CockpitRepository
import com.example.data.repository.CockpitRemoteDataSource

/**
 * Dependency Injection container.
 * In a production app, this could be replaced by Hilt or Koin.
 */
interface AppContainer {
    val orderRepository: OrderRepository
    val driverApiService: DriverApiService
    val cockpitRepository: CockpitRepository
}

class DefaultAppContainer(private val context: Context) : AppContainer {

    private val database: AppDatabase by lazy {
        AppDatabase.getDatabase(context)
    }

    override val orderRepository: OrderRepository by lazy {
        OrderRepositoryImpl(context, database.orderDao(), driverApiService)
    }

    override val cockpitRepository: CockpitRepository by lazy {
        CockpitRemoteDataSource(driverApiService)
    }

    override val driverApiService: DriverApiService by lazy {
        RetrofitClient.createService(context)
    }
}
