package com.example.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "orders")
data class OrderEntity(
    @PrimaryKey val id: String,
    val originName: String,
    val originAddress: String,
    val destinationName: String,
    val destinationAddress: String,
    val distanceMeters: Int,
    val fareCents: Int,
    val slaSeconds: Int,
    val status: String, // OFFERED, ACCEPTED, IN_PROGRESS, COMPLETED
    val syncStatus: String // SYNCED, PENDING_SYNC
)
