package com.example.ui.screens

import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.platform.LocalContext
import androidx.navigation.NavController
import com.example.MyApplication
import com.example.domain.models.DriverCalendarItem
import com.example.domain.models.ShiftCheckInRequest
import com.example.domain.models.ShiftCheckOutRequest
import com.example.domain.models.ShiftInfo
import com.example.domain.models.ShiftReservationRequest
import com.example.ui.components.DriverPrimaryButton
import com.example.ui.components.DriverSecondaryButton
import kotlinx.coroutines.launch
import java.time.LocalDate

private fun buildScheduleDetailsRoute(item: DriverCalendarItem): String {
    return buildString {
        append("escala_detalhes/")
        append(Uri.encode(item.kind))
        append("/")
        append(Uri.encode(item.date))
        append("/")
        append(Uri.encode(item.status))
        append("/")
        append(Uri.encode(item.storeId))
        append("/")
        append(Uri.encode(item.storeName))
        append("/")
        append(Uri.encode(item.turnoId))
        append("/")
        append(Uri.encode(item.turnoName))
    }
}

private fun scheduleActionKey(action: String, item: DriverCalendarItem): String {
    return "$action:${item.kind}:${item.turnoId}:${item.date}"
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SchedulesScreen(navController: NavController) {
    val context = LocalContext.current
    val apiService = remember { (context.applicationContext as MyApplication).container.driverApiService }
    val scope = rememberCoroutineScope()
    var selectedTab by remember { mutableIntStateOf(0) }
    var calendarItems by remember { mutableStateOf<List<DriverCalendarItem>>(emptyList()) }
    var currentShift by remember { mutableStateOf<ShiftInfo?>(null) }
    var infoMessage by remember { mutableStateOf<String?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var activeActionKey by remember { mutableStateOf<String?>(null) }

    fun refresh(showLoader: Boolean = true) {
        scope.launch {
            if (showLoader) {
                isLoading = true
            }
            errorMessage = null
            try {
                val today = LocalDate.now().toString()
                val calendarResponse = apiService.getShiftCalendar(startDate = today)
                if (calendarResponse.isSuccessful) {
                    calendarItems = calendarResponse.body().orEmpty()
                } else {
                    errorMessage = "Nao foi possivel carregar a agenda operacional."
                }

                val cockpitResponse = apiService.getCockpit()
                currentShift = if (cockpitResponse.isSuccessful) {
                    cockpitResponse.body()?.shift
                } else {
                    currentShift
                }
                if (!cockpitResponse.isSuccessful && errorMessage == null) {
                    errorMessage = "Nao foi possivel validar a sessao de turno atual."
                }
            } catch (_: Exception) {
                errorMessage = "Falha ao sincronizar agenda e turno com o backend."
            } finally {
                activeActionKey = null
                isLoading = false
            }
        }
    }

    fun reserveShift(item: DriverCalendarItem) {
        scope.launch {
            activeActionKey = scheduleActionKey("reserve", item)
            errorMessage = null
            val response = try {
                apiService.createShiftReservation(
                    ShiftReservationRequest(
                        storeId = item.storeId,
                        turnoId = item.turnoId,
                        date = item.date
                    )
                )
            } catch (_: Exception) {
                null
            }
            if (response?.isSuccessful == true) {
                infoMessage = "Reserva enviada para ${item.storeName}."
                refresh(showLoader = false)
            } else {
                activeActionKey = null
                errorMessage = "Falha ao reservar o turno selecionado."
            }
        }
    }

    fun checkIn(item: DriverCalendarItem) {
        scope.launch {
            activeActionKey = scheduleActionKey("checkin", item)
            errorMessage = null
            val response = try {
                apiService.checkIn(
                    ShiftCheckInRequest(
                        turnoId = item.turnoId,
                        storeId = item.storeId,
                        date = item.date
                    )
                )
            } catch (_: Exception) {
                null
            }
            if (response?.isSuccessful == true) {
                infoMessage = response.body()?.message ?: "Check-in realizado com sucesso."
                com.example.services.TrackingService.start(context)
                refresh(showLoader = false)
            } else {
                activeActionKey = null
                errorMessage = "Falha ao realizar check-in no turno."
            }
        }
    }

    fun checkOut() {
        scope.launch {
            activeActionKey = "checkout"
            errorMessage = null
            val response = try {
                apiService.checkOut(ShiftCheckOutRequest())
            } catch (_: Exception) {
                null
            }
            if (response?.isSuccessful == true) {
                val minutes = response.body()?.workedMinutes
                infoMessage = if (minutes != null) {
                    "Check-out realizado. Jornada registrada: $minutes min."
                } else {
                    response.body()?.message ?: "Check-out realizado com sucesso."
                }
                com.example.services.TrackingService.stop(context)
                refresh(showLoader = false)
            } else {
                activeActionKey = null
                errorMessage = "Falha ao realizar check-out da jornada."
            }
        }
    }

    LaunchedEffect(Unit) {
        refresh()
    }

    val scheduledItems = calendarItems.filter { it.kind == "SCHEDULE" }
    val reservationItems = calendarItems.filter { it.kind == "RESERVATION" && it.status != "CANCELED" }
    val canceledItems = calendarItems.filter { it.kind == "RESERVATION" && it.status == "CANCELED" }
    val currentList = when (selectedTab) {
        0 -> scheduledItems
        1 -> reservationItems
        else -> canceledItems
    }
    val openShift = currentShift?.takeIf { !it.sessionId.isNullOrBlank() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Escalas", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Voltar")
                    }
                },
                actions = {
                    IconButton(onClick = { refresh() }) {
                        Icon(Icons.Filled.Refresh, contentDescription = "Atualizar")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
        ) {
            if (openShift != null) {
                ActiveShiftCard(
                    shift = openShift,
                    isCheckingOut = activeActionKey == "checkout",
                    onCheckOut = { checkOut() }
                )
            }

            TabRow(selectedTabIndex = selectedTab) {
                Tab(selected = selectedTab == 0, onClick = { selectedTab = 0 }, text = { Text("Disponiveis") })
                Tab(selected = selectedTab == 1, onClick = { selectedTab = 1 }, text = { Text("Reservas") })
                Tab(selected = selectedTab == 2, onClick = { selectedTab = 2 }, text = { Text("Canceladas") })
            }

            if (!infoMessage.isNullOrBlank() || !errorMessage.isNullOrBlank()) {
                Text(
                    text = errorMessage ?: infoMessage.orEmpty(),
                    color = if (errorMessage != null) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp)
                )
            }

            LazyColumn(
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                if (isLoading) {
                    item {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 32.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            CircularProgressIndicator()
                        }
                    }
                } else if (currentList.isEmpty()) {
                    item {
                        Text(
                            text = "Nenhum item operacional encontrado nesta aba.",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(vertical = 24.dp)
                        )
                    }
                } else {
                    items(currentList, key = { "${it.kind}:${it.turnoId}:${it.date}" }) { item ->
                        val isCurrentShiftItem =
                            openShift?.turnoId == item.turnoId &&
                                openShift.date == item.date &&
                                openShift.storeId == item.storeId
                        ScheduleListCard(
                            item = item,
                            hasOpenShift = openShift != null,
                            isCurrentShiftItem = isCurrentShiftItem,
                            reserveInFlight = activeActionKey == scheduleActionKey("reserve", item),
                            checkInInFlight = activeActionKey == scheduleActionKey("checkin", item),
                            onOpenDetails = {
                                navController.navigate(buildScheduleDetailsRoute(item))
                            },
                            onReserve = { reserveShift(item) },
                            onCheckIn = { checkIn(item) },
                            onCheckOut = { checkOut() }
                        )
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ScheduleDetailsScreen(
    navController: NavController,
    kind: String?,
    date: String?,
    status: String?,
    storeId: String?,
    storeName: String?,
    turnoId: String?,
    turnoName: String?
) {
    val context = LocalContext.current
    val apiService = remember { (context.applicationContext as MyApplication).container.driverApiService }
    val scope = rememberCoroutineScope()
    var currentShift by remember { mutableStateOf<ShiftInfo?>(null) }
    var infoMessage by remember { mutableStateOf<String?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var actionKey by remember { mutableStateOf<String?>(null) }

    fun refreshShift() {
        scope.launch {
            try {
                val cockpitResponse = apiService.getCockpit()
                if (cockpitResponse.isSuccessful) {
                    currentShift = cockpitResponse.body()?.shift
                }
            } catch (_: Exception) {
                errorMessage = "Nao foi possivel atualizar a sessao de turno."
            }
        }
    }

    fun reserveCurrent() {
        if (storeId.isNullOrBlank() || turnoId.isNullOrBlank() || date.isNullOrBlank()) return
        scope.launch {
            actionKey = "reserve"
            errorMessage = null
            val response = try {
                apiService.createShiftReservation(
                    ShiftReservationRequest(
                        storeId = storeId,
                        turnoId = turnoId,
                        date = date
                    )
                )
            } catch (_: Exception) {
                null
            }
            if (response?.isSuccessful == true) {
                infoMessage = "Reserva enviada para aprovacao."
                actionKey = null
            } else {
                actionKey = null
                errorMessage = "Falha ao reservar este turno."
            }
        }
    }

    fun checkInCurrent() {
        if (storeId.isNullOrBlank() || turnoId.isNullOrBlank() || date.isNullOrBlank()) return
        scope.launch {
            actionKey = "checkin"
            errorMessage = null
            val response = try {
                apiService.checkIn(
                    ShiftCheckInRequest(
                        turnoId = turnoId,
                        storeId = storeId,
                        date = date
                    )
                )
            } catch (_: Exception) {
                null
            }
            if (response?.isSuccessful == true) {
                infoMessage = response.body()?.message ?: "Check-in realizado com sucesso."
                com.example.services.TrackingService.start(context)
                refreshShift()
                actionKey = null
            } else {
                actionKey = null
                errorMessage = "Falha ao abrir jornada neste turno."
            }
        }
    }

    fun checkOutCurrent() {
        scope.launch {
            actionKey = "checkout"
            errorMessage = null
            val response = try {
                apiService.checkOut(ShiftCheckOutRequest())
            } catch (_: Exception) {
                null
            }
            if (response?.isSuccessful == true) {
                infoMessage = response.body()?.message ?: "Check-out realizado com sucesso."
                com.example.services.TrackingService.stop(context)
                refreshShift()
                actionKey = null
            } else {
                actionKey = null
                errorMessage = "Falha ao encerrar a jornada aberta."
            }
        }
    }

    LaunchedEffect(Unit) {
        refreshShift()
    }

    val isReservation = kind == "RESERVATION"
    val isCurrentShiftItem =
        currentShift?.sessionId != null &&
            currentShift?.turnoId == turnoId &&
            currentShift?.date == date &&
            currentShift?.storeId == storeId

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Detalhes da Escala", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Voltar")
                    }
                }
            )
        },
        bottomBar = {
            Column(modifier = Modifier.padding(16.dp)) {
                when {
                    isCurrentShiftItem -> {
                        DriverSecondaryButton(
                            text = if (actionKey == "checkout") "ENCERRANDO..." else "FAZER CHECK-OUT",
                            onClick = { checkOutCurrent() },
                            enabled = actionKey == null
                        )
                    }

                    currentShift?.sessionId != null -> {
                        DriverSecondaryButton(
                            text = "JA EXISTE JORNADA ABERTA",
                            onClick = {},
                            enabled = false
                        )
                    }

                    isReservation -> {
                        DriverPrimaryButton(
                            text = if (actionKey == "checkin") "ABRINDO JORNADA..." else "FAZER CHECK-IN",
                            onClick = { checkInCurrent() },
                            enabled = actionKey == null
                        )
                    }

                    else -> {
                        DriverPrimaryButton(
                            text = if (actionKey == "reserve") "ENVIANDO RESERVA..." else "RESERVAR TURNO",
                            onClick = { reserveCurrent() },
                            enabled = actionKey == null
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        DriverSecondaryButton(
                            text = if (actionKey == "checkin") "ABRINDO JORNADA..." else "FAZER CHECK-IN",
                            onClick = { checkInCurrent() },
                            enabled = actionKey == null
                        )
                    }
                }
            }
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                if (!infoMessage.isNullOrBlank() || !errorMessage.isNullOrBlank()) {
                    Text(
                        text = errorMessage ?: infoMessage.orEmpty(),
                        color = if (errorMessage != null) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(top = 8.dp)
                    )
                }
            }

            item {
                Card(
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                Icons.Filled.CalendarMonth,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary
                            )
                            Spacer(modifier = Modifier.width(16.dp))
                            Column {
                                Text(date ?: "Data nao informada", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                                Text(
                                    if (isReservation) "Reserva do entregador" else "Janela operacional disponivel",
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                        Spacer(modifier = Modifier.height(16.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                Icons.Filled.Schedule,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary
                            )
                            Spacer(modifier = Modifier.width(16.dp))
                            Column {
                                Text(turnoName ?: "Turno nao informado", fontWeight = FontWeight.SemiBold)
                                Text(
                                    "Status: ${status ?: "DESCONHECIDO"}",
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    fontSize = 14.sp
                                )
                            }
                        }
                    }
                }
            }

            item {
                Card(
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("Loja vinculada", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(storeName ?: "Loja nao informada", fontWeight = FontWeight.SemiBold)
                        Text(
                            "Store ID: ${storeId ?: "indisponivel"}",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 14.sp
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        AssistChip(
                            onClick = {},
                            label = { Text(kind ?: "SEM TIPO") }
                        )
                    }
                }
            }

            item {
                if (currentShift?.sessionId != null) {
                    Card(
                        shape = RoundedCornerShape(20.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("Jornada atual", fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(currentShift?.storeName ?: "Loja em andamento")
                            Text(
                                currentShift?.turnoName ?: "Turno em andamento",
                                color = MaterialTheme.colorScheme.onPrimaryContainer
                            )
                            Text(
                                "Sessao: ${currentShift?.sessionId ?: "indisponivel"}",
                                color = MaterialTheme.colorScheme.onPrimaryContainer,
                                fontSize = 13.sp
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ActiveShiftCard(
    shift: ShiftInfo,
    isCheckingOut: Boolean,
    onCheckOut: () -> Unit
) {
    Card(
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 12.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Jornada aberta", fontWeight = FontWeight.Bold, fontSize = 18.sp)
            Spacer(modifier = Modifier.height(8.dp))
            Text(shift.storeName ?: "Loja nao identificada", fontWeight = FontWeight.SemiBold)
            Text(
                "${shift.turnoName ?: "Turno"} • ${shift.date ?: "Data nao informada"}",
                color = MaterialTheme.colorScheme.onPrimaryContainer
            )
            Text(
                "Sessao ${shift.sessionId ?: "indisponivel"}",
                color = MaterialTheme.colorScheme.onPrimaryContainer,
                fontSize = 13.sp
            )
            Spacer(modifier = Modifier.height(12.dp))
            DriverSecondaryButton(
                text = if (isCheckingOut) "ENCERRANDO..." else "ENCERRAR JORNADA",
                onClick = onCheckOut,
                enabled = !isCheckingOut
            )
        }
    }
}

@Composable
private fun ScheduleListCard(
    item: DriverCalendarItem,
    hasOpenShift: Boolean,
    isCurrentShiftItem: Boolean,
    reserveInFlight: Boolean,
    checkInInFlight: Boolean,
    onOpenDetails: () -> Unit,
    onReserve: () -> Unit,
    onCheckIn: () -> Unit,
    onCheckOut: () -> Unit
) {
    Card(
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(item.date, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 14.sp)
                    Text(item.storeName, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                    Text(item.turnoName, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 14.sp)
                }
                Column(horizontalAlignment = Alignment.End) {
                    AssistChip(onClick = {}, label = { Text(item.status) })
                    Spacer(modifier = Modifier.height(8.dp))
                    AssistChip(onClick = {}, label = { Text(item.kind) })
                }
            }

            Spacer(modifier = Modifier.height(16.dp))
            DriverSecondaryButton(
                text = "VER DETALHES",
                onClick = onOpenDetails
            )
            Spacer(modifier = Modifier.height(8.dp))

            when {
                isCurrentShiftItem -> {
                    DriverSecondaryButton(
                        text = "FAZER CHECK-OUT",
                        onClick = onCheckOut
                    )
                }

                item.kind == "RESERVATION" && !hasOpenShift -> {
                    DriverPrimaryButton(
                        text = if (checkInInFlight) "ABRINDO JORNADA..." else "FAZER CHECK-IN",
                        onClick = onCheckIn,
                        enabled = !checkInInFlight
                    )
                }

                item.kind == "SCHEDULE" && !hasOpenShift -> {
                    DriverPrimaryButton(
                        text = if (reserveInFlight) "ENVIANDO RESERVA..." else "RESERVAR TURNO",
                        onClick = onReserve,
                        enabled = !reserveInFlight && !checkInInFlight
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    DriverSecondaryButton(
                        text = if (checkInInFlight) "ABRINDO JORNADA..." else "FAZER CHECK-IN",
                        onClick = onCheckIn,
                        enabled = !reserveInFlight && !checkInInFlight
                    )
                }

                else -> {
                    Text(
                        text = if (hasOpenShift) {
                            "Ja existe jornada aberta. Encerre o turno atual antes de abrir outro."
                        } else {
                            "Acompanhe esta reserva ate a confirmacao operacional."
                        },
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}
