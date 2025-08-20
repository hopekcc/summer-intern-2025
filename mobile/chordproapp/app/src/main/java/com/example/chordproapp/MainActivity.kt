package com.example.chordproapp

import android.os.Bundle
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
import com.example.chordproapp.ui.theme.PlaylistViewModel
import com.example.chordproapp.ui.theme.ChordproappTheme
import com.example.chordproapp.screens.LoginScreen
import com.google.firebase.FirebaseApp
import com.google.firebase.auth.FirebaseAuth

class MainActivity : ComponentActivity() {
    private lateinit var auth: FirebaseAuth

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Initialize Firebase
        FirebaseApp.initializeApp(this)
        auth = FirebaseAuth.getInstance()

        setContent {
            ChordproappTheme {
                var username by remember { mutableStateOf("Hey, User! 👋🏻") }
                var isLoggedIn by remember { mutableStateOf(false) }
                val navController = rememberNavController()

                // Check if user is already logged in
                LaunchedEffect(Unit) {
                    val currentUser = auth.currentUser
                    if (currentUser != null) {
                        isLoggedIn = true
                        username = "Hey, ${currentUser.email?.substringBefore("@") ?: "User"}! 👋🏻"
                    }
                }

                // Create shared ViewModel for sync-related screens
                val playlistViewModel = remember { PlaylistViewModel() }

                if (isLoggedIn) {
                    Scaffold(
                        bottomBar = {
                            BottomNavigationBar(
                                navController = navController,
                                onLogout = {
                                    auth.signOut()
                                    isLoggedIn = false
                                    username = "Hey, User! 👋🏻"
                                }
                            )
                        }
                    ) { innerPadding ->
                        AppNavigation(
                            navController = navController,
                            titleText = username,
                            setTitleText = { username = it },
                            playlistViewModel = playlistViewModel, // Pass to sync screens
                            onLogout = {
                                auth.signOut()
                                isLoggedIn = false
                                username = "Hey, User! 👋🏻"
                            },
                            modifier = Modifier.padding(innerPadding)
                        )
                    }
                } else {
                    LoginScreen(
                        onLoginSuccess = { email ->
                            isLoggedIn = true
                            username = "Hey, ${email.substringBefore("@")}! 👋🏻"
                        }
                    )
                }
            }
        }
    }
}