package com.nevesgo.app.ui.theme

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.LocalShipping
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@Composable
fun NevesGoBottomNav(activeTab: String, modifier: Modifier = Modifier) {
    Surface(
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 16.dp,
        modifier = modifier.fillMaxWidth().navigationBarsPadding().height(80.dp)
    ) {
        Column {
            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
            Row(
                modifier = Modifier.fillMaxWidth().weight(1f).padding(horizontal = 8.dp),
                horizontalArrangement = Arrangement.SpaceAround,
                verticalAlignment = Alignment.CenterVertically
            ) {
                BottomNavItem(icon = Icons.Filled.Home, label = "Início", isActive = activeTab == "inicio")
                BottomNavItem(icon = Icons.Outlined.LocalShipping, label = "Entregas", isActive = activeTab == "entregas")
                BottomNavItem(icon = Icons.Outlined.CalendarMonth, label = "Escala", isActive = activeTab == "escala")
                BottomNavItem(icon = Icons.Outlined.Person, label = "Perfil", isActive = activeTab == "perfil")
            }
        }
    }
}

@Composable
private fun BottomNavItem(icon: androidx.compose.ui.graphics.vector.ImageVector, label: String, isActive: Boolean) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
        modifier = Modifier.padding(4.dp).clickable { /* TODO */ }
    ) {
        Icon(imageVector = icon, contentDescription = label, tint = if (isActive) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline)
        Text(text = label, style = MaterialTheme.typography.labelSmall.copy(fontWeight = if (isActive) FontWeight.SemiBold else FontWeight.Medium), color = if (isActive) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline)
    }
}
