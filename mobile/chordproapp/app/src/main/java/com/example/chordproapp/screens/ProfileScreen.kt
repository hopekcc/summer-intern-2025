package com.example.chordproapp.screens

import android.annotation.SuppressLint
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
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
import androidx.navigation.compose.rememberNavController
import com.example.chordproapp.R
import com.example.chordproapp.ui.theme.PlaylistViewModel

@Composable
fun ProfileScreen(
    navController: NavController,
    playlistViewModel: PlaylistViewModel,
    onLogout: () -> Unit
) {
    val playlists = playlistViewModel.playlists
    val first3Playlists = playlists.take(3)

    Scaffold { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(25.dp)
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // 🔓 Logout button at the top
            Button(
                onClick = { onLogout() },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 16.dp)
                    .height(50.dp)
            ) {
                Text("Log Out", fontSize = 18.sp)
            }

            // Profile picture and name section
            Row {
                val profilePicture = painterResource(R.drawable.user_icon)
                Image(
                    painter = profilePicture,
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier
                        .size(90.dp)
                        .clip(CircleShape)
                )
                Column(modifier = Modifier.padding(start = 15.dp)) {
                    Text(stringResource(R.string.username), fontSize = 35.sp, fontWeight = Bold)
                    val idNumber = stringResource(R.string.idNum) + " " + stringResource(R.string.id)
                    Text(idNumber, fontSize = 18.sp, fontWeight = Bold)

                    Row {
                        val followers = stringResource(R.string.followers) + " " + stringResource(R.string.followerCount)
                        Text(followers, fontSize = 16.sp)
                        Spacer(modifier = Modifier.width(16.dp))
                        val following = stringResource(R.string.following) + " " + stringResource(R.string.followingCount)
                        Text(following, fontSize = 16.sp)
                    }
                }
            }

            Spacer(modifier = Modifier.height(50.dp))

            // First 3 playlists
            first3Playlists.forEach { name ->
                PlaylistButton(text = name) {
                    navController.navigate("playlist/${name}")
                }
                Spacer(modifier = Modifier.height(15.dp))
            }

            // See more + create new playlist
            Button(onClick = { navController.navigate("allPlaylists") }) {
                Text(stringResource(R.string.seeMore))
            }

            Spacer(modifier = Modifier.height(20.dp))

            Button(
                onClick = { navController.navigate("newPlaylist") },
                modifier = Modifier
                    .height(60.dp)
                    .width(250.dp)
            ) {
                Text(stringResource(R.string.createNewPlaylist), fontSize = 20.sp)
            }
        }
    }
}



@Composable
fun PlaylistButton(text: String, onClick: () -> Unit) {
    Button(
        onClick = onClick,
        modifier = Modifier
            .height(60.dp)
            .width(350.dp)
    ) {
        Text(text, fontSize = 35.sp)
    }
}

@Composable
fun Playlist(title: String, songCount: Int, playlistViewModel: PlaylistViewModel) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(30.dp)
    ) {
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(title, fontSize = 30.sp, fontWeight = Bold)
                Spacer(modifier = Modifier.weight(1f))
                Button(onClick = { playlistViewModel.deletePlaylist(title) }) {
                    Text("Delete")
                }
            }
            Spacer(modifier = Modifier.height(15.dp))
            repeat(songCount) {
                SongButton(onClick = {})
            }
        }
    }
}

@Composable
fun SongButton(onClick: () -> Unit) {
    OutlinedButton(
        onClick = { onClick() },
        modifier = Modifier.width(350.dp)
    ) {
        Row(Modifier.fillMaxWidth()) {
            Text("Song Name")
            Spacer(modifier = Modifier.weight(1f))
            Text("Song Artist")
        }
    }
}

@Composable
fun AllPlaylists(navController: NavController, playlistViewModel: PlaylistViewModel) {
    val playlists = playlistViewModel.playlists

    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(30.dp)
    ) {
        Text("All Playlists", fontSize = 40.sp)
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Spacer(modifier = Modifier.height(60.dp))
            playlists.forEach { name ->
                PlaylistButton(text = name) {
                    navController.navigate("playlist/${name}")
                }
                Spacer(modifier = Modifier.height(15.dp))
            }
        }
    }
}

@Composable
fun NewPlaylist(navController: NavController, playlistViewModel: PlaylistViewModel) {
    var playlistName by remember { mutableStateOf("") }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(30.dp)
    ) {
        Column {
            TextField(
                value = playlistName,
                onValueChange = { playlistName = it },
                label = { Text("Playlist Name: ") }
            )
            Button(
                onClick = {
                    playlistViewModel.addPlaylist(playlistName)
                    navController.navigate("playlist/${playlistName}")
                    playlistName = ""
                },
                enabled = playlistName.isNotBlank()
            ) {
                Text("Create")
            }
        }
    }
}

@SuppressLint("ViewModelConstructorInComposable")
@Preview(showBackground = true)
@Composable
fun ProfileScreenPreview() {
    val previewNavController = rememberNavController()
    val previewPlaylistViewModel = PlaylistViewModel()
    ProfileScreen(
        navController = previewNavController,
        playlistViewModel = previewPlaylistViewModel,
        onLogout = {}
    )
}
