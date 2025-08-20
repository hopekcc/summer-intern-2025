package com.example.chordproapp.navigation

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.example.chordproapp.screens.SearchScreen
import com.example.chordproapp.screens.SyncScreen
import com.example.chordproapp.screens.JoinedSyncScreen
import com.example.chordproapp.viewmodels.PlaylistViewModel
import com.example.chordproapp.screens.AllPlaylists
import com.example.chordproapp.screens.NewPlaylist
import com.example.chordproapp.screens.Playlist
import com.example.chordproapp.screens.ProfileScreen
import com.example.chordproapp.screens.Viewer

@Composable
fun AppNavigation(
    navController: NavHostController,
    titleText: String,
    setTitleText: (String) -> Unit,
    playlistViewModel: PlaylistViewModel,
    idTokenProvider: () -> String?,
    onLogout: () -> Unit,
    modifier: Modifier = Modifier
) {
    NavHost(
        navController = navController,
        startDestination = "sync" // Start with Sync screen
    ) {
        composable("sync") { SyncScreen(navController) }

        composable("joined_sync/{roomCode}") { backStackEntry ->
            val roomCode = backStackEntry.arguments?.getString("roomCode") ?: ""
            JoinedSyncScreen(navController, roomCode)
        }

        composable("search") {
            SearchScreen(
                navController = navController,  // Add this line
                idTokenProvider = idTokenProvider
            )
        }

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

        // Add this to your existing Navigation.kt file in the NavHost composable
        composable(
            route = "viewer/{songId}",
            arguments = listOf(navArgument("songId") { type = NavType.IntType })
        ) { backStackEntry ->
            val songId = backStackEntry.arguments?.getInt("songId") ?: 0
            Viewer(
                songId = songId,
                onClose = { navController.popBackStack() },
                idTokenProvider = idTokenProvider
            )
        }
    }
}