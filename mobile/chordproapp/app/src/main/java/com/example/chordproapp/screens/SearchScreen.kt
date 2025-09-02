package com.example.chordproapp.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.LibraryMusic
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.example.chordproapp.data.model.Playlist
import com.example.chordproapp.data.repository.PlaylistRepository
import com.example.chordproapp.viewmodels.PlaylistViewModel
import com.example.chordproapp.data.repository.SongRepository
import com.example.chordproapp.viewmodels.SearchViewModel
import kotlinx.coroutines.launch


@Composable
fun SearchScreen(
    navController: NavHostController,
    idTokenProvider: () -> String?,
    searchViewModel: SearchViewModel = viewModel { SearchViewModel(idTokenProvider) }
) {
    // Repository
    val playlistRepository = remember { PlaylistRepository(idTokenProvider) }

    // PlaylistViewModel with inline factory
    val playlistViewModel: PlaylistViewModel = viewModel(
        key = "playlistViewModel",
        factory = object : androidx.lifecycle.ViewModelProvider.Factory {
            override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
                return PlaylistViewModel(playlistRepository) as T
            }
        }
    )

    // Collect playlists
    val playlists by playlistViewModel.playlists.collectAsState()
    LaunchedEffect(Unit) { playlistViewModel.loadAllPlaylists() }

    // Search state
    viewModel: SearchViewModel = run {
        val context = LocalContext.current
        viewModel(
            factory = object : ViewModelProvider.Factory {
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    @Suppress("UNCHECKED_CAST")
                    return SearchViewModel(
                        SongRepository(idTokenProvider, context)
                    ) as T
                }
            }
        )
    }
) {
    var query by remember { mutableStateOf("") }
    val searchResults by searchViewModel.searchResults.collectAsState()
    val isLoading by searchViewModel.isLoading.collectAsState()
    val error by searchViewModel.error.collectAsState(initial = null)
    LaunchedEffect(query) { searchViewModel.searchSongs(query) }

    // Snackbar
    val snackbarHostState = remember { SnackbarHostState() }
    val coroutineScope = rememberCoroutineScope()

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(hostState = snackbarHostState) }
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(24.dp)
        ) {
            // Header
            item {
                Column(modifier = Modifier.padding(bottom = 32.dp)) {
                    Text(
                        "Search",
                        style = MaterialTheme.typography.headlineLarge,
                        color = MaterialTheme.colorScheme.onBackground,
                        modifier = Modifier.padding(bottom = 8.dp)
                    )
                    Text(
                        "Find your favorite music sheets and discover new ones",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.6f)
                    )
                }
            }

            // Search bar
            item {
                // Search Bar
                OutlinedTextField(
                    value = query,
                    onValueChange = { query = it },
                    leadingIcon = {
                        Icon(
                            imageVector = Icons.Default.Search,
                            contentDescription = "Search Icon",
                            tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                        )
                    },
                    placeholder = {
                        Text(
                            "Search music sheets",
                            style = MaterialTheme.typography.bodyLarge
                        )
                    },
                    textStyle = MaterialTheme.typography.bodyLarge,
                    singleLine = true,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 32.dp),
                    shape = RoundedCornerShape(20.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedContainerColor = MaterialTheme.colorScheme.secondary,
                        unfocusedContainerColor = MaterialTheme.colorScheme.secondary,
                        focusedBorderColor = MaterialTheme.colorScheme.primary,
                        unfocusedBorderColor = MaterialTheme.colorScheme.outline
                    )
                )
            }

            // Error message
            error?.let { errorMessage ->
                item {
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 16.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)
                    ) {
                        Text(
                            text = errorMessage,
                            modifier = Modifier.padding(16.dp),
                            color = MaterialTheme.colorScheme.onErrorContainer,
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                }
            }

            // Loading
            if (isLoading) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(32.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                    }
                }
            }

            // Search results
            if (searchResults.isNotEmpty()) {
                item {
                    Text(
                        if (query.isEmpty()) "All Songs" else "Search Results",
                        style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.onBackground,
                        modifier = Modifier.padding(bottom = 16.dp)
                    )
                }

                items(searchResults) { song ->
                    var expanded by remember { mutableStateOf(false) }
                    var selectedPlaylist by remember { mutableStateOf<Playlist?>(null) }

                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 12.dp),
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
                        border = CardDefaults.outlinedCardBorder()
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(20.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(song.title, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurface)
                                Text("Artist", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f), modifier = Modifier.padding(top = 4.dp))
                            }

                            Button(
                                onClick = {
                                    navController.navigate("viewer/${song.id}/${song.pageCount}")
                                },
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = MaterialTheme.colorScheme.secondary,
                                    contentColor = MaterialTheme.colorScheme.primary
                                ),
                                shape = RoundedCornerShape(12.dp),
                                elevation = ButtonDefaults.buttonElevation(defaultElevation = 2.dp)
                            ) {
                                Text(
                                    "View Sample Sheet",
                                    style = MaterialTheme.typography.labelMedium
                                )

                            Row {
                                // View button
                                Button(
                                    onClick = { navController.navigate("viewer/${song.id}") },
                                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary, contentColor = MaterialTheme.colorScheme.primary),
                                    shape = RoundedCornerShape(12.dp),
                                    elevation = ButtonDefaults.buttonElevation(defaultElevation = 2.dp)
                                ) {
                                    Text("View", style = MaterialTheme.typography.labelMedium)
                                }

                                Spacer(modifier = Modifier.width(8.dp))

                                // Add to playlist
                                Box {
                                    Button(
                                        onClick = { expanded = true },
                                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary, contentColor = MaterialTheme.colorScheme.onPrimary),
                                        shape = RoundedCornerShape(12.dp),
                                        elevation = ButtonDefaults.buttonElevation(defaultElevation = 2.dp)
                                    ) {
                                        Text(selectedPlaylist?.name ?: "Add to")
                                        Icon(Icons.Default.LibraryMusic, contentDescription = null, modifier = Modifier.size(25.dp).padding(start = 8.dp))
                                    }

                                    DropdownMenu(
                                        expanded = expanded,
                                        onDismissRequest = { expanded = false }
                                    ) {
                                        playlists.forEach { playlist ->
                                            DropdownMenuItem(
                                                text = { Text(playlist.name) },
                                                onClick = {
                                                    selectedPlaylist = playlist
                                                    expanded = false

                                                    // Call ViewModel with callback for Snackbar
                                                    playlistViewModel.addSongToPlaylist(playlist.id, song.id) { success ->
                                                        coroutineScope.launch {
                                                            val message = if (success) {
                                                                "Added to ${playlist.name}"
                                                            } else {
                                                                "Failed to add to ${playlist.name}"
                                                            }
                                                            snackbarHostState.showSnackbar(message)
                                                        }
                                                    }
                                                }
                                            )
                                        }
                                    }
                                }


                        }
                    }
                }
            } else if (!isLoading && query.isNotEmpty()) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(32.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            "No songs found for \"$query\"",
                            style = MaterialTheme.typography.bodyLarge,
                            color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.6f)
                        )
                    }
                }
            }
        }
    }
}


