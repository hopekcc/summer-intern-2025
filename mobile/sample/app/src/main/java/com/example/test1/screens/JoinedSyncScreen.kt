package com.example.chordproapp.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.example.chordproapp.viewmodel.RoomViewModel
import com.example.chordproapp.model.Song

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun JoinedSyncScreen(
    navController: NavHostController,
    roomCode: String,
    groupName: String,
    currentUserName: String,
    isHost: Boolean,
    onRemoveParticipant: (String) -> Unit,
    onLeaveRoom: () -> Unit,
    vm: RoomViewModel = viewModel()
) {
    val state by vm.uiState.collectAsState()

    // Theme Colors
    val backgroundColor = Color(0xFFF7F7FF)
    val primaryTextColor = Color(0xFF07277C)
    val navBarColor = Color(0xFF231973)
    val leaveButtonColor = Color(0xFFEA4E4E)

    Scaffold(
        containerColor = backgroundColor,
        topBar = {
            TopAppBar(
                title = { Text("Room $roomCode", color = Color.White) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = navBarColor)
            )
        }
    ) { innerPadding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Group Info
            Text("Group: $groupName", color = primaryTextColor)

            // Queue Section
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text("Queue", color = primaryTextColor)
                    LazyColumn {
                        items(state.songQueue) { song: Song ->
                            Row(
                                Modifier
                                    .fillMaxWidth()
                                    .padding(6.dp)
                                    .clickable {
                                        // Navigate to PDF Viewer with song ID and total page count
                                        navController.navigate("viewer/${song.id}/${song.pageCount}")
                                    },
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(song.title, modifier = Modifier.weight(1f), color = primaryTextColor)
                                if (isHost) {
                                    IconButton(onClick = {
                                        vm.removeSongFromQueue(roomCode, song.id)
                                    }) {
                                        Icon(
                                            Icons.Default.Delete,
                                            contentDescription = "Remove song",
                                            tint = Color.Red
                                        )
                                    }
                                }
                            }
                        }
                    }
                    if (isHost) {
                        Button(
                            onClick = { /* Navigate to song selection screen */ },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Add Song / Playlist")
                        }
                    }
                }
            }

            // Participants Section
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text("Participants", color = primaryTextColor)
                    LazyColumn {
                        items(state.participants) { participant ->
                            Row(
                                Modifier
                                    .fillMaxWidth()
                                    .padding(6.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(participant, modifier = Modifier.weight(1f), color = primaryTextColor)
                                if (isHost && participant != currentUserName) {
                                    IconButton(onClick = {
                                        vm.removeParticipant(roomCode, participant)
                                        onRemoveParticipant(participant)
                                    }) {
                                        Icon(
                                            Icons.Default.Delete,
                                            contentDescription = "Remove participant",
                                            tint = Color.Red
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Spacer(Modifier.weight(1f))

            // Leave Room Button
            Button(
                onClick = {
                    vm.leaveRoom()
                    onLeaveRoom()
                },
                colors = ButtonDefaults.buttonColors(containerColor = leaveButtonColor),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Leave Room", color = Color.White)
            }
        }
    }
}
