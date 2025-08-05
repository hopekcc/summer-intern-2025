package com.example.chordproapp.components

import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ExitToApp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.example.chordproapp.R

@Composable
fun BottomNavigationBar(
    navController: NavHostController,
    onLogout: () -> Unit
) {
    val items = listOf("home", "search", "sync", "profile")
    var showLogoutDialog by remember { mutableStateOf(false) }

    NavigationBar {
        items.forEach { screen ->
            val icon = when (screen) {
                "home" -> R.drawable.home_logo
                "profile" -> R.drawable.user_icon
                "search" -> R.drawable.search_logo
                "sync" -> R.drawable.sync_logo
                else -> R.drawable.home_logo
            }
            NavigationBarItem(
                selected = false,
                onClick = {
                    if (screen == "profile") {
                        showLogoutDialog = true
                    } else {
                        navController.navigate(screen)
                    }
                },
                icon = {
                    Icon(
                        painter = painterResource(id = icon),
                        contentDescription = screen,
                        modifier = Modifier.size(40.dp)
                    )
                },
                label = {
                    Text(
                        when (screen) {
                            "home" -> "Home"
                            "profile" -> "Profile"
                            "search" -> "Search"
                            "sync" -> "Sync"
                            else -> "Menu"
                        }
                    )
                }
            )
        }
    }

    // Logout Confirmation Dialog
    if (showLogoutDialog) {
        AlertDialog(
            onDismissRequest = { showLogoutDialog = false },
            title = { Text("Logout") },
            text = { Text("Are you sure you want to logout?") },
            confirmButton = {
                TextButton(
                    onClick = {
                        showLogoutDialog = false
                        onLogout()
                    }
                ) {
                    Text("Yes")
                }
            },
            dismissButton = {
                TextButton(
                    onClick = { showLogoutDialog = false }
                ) {
                    Text("No")
                }
            }
        )
    }
}