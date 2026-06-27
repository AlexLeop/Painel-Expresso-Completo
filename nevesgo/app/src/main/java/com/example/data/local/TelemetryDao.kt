package com.example.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface TelemetryDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(telemetry: TelemetryEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(telemetries: List<TelemetryEntity>)

    @Query("SELECT * FROM telemetry_points ORDER BY timestamp ASC")
    suspend fun getAll(): List<TelemetryEntity>

    @Query("DELETE FROM telemetry_points")
    suspend fun clearAll()
}
