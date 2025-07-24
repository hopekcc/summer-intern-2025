package com.example.test1.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.test1.R


@Composable
fun HomeScreen(
    titleText: String,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(start = 16.dp, top = 50.dp, end = 16.dp, bottom = 0.dp)
    ) {
        Row(modifier = modifier.wrapContentWidth(), verticalAlignment = Alignment.CenterVertically) {
            Image(
                painter = painterResource(id = R.drawable.home_logo),
                contentDescription = "music icon/home logo",
                modifier = Modifier.size(48.dp)
            )
            Text(text = "Tech Meets Music", fontSize = 40.sp)
        }
        Spacer(modifier = Modifier.height(20.dp))
        Text(text = titleText, fontSize = 24.sp, modifier = Modifier.align(Alignment.Start))
        Spacer(modifier = Modifier.height(80.dp))
        Text(text = "Recently played", fontSize = 20.sp, modifier = Modifier.align(Alignment.CenterHorizontally))
    }
}

