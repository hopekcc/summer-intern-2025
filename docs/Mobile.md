# Mobile App

A Jetpack Compose Android app.  
This app uses a modular structure with reusable components, clean navigation, and ViewModel-based state management.

---

## Project Structure

├── components/ # Reusable composables and UI elements (bars, etc.)

├── data/ # Data models, repositories, etc

├── navigation/ # Navigation setup using NavHost and routes

├── screens/ # Individual app screens (composables for each screen)

├── ui/ # App theme, colors, typography, and general styling

├── viewmodels/ # ViewModels for managing UI state

└── MainActivity.kt # App entry point, sets up navigation and the main UI

## API Usage

This app uses Retrofit to interact with a backend API for managing songs and playlists. All requests are automatically authenticated with an Authorization token via AuthInterceptor.

### Playlist API
*The playlist API is managed by PlaylistRepository and PlaylistApiService.*

```suspend fun createPlaylist(name: String): Playlist?``` 
Creates a new playlist.

```suspend fun addSongsToPlaylist(playlistId: String, songId: String): Boolean``` 
Adds a song to a specific playlist.

```suspend fun listAllPlaylists(): List<Playlist>``` 
Fetches all playlists for the user.

```suspend fun deletePlaylist(id: String): Boolean``` 
Deletes a playlist by its ID.

```suspend fun removeSong(playlistId: String, songId: Int): Boolean``` 
Removes a song from a playlist.

### Song API
*The song API is managed by SongRepository and ApiService.*

```suspend fun searchSongs(query: String): List<Song>``` 
Searches for songs matching a query.

```suspend fun getAllSongs(): List<Song>``` 
Fetches all available songs.

```suspend fun getSongDetails(songId: Int): SongDetail?``` 
Retrieves detailed information for a song.

```suspend fun getSongPdf(songId: Int): File?``` 
Downloads a song's PDF to the app cache.

```suspend fun getSongPageImage(songId: Int, pageNumber: Int): ByteArray?```
Retrieves a single song page as an image.


## AuthInterceptor
*All API requests automatically include a Bearer token for authentication.*

```class AuthInterceptor(private val tokenProvider: () -> String?) : Interceptor```

Repository Setup
Both PlaylistRepository and SongRepository are initialized with:
- Retrofit for API calls.
- OkHttpClient with HttpLoggingInterceptor (for logging) and AuthInterceptor (for authorization).
- GsonConverterFactory for JSON parsing.

*All repository functions are suspend functions, designed to be called from a coroutine. They handle errors gracefully by returning null, false, or empty lists.*


## Usage Notes
- API calls return data in models like Playlist, Song, and SongDetail.
- Debugging is supported via console logs in PlaylistRepository when adding songs to a playlist.
- Network requests are resilient to errors and exceptions.

## Getting Started

### Prerequisites

- Kotlin 1.8+  
- Jetpack Compose enabled  

### How to Run

1. Clone the repository:
   ```bash
   git clone https://github.com/hopekcc/summer-intern-2025.git
2. Open the project in Android Studio.
3. Build and run the app on an emulator or physical device.
