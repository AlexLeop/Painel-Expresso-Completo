package com.example.data.repository

import com.example.data.remote.DriverApiService
import com.example.domain.models.CockpitResponse
import com.example.domain.models.StatusRequest
import com.example.domain.repository.CockpitRepository

class CockpitRemoteDataSource(
    private val apiService: DriverApiService
) : CockpitRepository {

    override suspend fun getCockpitData(): Result<CockpitResponse> {
        return try {
            val response = apiService.getCockpit()
            if (response.isSuccessful) {
                response.body()?.let {
                    Result.success(it)
                } ?: Result.failure(Exception("Body is null"))
            } else {
                Result.failure(Exception("Error fetching cockpit data: \${response.code()} \${response.message()}"))
            }
        } catch (e: Exception) {
            if (e is kotlinx.coroutines.CancellationException) throw e
            Result.failure(e)
        }
    }

    override suspend fun setDriverStatus(status: String, reason: String?): Result<Unit> {
        return try {
            val response = apiService.setStatus(StatusRequest(status = status, reason = reason))
            if (response.isSuccessful) {
                Result.success(Unit)
            } else {
                Result.failure(Exception("Error setting status: ${response.code()} ${response.message()}"))
            }
        } catch (e: Exception) {
            if (e is kotlinx.coroutines.CancellationException) throw e
            Result.failure(e)
        }
    }
}
