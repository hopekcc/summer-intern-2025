package com.example.chordproapp.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun SyncScreen() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(30.dp)
    ) {
        Text("Sync", fontSize = 30.sp, fontWeight = FontWeight.Bold)
    }
}