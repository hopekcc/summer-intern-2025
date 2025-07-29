package com.example.test1

import android.R.attr.onClick
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight.Companion.Bold
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
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
                    startDestination = "HomeScreen",
                    modifier = Modifier.padding(innerPadding)
                )
                {
                    composable("HomeScreen") {
                        HomeScreen(
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
                    composable("sync") {
                        SyncScreen()
                    }
                    composable("profile") {
                        ProfileScreen(navController)
                    }
                    composable("profilePlaylist1") {
                        profilePlaylist1()
                    }
                    composable("profilePlaylist2") {
                        profilePlaylist2()
                    }
                    composable("profilePlaylist3") {
                        profilePlaylist3()
                    }
                    composable("playlist4") {
                        playlist4()
                    }
                    composable("playlist5") {
                        playlist5()
                    }
                    composable("allPlaylists") {
                        allPlaylists(navController)
                    }
                    composable("newPlaylistName") {
                        newPlaylistName()
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
fun HomeScreen(
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
    Box(modifier = Modifier
        .fillMaxSize()
        .padding(30.dp)) {
        Text(
            "Search",
            fontSize = 30.sp,
            fontWeight = Bold
        )
    }
}

@Composable
fun SyncScreen() {
    Box(modifier = Modifier
        .fillMaxSize()
        .padding(30.dp)) {
        Text(
            "Sync",
            fontSize = 30.sp,
            fontWeight = Bold
        )
    }
}

//@Composable
//fun LibraryScreen() {
//    Box(modifier = Modifier.fillMaxSize()
//                            .padding(30.dp)) {
//        Text("Library",
//            fontSize = 30.sp,
//            fontWeight = Bold)
////        LazyColumn(contentPadding = it) {
////            items(savedSongs) {
////                SavedSongItem(
////                    savedSong = it,
////                    modifier = Modifier.padding()
////                )
////            }
////        }
//    }
//}

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


@Composable
fun ProfileScreen(navController: NavController) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(25.dp)
    ) {
        Row {
            val profilePicture = painterResource(R.drawable.user_icon_on_transparent_background_free_png)
            Image(
                painter = profilePicture, //ADD change pfp icon (pencil)
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .size(90.dp)
                    .clip(CircleShape)
            )
            Column(
                modifier = Modifier.padding(start = 15.dp)
            ) {
                Text(
                    stringResource(R.string.username),
                    fontSize = 35.sp,
                    fontWeight = Bold
                )

                val idNumber = stringResource(R.string.idNum) + " " + stringResource(R.string.id)
                Text(
                    idNumber,
                    fontSize = 18.sp,
                    fontWeight = Bold
                )

                Row() {
                    val followers = stringResource(R.string.followers) + " " + stringResource(R.string.followerCount)
                    Text(
                        followers,
                        fontSize = 16.sp
                    )
                    Text("    ")
                    val following = stringResource(R.string.following) + " " + stringResource(R.string.followingCount)
                    Text(
                        following,
                        fontSize = 16.sp
                    )
                }
            }
        }
        Column {
            Spacer(modifier = Modifier.height(120.dp))

            Column(
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Button(
                    onClick = { navController.navigate("profilePlaylist1") },
                    modifier = Modifier
                        .height(60.dp)
                        .width(350.dp)
                ) {
                    Text(
                        stringResource(R.string.playlist1),
                        fontSize = 35.sp
                    )
                }

                Spacer(modifier = Modifier.height(15.dp))

                Button(
                    onClick = { navController.navigate("profilePlaylist2") },
                    modifier = Modifier
                        .height(60.dp)
                        .width(350.dp)
                ) {
                    Text(
                        stringResource(R.string.playlist2),
                        fontSize = 35.sp
                    )
                }

                Spacer(modifier = Modifier.height(15.dp))

                Button(
                    onClick = { navController.navigate("profilePlaylist3") },
                    modifier = Modifier
                        .height(60.dp)
                        .width(350.dp)
                ) {
                    Text(
                        stringResource(R.string.playlist3),
                        fontSize = 35.sp
                    )
                }

                Spacer(modifier = Modifier.height(15.dp))

                Button(
                    onClick = {navController.navigate("allPlaylists")} ) {
                    Text(stringResource(R.string.seeMore))
                }

                Spacer(modifier = Modifier.height(200.dp))

                Button(
                    onClick = {navController.navigate("newPlaylistName")},
                    modifier = Modifier
                        .height(60.dp)
                        .width(250.dp)) {
                    Text(stringResource(R.string.createNewPlaylist),
                        fontSize = 20.sp)
                }

            }

        }

    }
}

@Composable
fun songButton(onClick: () -> Unit) {
    OutlinedButton(
        onClick = { onClick() },
        modifier = Modifier.width(350.dp)
    ) {
        Row(Modifier.fillMaxWidth()) {
            Text("Song Name")
            Text("Song Artist")
        }
    }
}
@Composable
fun profilePlaylist1() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(30.dp)
    ) {
        Column {
            Text(
                "Playlist 1 Name",
                fontSize = 30.sp,
                fontWeight = Bold
            )
            Spacer(modifier = Modifier.height(15.dp))

            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
         }
    }
}
@Composable
fun profilePlaylist2() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(30.dp)
    ) {
        Column {
            Text(
                "Playlist 2 Name",
                fontSize = 30.sp,
                fontWeight = Bold
            )
            Spacer(modifier = Modifier.height(15.dp))

            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
        }
    }
}
@Composable
fun profilePlaylist3() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(30.dp)
    ) {
        Column {
            Text(
                "Playlist 3 Name",
                fontSize = 30.sp,
                fontWeight = Bold
            )
            Spacer(modifier = Modifier.height(15.dp))

            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})

        }
    }
}
@Composable
fun playlist4() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(30.dp)
    ) {
        Column {
            Text(
                "Playlist 4 Name",
                fontSize = 30.sp,
                fontWeight = Bold
            )
            Spacer(modifier = Modifier.height(15.dp))

            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})

        }
    }
}
@Composable
fun playlist5() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(30.dp)
    ) {
        Column {
            Text(
                "Playlist 5 Name",
                fontSize = 30.sp,
                fontWeight = Bold
            )
            Spacer(modifier = Modifier.height(15.dp))

            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
            songButton(onClick = {})
        }
    }
}

@Composable
fun allPlaylists(navController: NavController) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(30.dp)
    ) {
        Text("All Playlists",
            fontSize = 40.sp)

        Column(
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(60.dp))

            Button(
                onClick = { navController.navigate("profilePlaylist1") },
                modifier = Modifier
                    .height(60.dp)
                    .width(350.dp)
            ) {
                Text(
                    stringResource(R.string.playlist1),
                    fontSize = 35.sp
                )
            }

            Spacer(modifier = Modifier.height(15.dp))

            Button(
                onClick = { navController.navigate("profilePlaylist2") },
                modifier = Modifier
                    .height(60.dp)
                    .width(350.dp)
            ) {
                Text(
                    stringResource(R.string.playlist2),
                    fontSize = 35.sp
                )
            }

            Spacer(modifier = Modifier.height(15.dp))

            Button(
                onClick = { navController.navigate("profilePlaylist3") },
                modifier = Modifier
                    .height(60.dp)
                    .width(350.dp)
            ) {
                Text(
                    stringResource(R.string.playlist3),
                    fontSize = 35.sp
                )
            }

            Spacer(modifier = Modifier.height(15.dp))

            Button(
                onClick = { navController.navigate("playlist4") },
                modifier = Modifier
                    .height(60.dp)
                    .width(350.dp)
            ) {
                Text(
                    stringResource(R.string.playlist4),
                    fontSize = 35.sp
                )
            }

            Spacer(modifier = Modifier.height(15.dp))

            Button(
                onClick = { navController.navigate("playlist5") },
                modifier = Modifier
                    .height(60.dp)
                    .width(350.dp)
            ) {
                Text(
                    stringResource(R.string.playlist5),
                    fontSize = 35.sp
                )
            }
        }
    }
}

@Composable
fun newPlaylistName() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(30.dp)
    ) {
        Text(stringResource(R.string.newPlaylistName),
            fontSize = 35.sp)
    }
}



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
    val items = listOf("HomeScreen", "search", "sync", "profile")
    NavigationBar {
        items.forEach { screen ->
            val icon = when (screen) {
                "HomeScreen" -> R.drawable.musical_note_flat_icon_png
                "search" -> R.drawable.search_logo
                "sync" -> R.drawable.songlibrary
                "profile" -> R.drawable.user_icon_on_transparent_background_free_png
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
                            "HomeScreen" -> "Home"
                            "search" -> "Search"
                            "sync" -> "Sync"
                            "profile" -> "Profile"
                            else -> "Menu"
                        }
                    )
                }
            )
        }
    }
}

//@Preview(showBackground = true)
//@Composable
//fun HomeScreenPreview() {
//    HomeScreen(
//        titleText = "Tech meets Music",
//        onButtonClick = {}
//    )
//}
//
//@Preview(showBackground = true)
//@Composable
//fun SearchScreenPreview() {
//    SearchScreen()
//}
//
//@Preview(showBackground = true)
//@Composable
//fun SyncScreenPreview() {
//    SyncScreen()
//}

//@Preview(showBackground = true)
//@Composable
//fun ProfileScreenPreview() {
//    val profileNavController = rememberNavController()
//    ProfileScreen(navController = profileNavController)
//}

@Preview(showBackground = true)
@Composable
fun Playlist1Preview() {
    profilePlaylist1()
}

