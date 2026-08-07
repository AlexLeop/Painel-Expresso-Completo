package com.nevesgo.app.domain.repository

import com.nevesgo.app.data.api.EscalaApi

class EscalaRepository(private val api: EscalaApi) {
    suspend fun getCalendarShifts() = api.getCalendarShifts()
    suspend fun reserveShift() = api.reserveShift()
    suspend fun checkOutShift() = api.checkOutShift()
}
