package com.example.test1.navigation

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import androidx.navigation.NavType
import com.example.test1.screens.HomeScreen
import com.example.test1.screens.ProfileScreen
import com.example.test1.screens.SearchScreen
import com.example.test1.screens.SyncScreen
import com.example.test1.screens.JoinedSyncScreen
import kotlin.random.Random

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
            HomeScreen(titleText = titleText)
        }
        composable("search") {
            SearchScreen()
        }
        composable("profile") {
            ProfileScreen()
        }

        // Sync Screen - Host or Join entry point
        composable("sync") {
            SyncScreen(
                navController = navController,
                onCreateRoomClicked = {
                    val newRoomCode = generateRoomCode()
                    val groupName = "My Group" // Replace with Firebase group name
                    val userName = getCurrentUserName() // Replace with Firebase user
                    navController.navigate("joined_sync/$newRoomCode/$groupName/true/$userName")
                },
                onJoinRoomClicked = { roomCode ->
                    val groupName = fetchGroupName(roomCode) // Fetch from Firebase
                    val userName = getCurrentUserName()
                    navController.navigate("joined_sync/$roomCode/$groupName/false/$userName")
                }
            )
        }

        // Joined Sync Screen - Shared for Host & Join
        composable(
            route = "joined_sync/{roomCode}/{groupName}/{isHost}/{currentUserName}",
            arguments = listOf(
                navArgument("roomCode") { type = NavType.StringType },
                navArgument("groupName") { type = NavType.StringType },
                navArgument("isHost") { type = NavType.BoolType },
                navArgument("currentUserName") { type = NavType.StringType }
            )
        ) { backStackEntry ->
            val roomCode = backStackEntry.arguments?.getString("roomCode") ?: "Unknown"
            val groupName = backStackEntry.arguments?.getString("groupName") ?: "Unknown"
            val isHost = backStackEntry.arguments?.getBoolean("isHost") ?: false
            val currentUserName = backStackEntry.arguments?.getString("currentUserName") ?: "User"

            val participants = fetchParticipants(roomCode, currentUserName)
            val nowPlaying = fetchNowPlaying(roomCode)

            JoinedSyncScreen(
                navController = navController,
                roomCode = roomCode,
                groupName = groupName,
                nowPlaying = nowPlaying,
                participants = participants,
                currentUserName = currentUserName,
                isHost = isHost,
                onRemoveParticipant = { participantName ->
                    removeParticipant(roomCode, participantName)
                },
                onLeaveRoom = {
                    navController.navigate("sync") {
                        popUpTo("sync") { inclusive = true }
                    }
                }
            )
        }
    }
}

// --- Placeholder Dynamic Functions ---
// Later: Replace with Firebase Firestore/Realtime Database calls

fun generateRoomCode(): String {
    val letters = ('A'..'Z').toList()
    val numbers = ('0'..'9').toList()
    return (1..3).map { letters.random() }.joinToString("") +
            (1..3).map { numbers.random() }.joinToString("")
}

fun getCurrentUserName(): String {
    // Later: Firebase Auth
    return "CurrentUser"
}

fun fetchGroupName(roomCode: String): String {
    // Later: Firestore fetch by roomCode
    return "Group-$roomCode"
}

fun fetchParticipants(roomCode: String, currentUser: String): List<String> {
    // Later: Firestore snapshot listener
    return listOf("Alice", "Bob", currentUser)
}

fun fetchNowPlaying(roomCode: String): String {
    // Later: Firestore document field
    return "Song Title Here"
}

fun removeParticipant(roomCode: String, participantName: String) {
    // Later: Firestore update
    println("Removed $participantName from $roomCode")
}
