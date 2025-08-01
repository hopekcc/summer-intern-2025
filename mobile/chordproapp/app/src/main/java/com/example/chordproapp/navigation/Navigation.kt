package com.example.chordproapp.navigation

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.example.chordproapp.screens.HomeScreen
import com.example.chordproapp.screens.ProfileScreen
import com.example.chordproapp.screens.SearchScreen
import com.example.chordproapp.screens.SyncScreen

@Composable
fun AppNavigation(
    navController: NavHostController,
    titleText: String,
    setTitleText: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    NavHost(
        navController = navController,
        startDestination = "home",
        modifier = modifier
    ) {
        composable("home") {
            HomeScreen(
                titleText = titleText, // Username not title, title is seperate
            )
        }
        composable("search") { SearchScreen() }
        composable("profile") { ProfileScreen() }
        composable("sync") { SyncScreen() }
    }
}