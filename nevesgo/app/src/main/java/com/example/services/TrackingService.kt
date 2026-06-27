package com.example.services

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.location.Location
import android.os.Build
import android.os.IBinder
import android.os.Looper
import androidx.core.app.NotificationCompat
import com.example.MainActivity
import com.example.MyApplication
import com.example.domain.models.IncidentRequest
import com.example.domain.models.LocationUpdate
import com.google.android.gms.location.*
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class TrackingService : Service() {
    private var trackedOrderId: String? = null

    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private lateinit var locationCallback: LocationCallback
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val apiService by lazy { (application as MyApplication).container.driverApiService }

    override fun onCreate() {
        super.onCreate()
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)

        locationCallback = object : LocationCallback() {
            override fun onLocationResult(locationResult: LocationResult) {
                locationResult.lastLocation?.let { location ->
                    sendLocationToServer(location)
                }
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {

        createNotificationChannel()

        val launchIntent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this,
            1,
            launchIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, "TRACKING_CHANNEL")
            .setContentTitle("NevesGo")
            .setContentText("Rastreamento de jornada ativo (Online)")
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setContentIntent(pendingIntent)
            .build()
            
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(1, notification, android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION)
        } else {
            startForeground(1, notification)
        }
        
        requestLocationUpdates()

        return START_STICKY
    }

    private fun requestLocationUpdates() {
        val hasFine = androidx.core.content.ContextCompat.checkSelfPermission(this, android.Manifest.permission.ACCESS_FINE_LOCATION) == android.content.pm.PackageManager.PERMISSION_GRANTED
        val hasCoarse = androidx.core.content.ContextCompat.checkSelfPermission(this, android.Manifest.permission.ACCESS_COARSE_LOCATION) == android.content.pm.PackageManager.PERMISSION_GRANTED
        
        if (!hasFine && !hasCoarse) {
            return
        }
        
        val priority = if (hasFine) Priority.PRIORITY_HIGH_ACCURACY else Priority.PRIORITY_BALANCED_POWER_ACCURACY
        
        val locationRequest = LocationRequest.Builder(priority, 10000)
            .setMinUpdateIntervalMillis(5000)
            .build()

        try {
            fusedLocationClient.requestLocationUpdates(
                locationRequest,
                locationCallback,
                Looper.getMainLooper()
            )
        } catch (e: SecurityException) {
            e.printStackTrace()
        }
    }

    private fun sendLocationToServer(location: Location) {
        serviceScope.launch {
            try {
                val isMock = androidx.core.location.LocationCompat.isMock(location)
                if (isMock) {
                    val incident = IncidentRequest(
                        type = "GPS_SPOOFING",
                        description = "Mock location detected via LocationCompat",
                        lat = location.latitude,
                        lng = location.longitude
                    )
                    apiService.reportIncident(incident)
                }

                val update = LocationUpdate(
                    lat = location.latitude,
                    lng = location.longitude,
                    heading = location.bearing.toInt(),
                    speedKmh = (location.speed * 3.6).toInt(),
                    timestamp = location.time
                )
                
                // Get the base url from BuildConfig and replace port 8000 with 8001
                val baseUrl = com.example.BuildConfig.API_BASE_URL
                val fastLaneUrl = if (baseUrl.contains("8000")) {
                    baseUrl.replace("8000", "8001").replace("api/v1/", "telemetry")
                } else {
                    baseUrl.replace("api/v1/", "telemetry")
                }
                
                val deviceToken = com.example.data.local.SecureStorage.getPrefs(this@TrackingService).getString("device_token", "missing") ?: "missing"
                
                // First, try to send cached offline points if any
                val db = com.example.data.local.AppDatabase.getDatabase(this@TrackingService)
                val offlinePoints = db.telemetryDao().getAll()
                if (offlinePoints.isNotEmpty()) {
                    for (point in offlinePoints) {
                        try {
                            val cachedUpdate = LocationUpdate(
                                lat = point.lat,
                                lng = point.lng,
                                heading = point.heading,
                                speedKmh = point.speedKmh,
                                timestamp = point.timestamp
                            )
                            apiService.updateLocation(url = fastLaneUrl, deviceToken = deviceToken, location = cachedUpdate)
                        } catch (e: Exception) {
                            // Ignora erros individuais no sync em lote
                        }
                    }
                    db.telemetryDao().clearAll()
                }

                // Send the current one
                apiService.updateLocation(url = fastLaneUrl, deviceToken = deviceToken, location = update)
            } catch (e: Exception) {
                // Offline fallback: save to local DB
                val db = com.example.data.local.AppDatabase.getDatabase(this@TrackingService)
                db.telemetryDao().insert(
                    com.example.data.local.TelemetryEntity(
                        lat = location.latitude,
                        lng = location.longitude,
                        heading = location.bearing.toInt(),
                        speedKmh = (location.speed * 3.6).toInt(),
                        timestamp = location.time
                    )
                )
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        fusedLocationClient.removeLocationUpdates(locationCallback)
        kotlinx.coroutines.cancel(serviceScope)
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                "TRACKING_CHANNEL",
                "Tracking Service",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(channel)
        }
    }

    companion object {
        fun start(context: Context) {
            val intent = Intent(context, TrackingService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, TrackingService::class.java))
        }
    }
}
