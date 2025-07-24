package com.example.test1

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.navigation.compose.rememberNavController
import com.example.test1.components.BottomNavigationBar
import com.example.test1.navigation.AppNavigation
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.jsoup.Jsoup
import java.io.IOException

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            var username by remember { mutableStateOf("Hey, User! 👋🏻") }
            val navController = rememberNavController()

            Scaffold(
                bottomBar = { BottomNavigationBar(navController) }
            ) { innerPadding ->
                AppNavigation(
                    navController = navController,
                    titleText = username,
                    setTitleText = { username = it },
                    modifier = Modifier.padding(innerPadding)
                )
            }
        }
    }
}
