package de.stustanet.stustapay.ui.common

import androidx.compose.foundation.layout.*
import androidx.compose.material.Button
import androidx.compose.material.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel

@Composable
fun NumberKeyboard(
    onDigitEntered: (UInt) -> Unit,
    onClear: () -> Unit,
) {
    val haptic = LocalHapticFeedback.current

    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        for (i in 0u..2u) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                for (j in 1u..3u) {
                    val nr = i * 3u + j
                    Button(
                        modifier = Modifier
                            .fillMaxWidth(0.33f)
                            .height(90.dp)
                            .padding(5.dp),
                        onClick = {
                            haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                            onDigitEntered(nr)
                        }
                    ) {
                        Text(nr.toString(), fontSize = 24.sp)
                    }
                }
            }
        }
        Row (
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            Button(
                modifier = Modifier
                    .fillMaxWidth(0.33f)
                    .height(90.dp)
                    .padding(5.dp),
                onClick = {
                    haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                    onDigitEntered(0u)
                    onDigitEntered(0u)
                }
            ) {
                Text("00", fontSize = 24.sp)
            }
            Button(
                modifier = Modifier
                    .fillMaxWidth(0.5f)
                    .height(90.dp)
                    .padding(5.dp),
                onClick = {
                    haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                    onDigitEntered(0u)
                }
            ) {
                Text("0", fontSize = 24.sp)
            }
            Button(
                modifier = Modifier
                    .fillMaxWidth(1f)
                    .height(90.dp)
                    .padding(5.dp),
                onClick = {
                    haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                    onClear()
                }
            ) {
                Text("❌", fontSize = 24.sp)
            }
        }
    }
}