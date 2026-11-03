package com.neurotracee.pdfmask.ui

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import com.neurotracee.pdfmask.AppPrefs

val BrandBlue = Color(0xFF2563EB)
val BrandBlueDark = Color(0xFF1D4ED8)
val DangerRed = Color(0xFFE5484D)
val WarnAmber = Color(0xFFB45309)

private val Light = lightColorScheme(
    primary = BrandBlue,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFE3ECFF),
    onPrimaryContainer = Color(0xFF0B2C6B),
    secondary = Color(0xFF4B5563),
    background = Color(0xFFF5F6F8),
    onBackground = Color(0xFF141922),
    surface = Color.White,
    onSurface = Color(0xFF141922),
    surfaceVariant = Color(0xFFEFF2F6),
    onSurfaceVariant = Color(0xFF5B6472),
    outline = Color(0xFFD5DAE2),
    error = DangerRed
)

private val Dark = darkColorScheme(
    primary = Color(0xFF7BA3FF),
    onPrimary = Color(0xFF06122B),
    primaryContainer = Color(0xFF1B335F),
    onPrimaryContainer = Color(0xFFD7E4FF),
    secondary = Color(0xFF9AA5B5),
    background = Color(0xFF11151C),
    onBackground = Color(0xFFE7EBF2),
    surface = Color(0xFF181E27),
    onSurface = Color(0xFFE7EBF2),
    surfaceVariant = Color(0xFF232B36),
    onSurfaceVariant = Color(0xFFA8B2C1),
    outline = Color(0xFF333D4B),
    error = Color(0xFFFF6B6E)
)

/** 按偏好解析当前是否深色 */
@Composable
fun resolveDark(): Boolean = when (AppPrefs.themeMode) {
    "dark" -> true
    "light" -> false
    else -> isSystemInDarkTheme()
}

@Composable
fun PdfMaskTheme(dark: Boolean = resolveDark(), content: @Composable () -> Unit) {
    val scheme = if (dark) Dark else Light
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = Color.Transparent.toArgb()
            window.navigationBarColor = Color.Transparent.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !dark
            WindowCompat.getInsetsController(window, view).isAppearanceLightNavigationBars = !dark
        }
    }
    MaterialTheme(colorScheme = scheme, content = content)
}
