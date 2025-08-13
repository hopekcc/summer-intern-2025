package com.example.chordproapp.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val DarkColorScheme = darkColorScheme(
    primary = AccentBlue,
    secondary = LightGray,
    tertiary = AccentBlue,
    background = DarkBackground,
    surface = DarkSurface,
    onPrimary = Color.White,
    onSecondary = Color.White,
    onTertiary = Color.White,
    onBackground = Color.White,
    onSurface = Color.White,
)

private val LightColorScheme = lightColorScheme(
    primary = DarkBlue,              // Primary buttons and accents
    secondary = GhostBlue,           // Secondary backgrounds and elements
    tertiary = AccentBlue,           // Tertiary accents
    background = White,              // Main background - pure white
    surface = White,                 // Card surfaces - pure white
    surfaceVariant = GhostBlue,      // Subtle surface variations
    onPrimary = Color.White,         // Text on primary
    onSecondary = DarkBlue,          // Text on secondary
    onTertiary = Color.White,        // Text on tertiary
    onBackground = DarkBlue,         // Text on background
    onSurface = DarkBlue,            // Text on surfaces
    outline = MediumGray,            // Borders and dividers
    outlineVariant = LightestGray,   // Subtle borders
    error = ErrorRed,                // Error color
    onError = Color.White,           // Text on error
    surfaceTint = AccentBlue         // Surface tinting
)

@Composable
fun ChordproappTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = false, // Disabled to use custom colors
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = Color.White.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = true
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}