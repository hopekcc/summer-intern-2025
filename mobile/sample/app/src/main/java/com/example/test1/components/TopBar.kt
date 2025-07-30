// NOT USED
package com.example.test1.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.test1.R

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TopAppBar(modifier: Modifier = Modifier) {
    val musicNote = painterResource(R.drawable.home_logo)
    CenterAlignedTopAppBar(
        title = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center
            ) {
                Image(
                    painter = musicNote,
                    contentDescription = null,
                    modifier = Modifier.size(50.dp)
                )
                Text(
                    text = "Tech meets Music",
                    fontSize = 35.sp,
                    modifier = modifier.padding(start = 10.dp)
                )
            }
        },
        modifier = modifier
    )
}