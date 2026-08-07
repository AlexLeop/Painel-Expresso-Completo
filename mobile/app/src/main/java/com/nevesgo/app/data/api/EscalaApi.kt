package com.nevesgo.app.data.api

import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.POST

interface EscalaApi {
    @GET("driver/shifts/calendar")
    suspend fun getCalendarShifts(): Response<Any>

    @POST("driver/shifts/reservations")
    suspend fun reserveShift(): Response<Unit>

    @POST("driver/shifts/check-out")
    suspend fun checkOutShift(): Response<Unit>
}
