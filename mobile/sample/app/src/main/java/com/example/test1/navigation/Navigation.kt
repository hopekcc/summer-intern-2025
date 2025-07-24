package com.example.test1.navigation

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.example.test1.screens.HomeScreen
import com.example.test1.screens.ProfileScreen
import com.example.test1.screens.SearchScreen
import com.example.test1.screens.SyncScreen
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.jsoup.Jsoup
import java.io.IOException

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