package de.stustanet.stustapay.ui.chipscan

import androidx.compose.foundation.layout.*
import androidx.compose.material.Card
import androidx.compose.material.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import de.stustanet.stustapay.model.UserTag

@Composable
fun NfcScanDialog(
    state: NfcScanDialogState,
    viewModel: NfcScanDialogViewModel = hiltViewModel(),
    onScan: suspend (UserTag) -> Unit = {},
    content: @Composable () -> Unit = {
        // utf8 "satellite antenna"
        Text("Scan a Chip \uD83D\uDCE1", textAlign = TextAlign.Center, fontSize = 40.sp)
    },
) {
    state.setViewModel(viewModel)
    val scanResult by viewModel.scanState.collectAsStateWithLifecycle()

    LaunchedEffect(scanResult) {
        val tag = scanResult.scanTag
        if (tag != null) {
            state.close()
            onScan(tag)
        }
    }

    if (state.isOpen()) {
        Dialog(
            onDismissRequest = {
                state.close()
            }
        ) {
            Box(Modifier.size(350.dp, 350.dp)) {
                Card(modifier = Modifier.padding(20.dp)) {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(
                            modifier = Modifier
                                .padding(start = 5.dp)
                                .fillMaxWidth()
                        ) {

                            val actionMsg = scanResult.action
                            if (actionMsg == null) {
                                content()
                            } else {
                                Text(
                                    actionMsg,
                                    textAlign = TextAlign.Center,
                                    fontSize = 40.sp,
                                )
                            }
                            Text(
                                scanResult.status,
                                textAlign = TextAlign.Left,
                                fontSize = 20.sp,
                            )
                        }
                    }
                }
            }
        }
    }
}
