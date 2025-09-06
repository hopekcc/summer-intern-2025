package com.example.chordproapp

import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.navigation.compose.rememberNavController
import com.example.chordproapp.components.BottomNavigationBar
import com.example.chordproapp.data.repository.PlaylistRepository
import com.example.chordproapp.navigation.AppNavigation
import com.example.chordproapp.viewmodels.PlaylistViewModel
import com.example.chordproapp.ui.theme.ChordproappTheme
import com.example.chordproapp.screens.LoginScreen
import com.google.firebase.FirebaseApp
import com.google.firebase.auth.FirebaseAuth

class MainActivity : ComponentActivity() {
    private lateinit var auth: FirebaseAuth

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Firebase
        FirebaseApp.initializeApp(this)
        auth = FirebaseAuth.getInstance()

        setContent {
            ChordproappTheme {
                var username by remember { mutableStateOf("Hey, User! 👋🏻") }
                var isLoggedIn by remember { mutableStateOf(false) }
                var currentUserId by remember { mutableStateOf<String?>(null) }
                // Auth token
                var idToken by remember { mutableStateOf<String?>(null) }
                val navController = rememberNavController()

                // Create repository and ViewModel that will be recreated for each user
                var playlistRepository by remember { mutableStateOf<PlaylistRepository?>(null) }
                var playlistViewModel by remember { mutableStateOf<PlaylistViewModel?>(null) }

                // Function to clear user data and create new instances
                fun setupUserSession(userId: String, userEmail: String, token: String) {
                    currentUserId = userId
                    idToken = token
                    username = "Hey, ${userEmail.substringBefore("@")}! 👋🏻"

                    // Create new repository and ViewModel instances for this user
                    playlistRepository = PlaylistRepository { idToken }
                    playlistViewModel = PlaylistViewModel(playlistRepository!!, userId)

                    isLoggedIn = true
                    Log.d("MainActivity", "User session setup for: $userId with token: ${token.take(10)}...")
                }

                // Function to clear user session
                fun clearUserSession() {
                    auth.signOut()
                    isLoggedIn = false
                    currentUserId = null
                    idToken = null
                    username = "Hey, User! 👋🏻"
                    playlistRepository = null
                    playlistViewModel = null
                    Log.d("MainActivity", "User session cleared")
                }

                // Check if user is already logged in
                LaunchedEffect(Unit) {
                    val currentUser = auth.currentUser
                    if (currentUser != null) {
                        // Get Firebase ID token
                        currentUser.getIdToken(true)
                            .addOnSuccessListener { result ->
                                result.token?.let { token ->
                                    setupUserSession(
                                        userId = currentUser.uid,
                                        userEmail = currentUser.email ?: "User",
                                        token = token
                                    )
                                }
                            }
                            .addOnFailureListener { e ->
                                Log.e("MainActivity", "Failed to get ID token", e)
                                clearUserSession()
                            }
                    }
                }

                // Create idTokenProvider function
                val idTokenProvider: () -> String? = { idToken }

                if (isLoggedIn && playlistViewModel != null) {
                    Scaffold(
                        bottomBar = {
                            BottomNavigationBar(
                                navController = navController,
                                onLogout = { clearUserSession() }
                            )
                        }
                    ) { innerPadding ->
                        AppNavigation(
                            navController = navController,
                            titleText = username,
                            setTitleText = { username = it },
                            playlistViewModel = playlistViewModel!!,
                            idTokenProvider = idTokenProvider,
                            onLogout = { clearUserSession() },
                            modifier = Modifier.padding(innerPadding)
                        )
                    }
                } else {
                    LoginScreen(
                        onLoginSuccess = { userId, userEmail ->
                            // Get the current user and token after login
                            val currentUser = auth.currentUser
                            if (currentUser != null && currentUser.uid == userId) {
                                currentUser.getIdToken(true)
                                    .addOnSuccessListener { result ->
                                        result.token?.let { token ->
                                            setupUserSession(
                                                userId = userId,
                                                userEmail = userEmail, // Use the provided userEmail parameter
                                                token = token
                                            )
                                        }
                                    }
                                    .addOnFailureListener { e ->
                                        Log.e("MainActivity", "Failed to get ID token after login", e)
                                    }
                            } else {
                                Log.e("MainActivity", "User mismatch after login")
                            }
                        }
                    )
                }
            }
        }
    }
}