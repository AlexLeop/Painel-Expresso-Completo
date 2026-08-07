package com.example

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

@RunWith(AndroidJUnit4::class)
@Config(sdk = [36])
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class ExampleRobolectricTest {

  @Test
  fun `read string from context`() {
    val context = ApplicationProvider.getApplicationContext<Context>()
    val appName = context.getString(R.string.app_name)
    assertEquals("NevesGo", appName)
  }

  @Test
  fun `launch activity`() {
    System.setProperty("robolectric.logging.enabled", "true")
    try {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            scenario.onActivity { 
                println("Activity launched successfully!")
            }
        }
    } catch (e: Exception) {
        e.printStackTrace()
        throw e
    }
  }
}
