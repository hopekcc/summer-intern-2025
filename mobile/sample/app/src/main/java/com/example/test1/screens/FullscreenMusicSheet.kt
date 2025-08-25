package com.example.chordproapp.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore

@Composable
fun FullscreenMusicSheet(
    roomId: String,
    onExit: () -> Unit
) {
    // Firebase instances
    val auth = FirebaseAuth.getInstance()
    val firestore = FirebaseFirestore.getInstance()

    // State variables
    var pdfUri by remember { mutableStateOf<String?>(null) }
    var currentPage by remember { mutableStateOf(0) }
    var totalPages by remember { mutableStateOf(0) }
    var isHost by remember { mutableStateOf(false) }
    var isLoading by remember { mutableStateOf(true) }

    // Theme colors
    val backgroundColor = Color(0xFFF7F7FF)
    val primaryTextColor = Color(0xFF07277C)
    val exitButtonColor = Color(0xFFEA4E4E)

    // Real-time Firestore Listener
    LaunchedEffect(roomId) {
        firestore.collection("rooms").document(roomId)
            .addSnapshotListener { snapshot, error ->
                if (error != null) {
                    isLoading = false
                    return@addSnapshotListener
                }
                snapshot?.let {
                    pdfUri = it.getString("pdfUri")
                    currentPage = it.getLong("currentPage")?.toInt() ?: 0
                    totalPages = it.getLong("totalPages")?.toInt() ?: 0
                    isHost = it.getString("hostId") == auth.currentUser?.uid
                    isLoading = false
                }
            }
    }

    // UI Layout
    Box(
        Modifier
            .fillMaxSize()
            .background(backgroundColor),
        contentAlignment = Alignment.Center
    ) {
        if (isLoading) {
            CircularProgressIndicator(color = primaryTextColor)
        } else {
            Column(
                Modifier
                    .fillMaxSize()
                    .padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.SpaceBetween
            ) {
                // Header
                Text(
                    "Music Sheet",
                    color = primaryTextColor,
                    style = MaterialTheme.typography.titleLarge
                )

                // PDF Display Area
                Box(
                    Modifier
                        .fillMaxWidth()
                        .weight(1f)
                        .padding(16.dp),
                    contentAlignment = Alignment.Center
                ) {
                    if (pdfUri != null) {
                        // TODO: Replace with actual PDF rendering using pdfUri
                        Text(
                            text = "Page ${currentPage + 1} of $totalPages",
                            color = primaryTextColor.copy(alpha = 0.7f)
                        )
                    } else {
                        Text(
                            "No PDF found",
                            color = primaryTextColor.copy(alpha = 0.7f)
                        )
                    }
                }

                // Bottom Controls
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Button(
                        onClick = onExit,
                        colors = ButtonDefaults.buttonColors(containerColor = exitButtonColor)
                    ) {
                        Text("Exit", color = Color.White)
                    }
                    if (isHost) {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(
                                onClick = {
                                    if (currentPage > 0) {
                                        firestore.collection("rooms")
                                            .document(roomId)
                                            .update("currentPage", currentPage - 1)
                                    }
                                }
                            ) {
                                Text("Prev")
                            }
                            Button(
                                onClick = {
                                    if (currentPage < totalPages - 1) {
                                        firestore.collection("rooms")
                                            .document(roomId)
                                            .update("currentPage", currentPage + 1)
                                    }
                                }
                            ) {
                                Text("Next")
                            }
                        }
                    }
                }
            }
        }
    }
}
