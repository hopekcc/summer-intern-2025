package com.example.chordproapp.navigation

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.example.chordproapp.screens.HomeScreen
import com.example.chordproapp.screens.SearchScreen
import com.example.chordproapp.screens.SyncScreen
import com.example.chordproapp.ui.theme.PlaylistViewModel
import com.example.chordproapp.screens.AllPlaylists
import com.example.chordproapp.screens.NewPlaylist
import com.example.chordproapp.screens.Playlist
import com.example.chordproapp.screens.ProfileScreen

@Composable
fun AppNavigation(
    navController: NavHostController,
    titleText: String,
    setTitleText: (String) -> Unit,
    playlistViewModel: PlaylistViewModel,
    onLogout: () -> Unit,
    modifier: Modifier = Modifier
) {
    NavHost(
        navController = navController,
        startDestination = "home"
    ) {
        composable("home") {
            HomeScreen(titleText = titleText)
        }
        composable("search") { SearchScreen() }
        composable("sync") { SyncScreen() }
        composable("profile") {
            ProfileScreen(navController, playlistViewModel, onLogout)
        }
        composable("allPlaylists") {
            AllPlaylists(navController, playlistViewModel)
        }
        composable("newPlaylist") {
            NewPlaylist(navController, playlistViewModel)
        }
        composable("playlist/{name}") { backStackEntry ->
            val name = backStackEntry.arguments?.getString("name") ?: "Playlist Name"
            Playlist(title = name, songCount = 6, playlistViewModel)
        }
    }
}