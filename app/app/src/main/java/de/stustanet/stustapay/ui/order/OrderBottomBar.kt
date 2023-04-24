package de.stustanet.stustapay.ui.order

import androidx.compose.foundation.layout.*
import androidx.compose.material.Button
import androidx.compose.material.ButtonDefaults
import androidx.compose.material.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun OrderBottomBar(
    status: @Composable () -> Unit,
    saleConfig: SaleConfig,
    onAbort: () -> Unit,
    onSubmit: () -> Unit,
) {
    val haptic = LocalHapticFeedback.current

    Column {
        Row(horizontalArrangement = Arrangement.SpaceEvenly) {
            status()
        }
        Row(horizontalArrangement = Arrangement.SpaceEvenly) {
            Button(
                enabled = saleConfig.ready,
                colors = ButtonDefaults.buttonColors(backgroundColor = Color.Red),
                onClick = {
                    haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                    onAbort()
                },
                modifier = Modifier
                    .fillMaxWidth(0.5f)
                    .height(70.dp)
                    .padding(10.dp)
            ) {
                // WASTEBASKET symbol
                Text(text = "\uD83D\uDDD1", fontSize = 24.sp)
            }
            Button(
                enabled = saleConfig.ready,
                onClick = {
                    haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                    onSubmit()
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(70.dp)
                    .padding(10.dp)
            ) {
                Text(text = "✓")
            }
        }
    }
}