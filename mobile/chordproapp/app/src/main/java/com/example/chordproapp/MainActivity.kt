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
                // Auth token
                var idToken by remember { mutableStateOf<String?>(null) }
                val navController = rememberNavController()

                // Check if user is already logged in
                LaunchedEffect(Unit) {
                    val currentUser = auth.currentUser
                    if (currentUser != null) {
                        isLoggedIn = true
                        username = "Hey, ${currentUser.email?.substringBefore("@") ?: "User"}! 👋🏻"

                        // Firebase ID token
                        currentUser.getIdToken(true)
                            .addOnSuccessListener { result ->
                                idToken = result.token
                                Log.d("MainActivity", "Got ID token: $idToken")
                            }
                            .addOnFailureListener { e ->
                                Log.e("MainActivity", "Failed to get ID token", e)
                            }
                    }
                }

                // Create shared ViewModel for sync-related screens
                val playlistViewModel = remember { PlaylistViewModel() }

                // Create idTokenProvider function
                val idTokenProvider: () -> String? = { idToken }

                if (isLoggedIn) {
                    Scaffold(
                        bottomBar = {
                            BottomNavigationBar(
                                navController = navController,
                                onLogout = {
                                    auth.signOut()
                                    isLoggedIn = false
                                    username = "Hey, User! 👋🏻"
                                    idToken = null
                                }
                            )
                        }
                    ) { innerPadding ->
                        AppNavigation(
                            navController = navController,
                            titleText = username,
                            setTitleText = { username = it },
                            playlistViewModel = playlistViewModel, // Pass to sync screens
                            idTokenProvider = idTokenProvider, // Pass the token provider
                            onLogout = {
                                auth.signOut()
                                isLoggedIn = false
                                username = "Hey, User! 👋🏻"
                                idToken = null
                            },
                            modifier = Modifier.padding(innerPadding)
                        )
                    }
                } else {
                    LoginScreen(
                        onLoginSuccess = { email ->
                            isLoggedIn = true
                            username = "Hey, ${email.substringBefore("@")}! 👋🏻"

                            // Get token after login too
                            auth.currentUser?.getIdToken(true)
                                ?.addOnSuccessListener { result ->
                                    idToken = result.token
                                    Log.d("MainActivity", "Got ID token after login: $idToken")
                                }
                        }
                    )
                }
            }
        }
    }
}