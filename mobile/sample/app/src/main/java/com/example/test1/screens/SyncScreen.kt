package com.example.chordproapp.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HopeJamSyncScreen(navController: NavHostController) {
    var roomCode by remember { mutableStateOf("") }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("HopeJam Sync", color = Color.White) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color(0xFF231973))
            )
        },
        containerColor = Color(0xFFF7F7FF)
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            /** Header **/
            item {
                Text(
                    "Ready to Share Music Sheets?",
                    style = MaterialTheme.typography.headlineMedium,
                    color = Color(0xFF07277C)
                )
                Text(
                    "Create a new room or join an existing one",
                    style = MaterialTheme.typography.bodyLarge,
                    color = Color(0xFF07277C).copy(alpha = 0.6f),
                    modifier = Modifier.padding(top = 8.dp)
                )
            }

            /** Create Room Card **/
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                ) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier.padding(24.dp)
                    ) {
                        Icon(
                            Icons.Filled.PlayArrow,
                            contentDescription = null,
                            tint = Color(0xFF231973),
                            modifier = Modifier
                                .size(48.dp)
                                .padding(bottom = 16.dp)
                        )
                        Text("Create Room", style = MaterialTheme.typography.titleLarge, color = Color(0xFF07277C))
                        Text(
                            "You are the host! Start a new session and invite others.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = Color(0xFF07277C).copy(alpha = 0.6f),
                            modifier = Modifier.padding(vertical = 8.dp)
                        )

                        OutlinedTextField(
                            value = "",
                            onValueChange = {},
                            placeholder = { Text("Add songs or playlists to queue") },
                            singleLine = true,
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 8.dp),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = Color(0xFF231973),
                                unfocusedBorderColor = Color(0xFF231973).copy(alpha = 0.4f),
                                focusedContainerColor = Color.White,
                                unfocusedContainerColor = Color.White
                            )
                        )

                        Button(
                            onClick = { navController.navigate("joined_sync/ABC123") },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(48.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF231973))
                        ) {
                            Text("Create New Room")
                        }
                    }
                }
            }

            /** Join Room Card **/
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                ) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier.padding(24.dp)
                    ) {
                        Icon(
                            Icons.Filled.MusicNote,
                            contentDescription = null,
                            tint = Color(0xFF231973),
                            modifier = Modifier
                                .size(48.dp)
                                .padding(bottom = 16.dp)
                        )
                        Text("Join Room", style = MaterialTheme.typography.titleLarge, color = Color(0xFF07277C))
                        OutlinedTextField(
                            value = roomCode,
                            onValueChange = { roomCode = it },
                            placeholder = { Text("Enter room code (e.g. ABC123)") },
                            singleLine = true,
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 12.dp),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = Color(0xFF231973),
                                unfocusedBorderColor = Color(0xFF231973).copy(alpha = 0.4f),
                                focusedContainerColor = Color(0xFFF7F7FF),
                                unfocusedContainerColor = Color(0xFFF7F7FF)
                            )
                        )
                        Button(
                            onClick = { navController.navigate("joined_sync/${roomCode.ifEmpty { "ABC123" }}") },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(48.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF231973))
                        ) {
                            Text("Join Room")
                        }
                    }
                }
            }
        }
    }
}
