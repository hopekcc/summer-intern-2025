package com.example.test1

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.annotation.DrawableRes
import androidx.annotation.StringRes
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ModifierLocalBeyondBoundsLayout
import androidx.compose.ui.res.dimensionResource
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight.Companion.Bold
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import androidx.navigation.compose.*
import androidx.navigation.compose.NavHost
import kotlinx.coroutines.*
import org.jsoup.Jsoup
import java.io.IOException

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            var titleText by remember { mutableStateOf("Tech meets Music") }
            val navController = rememberNavController()

            Scaffold(
                topBar = { TopAppBar() },
                bottomBar = { BottomNavigationBar(navController = navController) }
            ) { innerPadding ->
                NavHost(
                    navController = navController,
                    startDestination = "songScreen",
                    modifier = Modifier.padding(innerPadding)
                )
                {
                    composable("songScreen") {
                        SongScreen(
                            titleText = titleText,
                            onButtonClick = {
                                CoroutineScope(Dispatchers.IO).launch {
                                    val result =
                                        fetchTextFromWeb("http://getsome.org/guitar/olga/chordpro/b/Beatles/HeyJude.chopro")
                                    withContext(Dispatchers.Main) {
                                        titleText = result
                                    }
                                }
                            }
                        )
                    }
                    composable("search") {
                        SearchScreen()
                    }
                    composable("profile") {
                        ProfileScreen()
                    }
                    composable("library") {
                        LibraryScreen()
                    }
                }
            }
        }
    }
}

// Web Fetch Function
fun fetchTextFromWeb(url: String): String {
    return try {
        val doc = Jsoup.connect(url).get()
        doc.body().text()
    } catch (e: IOException) {
        "Error: ${e.message}"
    }
}


@Composable
fun SongScreen(
    titleText: String,
    onButtonClick: () -> Unit,
    modifier: Modifier = Modifier
) {
        Column(
            modifier = modifier
                .fillMaxSize()
                .padding(vertical = 50.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(titleText, fontSize = 24.sp)
            Spacer(modifier = Modifier.height(20.dp))
            Button(onClick = onButtonClick) {
                Text("Upload Song File", fontSize = 20.sp)
            }
            Spacer(modifier = Modifier.height(80.dp))

        }
    }

@Composable
fun SearchScreen() {
    Box(modifier = Modifier.fillMaxSize()
                            .padding(30.dp)) {
        Text(
            "Search",
            fontSize = 30.sp,
            fontWeight = Bold
        )
    }
}
@Composable
fun ProfileScreen() {
    Box(modifier = Modifier.fillMaxSize()
                            .padding(30.dp)) {
        Text("Profile",
            fontSize = 30.sp,
            fontWeight = Bold)
    }
}

@Composable
fun LibraryScreen() {
    Box(modifier = Modifier.fillMaxSize()
                            .padding(30.dp)) {
        Text("Library",
            fontSize = 30.sp,
            fontWeight = Bold)
//        LazyColumn(contentPadding = it) {
//            items(savedSongs) {
//                SavedSongItem(
//                    savedSong = it,
//                    modifier = Modifier.padding()
//                )
//            }
//        }
    }
}

//@Composable
//fun SavedSongItem(
//    savedSong: SavedSong,
//    modifier: Modifier = Modifier
//) {
//    Card {
//        Row() {
//            Image()
//            Text(savedSong.title)
//            Text(savedSong.artist)
//        }
//    }
//}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TopAppBar(modifier: Modifier = Modifier) {
    val musicNote = painterResource(R.drawable.musical_note_flat_icon_png)
    CenterAlignedTopAppBar(
        title = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center
            ) {
                Image(
                    painter = musicNote,
                    contentDescription = null,
                    modifier = Modifier.size(50.dp)
                )
                Text(
                    text = "Tech meets Music",
                    fontSize = 35.sp,
                    modifier = modifier.padding(start = 10.dp)
                )
            }
        },
        modifier = modifier
    )
}

@Composable
fun BottomNavigationBar(navController: NavHostController) {
    val items = listOf("songScreen", "search", "profile", "library")
    NavigationBar {
        items.forEach { screen ->
            val icon = when (screen) {
                "songScreen" -> R.drawable.musical_note_flat_icon_png
                "profile" -> R.drawable.user_icon_on_transparent_background_free_png
                "library" -> R.drawable.songlibrary
                "search" -> R.drawable.search_logo
                else -> R.drawable.musical_note_flat_icon_png
            }
            NavigationBarItem(
                selected = false,
                onClick = { navController.navigate(screen) },
                icon = {
                    Icon(
                        painter = painterResource(id = icon),
                        contentDescription = screen,
                        modifier = Modifier.size(40.dp)
                    )
                },
                label = {
                    Text(
                        when (screen) {
                            "songScreen" -> "Home"
                            "profile" -> "Profile"
                            "library" -> "Library"
                            "search" -> "Search"
                            else -> "Menu"
                        }
                    )
                }
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
fun SongScreenPreview() {
    SongScreen(
        titleText = "Tech meets Music",
        onButtonClick = {}
    )
}

@Preview(showBackground = true)
@Composable
fun SearchScreenPreview() {
    SearchScreen()
}

@Preview(showBackground = true)
@Composable
fun ProfileScreenPreview() {
    ProfileScreen()
}

@Preview(showBackground = true)
@Composable
fun LibraryScreenPreview() {
    LibraryScreen()
}

