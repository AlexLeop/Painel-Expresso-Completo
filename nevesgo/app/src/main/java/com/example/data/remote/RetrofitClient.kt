package com.example.data.remote

import android.content.Context
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.example.BuildConfig
import com.example.data.remote.interceptors.AuthInterceptor
import com.example.data.remote.interceptors.ErrorInterceptor
import com.example.data.remote.interceptors.IdempotencyInterceptor
import com.example.data.remote.interceptors.RetryInterceptor
import com.example.data.remote.interceptors.TokenAuthenticator
import com.example.data.remote.interceptors.OfflineInterceptor
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.Cache
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit

val Context.dataStore by preferencesDataStore(name = "settings")

object RetrofitClient {
    private val baseUrl: String = BuildConfig.API_BASE_URL.let { configured ->
        if (configured.endsWith("/")) configured else "$configured/"
    }

    private val moshi = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()

    fun createService(context: Context): DriverApiService {
        val loggingInterceptor = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.ENABLE_HTTP_LOGGING) {
                HttpLoggingInterceptor.Level.BODY
            } else {
                HttpLoggingInterceptor.Level.NONE
            }
        }

        val okHttpClient = OkHttpClient.Builder()
            .addInterceptor(RetryInterceptor(maxRetries = 3))
            .addInterceptor(IdempotencyInterceptor())
            .addInterceptor(AuthInterceptor(context))
            .addInterceptor(ErrorInterceptor(context))
            .addInterceptor(OfflineInterceptor(context))
            .authenticator(TokenAuthenticator(context))
            .addInterceptor(loggingInterceptor)
            .cache(Cache(java.io.File(context.cacheDir, "offline_cache"), 10 * 1024 * 1024))
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()

        val retrofit = Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(okHttpClient)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()

        return retrofit.create(DriverApiService::class.java)
    }
}
