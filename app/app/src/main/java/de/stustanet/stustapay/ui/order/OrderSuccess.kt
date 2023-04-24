package de.stustanet.stustapay.ui.order

import androidx.compose.foundation.layout.*
import androidx.compose.material.Button
import androidx.compose.material.Scaffold
import androidx.compose.material.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle


@Composable
fun OrderSuccess(viewModel: OrderViewModel, onConfirm: () -> Unit) {
    val saleConfig by viewModel.saleConfig.collectAsStateWithLifecycle()
    val saleDraft by viewModel.saleDraft.collectAsStateWithLifecycle()

    val haptic = LocalHapticFeedback.current

    Scaffold(
        content = { padding ->
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(bottom = padding.calculateBottomPadding()),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    OrderCost(saleDraft)

                    for (product in saleDraft.buttonSelection) {
                        val name = saleConfig.buttons[product.key]!!.caption
                        val amount = product.value
                        Text(text = "$amount $name", fontSize = 24.sp)
                    }
                }
            }
        },
        bottomBar = {
            Button(
                onClick = {
                    haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                    onConfirm()
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(70.dp)
                    .padding(10.dp)
            ) {
                Text(text = "Next")
            }
        }
    )
}
