package com.example.chordproapp.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.chordproapp.Song

@Composable
fun HomeScreen(
    titleText: String,
    modifier: Modifier = Modifier
) {

    // fake data
    val songs = listOf(
        Song("Baby", "Justin Bieber", "akdjaskdhas"),
        Song("Shape of You", "Ed Sheeran", "khaiuhdliuzfhuli"),
        Song("Hello", "Adele", "sajkdhasjkdh"),
        Song("Blinding Lights", "The Weeknd", "asjkdhaksjd"),
        Song("Levitating", "Dua Lipa", "akdjaskdhas"),
        Song("Uptown Funk", "Bruno Mars", "asdasdasd"),
        Song("Stay", "The Kid LAROI", "asjkdhasd"),
        Song("Bad Guy", "Billie Eilish", "akdjaskdhas"),
        Song("Peaches", "Justin Bieber", "akdjaskdhas"),
        Song("Senorita", "Shawn Mendes", "akdjaskdhas")
    )

    // "See more" variables
    var seeMore by remember { mutableStateOf(false) }
    val baseSongs = songs.take(3)
    val extraSongs = songs.drop(3).take(7)

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(start = 20.dp, top = 30.dp, end = 20.dp)
    ) {
        Text(text = "Tech Meets Music", fontSize = 40.sp, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(20.dp))
        Text(text = titleText, fontSize = 24.sp, modifier = Modifier.align(Alignment.Start))
        Spacer(modifier = Modifier.height(30.dp))
        Text(
            text = "Recently played",
            fontSize = 20.sp,
            modifier = Modifier.align(Alignment.CenterHorizontally)
        )
        Spacer(modifier = Modifier.height(16.dp))

        // Scrollable list of songs
        LazyColumn(modifier = modifier.fillMaxHeight()) {
            items(baseSongs) { song ->
                SongCard(song = song) {
                    println("Clicked: ${song.title} by ${song.artist}")
                }
            }

            if (seeMore) {
                items(extraSongs) { song ->
                    SongCard(song = song) {
                        println("Clicked: ${song.title} by ${song.artist}")
                    }
                }
            }

            // Only show toggle if more than 3 songs
            if (songs.size > 3) {
                item {
                    TextButton(
                        onClick = { seeMore = !seeMore },
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 8.dp)
                            .wrapContentWidth(Alignment.CenterHorizontally)
                    ) {
                        Text(text = if (seeMore) "See less" else "See more")
                    }
                }
            }
        }
    }
}

@Composable
fun SongCard(song: Song, onClick: () -> Unit = {}) {
    Card(
        modifier = Modifier
            .padding(8.dp)
            .fillMaxWidth()
            .clickable { onClick() },
        elevation = CardDefaults.cardElevation(5.dp)
    ) {
        Row(
            modifier = Modifier
                .padding(16.dp)
                .fillMaxWidth()
        ) {
            """
            Image(
                painter = painterResource(id = R.drawable.song_icon),
                contentDescription = "song icon",
                modifier = Modifier
                    .size(25.dp)
                    //.padding(end = 8.dp)
            )
            """
            Text(text = song.title, fontWeight = FontWeight.Bold, fontSize = 16.sp)
            Spacer(modifier = Modifier.weight(1f))
            Text(text = song.artist, fontWeight = FontWeight.Bold, fontSize = 16.sp)
        }
    }
}
