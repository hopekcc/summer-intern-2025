package com.example.chordproapp.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun JoinedSyncScreen(navController: NavHostController, roomCode: String) {
    val nowPlaying = remember { mutableStateOf("Fur Elise") }
    val participants = remember { mutableStateListOf("You", "Alice") }
    val queue = remember { mutableStateListOf("Canon in D") }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Room $roomCode", color = Color.White) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color(0xFF231973))
            )
        },
        containerColor = Color(0xFFF7F7FF)
    ) { inner ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(inner)
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text("Group: MyGroup", color = Color(0xFF07277C))
            Text("Now Playing", color = Color(0xFF07277C))
            Text(nowPlaying.value)

            Card(
                Modifier
                    .fillMaxWidth()
                    .height(120.dp)
                    .clickable { /* toggle fullscreen */ },
                colors = CardDefaults.cardColors(containerColor = Color.White),
                shape = RoundedCornerShape(16.dp)
            ) {
                Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxSize()) {
                    Text("Tap to view music sheet (fullscreen)", color = Color(0xFF07277C))
                }
            }

            Text("Queue", color = Color(0xFF07277C))
            LazyColumn {
                items(queue) { song ->
                    Row(
                        Modifier
                            .fillMaxWidth()
                            .padding(vertical = 8.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(song)
                        TextButton(onClick = { queue.remove(song) }) {
                            Text("Remove", color = Color(0xFF07277C))
                        }
                    }
                }
            }

            Text("Participants", color = Color(0xFF07277C))
            LazyColumn {
                items(participants) { p ->
                    Row(
                        Modifier
                            .fillMaxWidth()
                            .padding(vertical = 8.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(p)
                        IconButton(onClick = { participants.remove(p) }) {
                            Icon(Icons.Default.Delete, contentDescription = null, tint = Color.Red)
                        }
                    }
                }
            }

            Spacer(Modifier.weight(1f))
            Button(
                onClick = { navController.popBackStack() },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF231973))
            ) {
                Text("Leave Room", color = Color.White)
            }
        }
    }
}
