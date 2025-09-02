package com.example.chordproapp.navigation

import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
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



        //playlist screens:

        composable("profile") {
            ProfileScreen(navController, playlistViewModel,username = titleText, onLogout)
        }
        composable("allPlaylists") {
            AllPlaylists(navController, playlistViewModel)
        }
        composable("newPlaylist") {
            NewPlaylist(navController, playlistViewModel)
        }
        composable(
            route = "playlist/{playlistId}",
            arguments = listOf(navArgument("playlistId") { type = NavType.StringType }) // Changed from IntType to StringType for UUID support
        ) { backStackEntry ->
            val playlistId = backStackEntry.arguments?.getString("playlistId") ?: "" // Changed from getInt to getString
            val playlists by playlistViewModel.playlists.collectAsState(initial = emptyList())
            val playlist = playlists.find { it.id == playlistId }

            if (playlist != null) {
                Playlist(
                    playlistId = playlist.id,
                    playlistViewModel = playlistViewModel,
                    navController = navController
                )
            } else {
                Text("Loading playlist...")
            }
        }

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
