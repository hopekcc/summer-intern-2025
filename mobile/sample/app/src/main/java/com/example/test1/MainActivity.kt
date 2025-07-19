package com.example.test1

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.shape.RoundedCornerShape

// Song data model with title and lyrics (in ChordPro-like format)
data class Song(val title: String, val chordProText: String)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Set the UI content to the navigation screen
        setContent {
            AppNavigator()
        }
    }
}

// Determines which screen to show (home, local playlist, or web view)
@Composable
fun AppNavigator() {
    var screenState by remember { mutableStateOf("home") }

    when (screenState) {
        "home" -> HomeScreen(
            onLocalClick = { screenState = "local" },
            onWebClick = { screenState = "web" }
        )
        "local" -> LocalSongLibraryScreen(onBack = { screenState = "home" })
        "web" -> WebRedirectScreen(onBack = { screenState = "home" })
    }
}

// First screen user sees – choose between local or web library
@Composable
fun HomeScreen(onLocalClick: () -> Unit, onWebClick: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 32.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.Top,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // Title banner box
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 32.dp, bottom = 32.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(Color(0xFFBBDEFB)) // Light blue
                .padding(vertical = 24.dp)
        ) {
            Text(
                text = "Tech Meets Music",
                fontSize = 28.sp,
                color = Color(0xFF0D47A1), // Dark blue
                modifier = Modifier.align(Alignment.Center)
            )
        }

        // Button to go to local song list
        Button(
            onClick = onLocalClick,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("🎵 Browse Local Playlist")
        }

        Spacer(modifier = Modifier.height(20.dp))

        // Button to go to web redirect
        Button(
            onClick = onWebClick,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("🌐 Browse From Web")
        }
    }
}

// Screen that shows local hardcoded song list
@Composable
fun LocalSongLibraryScreen(onBack: () -> Unit) {
    // Hardcoded snippets of sample songs that will be replaced with ChordPro files
    val songs = listOf(
        Song("Hey Jude – The Beatles", """
[D]Hey Jude, don't [A]make it bad  
[A7]Take a sad song and [D]make it better  
[G]Remember to let her into your heart  
[Em]Then you can start to [A7]make it better
""".trimIndent()),

        Song("Oceans & Engines – NIKI", """
[Cm]Saturday sunset-- we’re [Bb]lying on my bed with [Ab]five hours to [Eb]go  
[Cm]Fingers entwined and so were our [Bb]minds crying [Ab]'I don’t want you to [Eb]go'  
[Cm]You wiped away tears but not [Bb]fears under the [Ab]still and clear indigo  
You said, ‘[Cm]Baby don’t cry, we’ll be [Bb]fine, you’re the [Ab]one thing I swear I [Eb]can’t outgrow’

[Chorus]  
[Eb]But I’m letting [Cm]go  
I’m givin’ up the [Ab]ghost  
But don’t get me [Ab]wrong  
I’ll always love you, that’s why  
I wrote you this very last [Bb]song  
""".trimIndent()),

        Song("My Heart It Beats For You – grentperez", """
[A]My heart it beats for [Amaj7]you  
[Gmaj7]Though we are miles apart  
[F#m7]My lovin', it will always [Fm]follow [F]you  
[Bm7]More and more each [A]day  
[Amaj7]My heart it beats for you  
[Gmaj7]And when the sun sleeps at night  
[F#m7]It's the perfect time  
[Fmaj7]'Cause I get to dream of you  
[Bm7]While waiting for the [Amaj7]morning [Dmaj7]light  
""".trimIndent()),

        Song("4ME 4ME – Malcom Todd", """
[Em]I just want you  
[Am]Touching my face  
[Bm7]Look at my eyes  
[B7]Can you not stay?  
[Em]I just want you  
[Am]Look at my face  
[Bm7]Look at my eyes  
[B7]Are you gon' stay?  
[Em]For me, for me  
[Am] [Bm7]I want it all  
[B7]Give my everything  
[Em]To you, to you  
[Am] [Bm7] [B7]What's mine is yours  
""".trimIndent())
    )

    var selectedSong by remember { mutableStateOf<Song?>(null) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        // Back button to return to Home
        Button(onClick = onBack) {
            Text("← Back")
        }

        // Section title
        Text(
            "Local Playlist",
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.padding(vertical = 16.dp)
        )

        // Scrollable list of songs
        LazyColumn(modifier = Modifier.weight(1f)) {
            items(songs) { song ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 8.dp)
                        .clickable { selectedSong = song }, // Tap to view full song
                    elevation = CardDefaults.cardElevation(4.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(text = song.title, style = MaterialTheme.typography.titleLarge)
                        Text(
                            text = song.chordProText.take(50) + "...", // Preview of lyrics
                            style = MaterialTheme.typography.bodyMedium,
                            modifier = Modifier.padding(top = 4.dp)
                        )
                    }
                }
            }
        }

        // Show full song text when selected
        selectedSong?.let {
            Divider(modifier = Modifier.padding(vertical = 8.dp))
            Text(
                "Now Playing: ${it.title}",
                style = MaterialTheme.typography.titleMedium
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(it.chordProText)
        }
    }
}

// Immediately opens a web browser to Google and gives option to go back
@Composable
fun WebRedirectScreen(onBack: () -> Unit) {
    val context = LocalContext.current

    // Launch Google in browser when this screen is composed
    LaunchedEffect(Unit) {
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://www.google.com"))
        context.startActivity(intent)
    }

    // UI while redirecting
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text("Opening browser...", fontSize = 20.sp)
        Spacer(modifier = Modifier.height(20.dp))
        Button(onClick = onBack) {
            Text("← Back")
        }
    }
}



