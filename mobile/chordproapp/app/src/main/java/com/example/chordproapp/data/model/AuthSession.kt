package com.example.chordproapp.data.model

data class AuthSession(
    val idToken: String,
    val uid: String,
    val displayText: String // what you show in “Hey …”
)
