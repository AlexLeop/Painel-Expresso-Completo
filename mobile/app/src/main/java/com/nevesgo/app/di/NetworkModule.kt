package com.nevesgo.app.di

import com.nevesgo.app.data.api.CorridaApi
import com.nevesgo.app.data.api.FinanceiroApi
import com.nevesgo.app.data.api.EscalaApi
import com.nevesgo.app.domain.repository.CorridaRepository
import com.nevesgo.app.domain.repository.FinanceiroRepository
import com.nevesgo.app.domain.repository.EscalaRepository
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import okhttp3.OkHttpClient
import okhttp3.Interceptor
import javax.inject.Singleton
import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import com.nevesgo.app.data.local.TokenManager
import com.nevesgo.app.data.api.interceptors.AuthInterceptor
import com.nevesgo.app.data.api.AuthApi

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    // Base URL para emulador do Android bater no localhost da máquina
    private const val BASE_URL = "http://10.0.2.2:8000/api/v1/"

    @Provides
    @Singleton
    fun provideTokenManager(@ApplicationContext context: Context): TokenManager {
        return TokenManager(context)
    }

    @Provides
    @Singleton
    fun provideAuthInterceptor(tokenManager: TokenManager): Interceptor {
        return AuthInterceptor(tokenManager)
    }

    @Provides
    @Singleton
    fun provideOkHttpClient(authInterceptor: Interceptor): OkHttpClient {
        return OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(MockInterceptor()) // Ativando Mock para protótipo
            .build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(okHttpClient: OkHttpClient): Retrofit {
        return Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    @Provides
    @Singleton
    fun provideCorridaApi(retrofit: Retrofit): CorridaApi {
        return retrofit.create(CorridaApi::class.java)
    }

    @Provides
    @Singleton
    fun provideFinanceiroApi(retrofit: Retrofit): FinanceiroApi {
        return retrofit.create(FinanceiroApi::class.java)
    }

    @Provides
    @Singleton
    fun provideEscalaApi(retrofit: Retrofit): EscalaApi {
        return retrofit.create(EscalaApi::class.java)
    }

    @Provides
    @Singleton
    fun provideCorridaRepository(api: CorridaApi): CorridaRepository {
        return CorridaRepository(api)
    }

    @Provides
    @Singleton
    fun provideFinanceiroRepository(api: FinanceiroApi): FinanceiroRepository {
        return FinanceiroRepository(api)
    }

    @Provides
    @Singleton
    fun provideEscalaRepository(api: EscalaApi): EscalaRepository {
        return EscalaRepository(api)
    }

    @Provides
    @Singleton
    fun provideAuthApi(retrofit: Retrofit): AuthApi {
        return retrofit.create(AuthApi::class.java)
    }
}
