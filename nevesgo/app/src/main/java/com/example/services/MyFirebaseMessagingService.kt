package com.example.services

import android.util.Log
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class MyFirebaseMessagingService : FirebaseMessagingService() {

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.d(TAG, "Refreshed token: $token")
        sendRegistrationToServer(token)
    }

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        Log.d(TAG, "From: ${remoteMessage.from}")

        // Handle data payload
        if (remoteMessage.data.isNotEmpty()) {
            Log.d(TAG, "Message data payload: ${remoteMessage.data}")
            val application = applicationContext as? com.example.MyApplication
            application?.let {
                kotlinx.coroutines.GlobalScope.launch(kotlinx.coroutines.Dispatchers.IO) {
                    try {
                        it.container.orderRepository.syncOrders()
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to sync orders on push", e)
                    }
                }
            }
        }

        // Handle notification payload
        remoteMessage.notification?.let {
            Log.d(TAG, "Message Notification Body: ${it.body}")
            // Display notification is handled automatically by the system if the app is in the background.
            // If the app is in the foreground, we could show a custom UI or broadcast it.
        }
    }

    private fun sendRegistrationToServer(token: String?) {
        if (token == null) return
        val application = applicationContext as? com.example.MyApplication ?: return
        val apiService = application.container.driverApiService
        
        kotlinx.coroutines.GlobalScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            try {
                apiService.registerFcmToken(mapOf("token" to token))
                Log.d(TAG, "Token successfully sent to backend")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to send token to backend", e)
            }
        }
    }

    companion object {
        private const val TAG = "MyFirebaseMsgService"
    }
}
