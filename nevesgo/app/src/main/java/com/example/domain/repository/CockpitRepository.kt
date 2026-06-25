package com.example.domain.repository

import com.example.domain.models.CockpitResponse

interface CockpitRepository {
    suspend fun getCockpitData(): Result<CockpitResponse>
    suspend fun setDriverStatus(status: String, reason: String? = null): Result<Unit>
}
