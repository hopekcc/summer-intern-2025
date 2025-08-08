package com.example.test1.components

import androidx.compose.foundation.layout.size
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.example.test1.R

@Composable
fun BottomNavigationBar(navController: NavHostController) {
    val items = listOf("home", "search", "sync", "profile")
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
                onClick = { navController.navigate(screen) },
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
}
