package com.example.chordproapp.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.chordproapp.viewmodel.RoomViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SyncScreen(navController: NavHostController, vm: RoomViewModel = viewModel()) {
    var roomCode by remember { mutableStateOf("") }
    val state by vm.uiState.collectAsState()

    // colors for theme
    val backgroundColor = Color(0xFFF7F7FF)
    val primaryTextColor = Color(0xFF07277C)
    val navBarColor = Color(0xFF231973)

    Scaffold(
        containerColor = backgroundColor,
        topBar = {
            TopAppBar(
                title = { Text("Sync", color = Color.White) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = navBarColor)
            )
        }
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            item {
                Text(
                    "Ready to Share Music Sheets?",
                    style = MaterialTheme.typography.headlineLarge,
                    color = primaryTextColor
                )
                Text(
                    "Create a new room or join an existing one",
                    style = MaterialTheme.typography.bodyLarge,
                    color = primaryTextColor.copy(alpha = 0.7f),
                    modifier = Modifier.padding(top = 8.dp)
                )
            }

            /** Create Room **/
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(32.dp)) {
                        Icon(
                            Icons.Default.PlayArrow,
                            contentDescription = null,
                            tint = primaryTextColor,
                            modifier = Modifier.size(48.dp).padding(bottom = 16.dp)
                        )
                        Text("Create Room", style = MaterialTheme.typography.titleLarge, color = primaryTextColor)
                        Text(
                            "Start a new session and invite others.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = primaryTextColor.copy(alpha = 0.7f),
                            modifier = Modifier.padding(vertical = 8.dp)
                        )
                        Button(
                            onClick = {
                                vm.setMode(true)
                                vm.createRoom { ok, id ->
                                    if (ok && id != null) {
                                        navController.navigate("joined_sync/$id/MyGroup/Fur Elise/true/You")
                                    }
                                }
                            },
                            modifier = Modifier.fillMaxWidth().height(56.dp),
                            shape = RoundedCornerShape(16.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = navBarColor)
                        ) { Text("Create New Room", color = Color.White) }
                    }
                }
            }

            /** Join Room **/
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(32.dp)) {
                        Text("Join Room", style = MaterialTheme.typography.titleLarge, color = primaryTextColor)
                        OutlinedTextField(
                            value = roomCode,
                            onValueChange = { roomCode = it },
                            placeholder = { Text("Enter room code (e.g. ABC123)") },
                            singleLine = true,
                            shape = RoundedCornerShape(16.dp),
                            modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp)
                        )
                        Button(
                            onClick = {
                                navController.navigate("joined_sync/$roomCode/MyGroup/Fur Elise/false/You")
                            },
                            modifier = Modifier.fillMaxWidth().height(56.dp),
                            shape = RoundedCornerShape(16.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = navBarColor)
                        ) { Text("Join Room", color = Color.White) }
                    }
                }
            }

            /** Status **/
            item { Text(state.status, color = primaryTextColor) }
        }
    }
}
