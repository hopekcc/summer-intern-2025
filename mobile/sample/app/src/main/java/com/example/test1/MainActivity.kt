package com.example.test1


import android.annotation.SuppressLint
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.net.toUri

import kotlinx.coroutines.*
import org.jsoup.Jsoup
import java.io.IOException

class MainActivity : ComponentActivity() {
    private lateinit var openFileLauncher: ActivityResultLauncher<Intent>
    private lateinit var song: TextView
    private lateinit var btnOpenFile: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContentView(R.layout.layout)
        song = findViewById(R.id.song) // ✅ Must happen before using it
        song.text = "Hello, world!"

        btnOpenFile = findViewById((R.id.btnOpenFile))
        btnOpenFile.setOnClickListener {
            CoroutineScope(Dispatchers.IO).launch {
                val result =
                    fetchTextFromWeb("http://getsome.org/guitar/olga/chordpro/b/Beatles/HeyJude.chopro") // Simulate background work
                withContext(Dispatchers.Main) {
                    song.text = result // ✅ Safe UI update on main thread
                }
            }
            enableEdgeToEdge()
        }
    }
}

fun fetchTextFromWeb(url: String) : String {
    return try {
        val doc = Jsoup.connect(url).get()
        val text = doc.body().text()
        text
    } catch (e: IOException) {
        "Error: ${e.message}"
    }
}
