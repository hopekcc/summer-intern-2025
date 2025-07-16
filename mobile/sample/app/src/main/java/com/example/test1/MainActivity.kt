package com.example.test1

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.*
import org.jsoup.Jsoup
import java.io.IOException

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            // State to hold the song text
            var titleText by remember { mutableStateOf("Tech meets Music") }

            SongScreen(
                titleText = titleText,
                onButtonClick = {
                    CoroutineScope(Dispatchers.IO).launch {
                        val result = fetchTextFromWeb("http://getsome.org/guitar/olga/chordpro/b/Beatles/HeyJude.chopro")
                        withContext(Dispatchers.Main) {
                            titleText = result
                        }
                    }
                }
            )
        }
    }
}

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
    val musicNote = painterResource(R.drawable.musical_note_flat_icon_png)

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(top = 50.dp, bottom = 50.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = modifier.padding(start = 40.dp)
        ) {
            Image(
                painter = musicNote,
                contentDescription = null,
                modifier = Modifier
                    .size(80.dp, 80.dp)
            )
            Text(
                text = titleText,
                fontSize = 40.sp,
                modifier = modifier.padding(start = 15.dp),
            )
        }
        Spacer(modifier = Modifier.height(20.dp))
        Button(onClick = onButtonClick) {
            Text("Upload Song File",
            fontSize = 20.sp)
        }
    }

    val profileIcon = painterResource(R.drawable.user_icon_on_transparent_background_free_png)
    val songLibraryIcon = painterResource(R.drawable.songlibrary)

    Row(
        modifier = Modifier.padding(top = 800.dp),
    ) {
        var thisStep by remember {mutableStateOf(1)}
        when (thisStep) {
            1 -> {
                Image(
                    painter = profileIcon,
                    contentDescription = null,
                    modifier = Modifier
                        .size(70.dp,70.dp)
                        .clickable {
                            thisStep = 2
                        }
                )
            }

            2 -> {
                Text(text = "Your Profile")
            }
        }


        Spacer(modifier = Modifier.width(20.dp))


        var currentStep by remember {mutableStateOf(1)}
        when (currentStep) {
            1 -> {
                Image(
                    painter = songLibraryIcon,
                    contentDescription = null,
                    modifier = Modifier
                        .size(70.dp, 70.dp)
                        .clickable {
                            currentStep = 2
                        }
                )
            }

            2 -> {
                Text(text = "Saved Songs")
            }
        }
    }
}


@Preview(showBackground = true)
@Composable
fun SongScreenPreview() {
    Box(modifier = Modifier.fillMaxSize()) {
        SongScreen(
            titleText = "Tech meets Music",
            onButtonClick = {}
        )
    }
}
