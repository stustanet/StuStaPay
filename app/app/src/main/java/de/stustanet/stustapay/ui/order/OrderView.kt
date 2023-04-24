package de.stustanet.stustapay.ui.order

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.tooling.preview.Preview
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import de.stustanet.stustapay.ui.chipscan.NfcScanDialog
import de.stustanet.stustapay.ui.chipscan.rememberNfcScanDialogState
import kotlinx.coroutines.launch


/**
 * Displays available purchase items and guides through the whole order.
 */
@Preview
@Composable
fun OrderView(viewModel: OrderViewModel = hiltViewModel()) {
    val scope = rememberCoroutineScope()
    val nav = rememberNavController()

    val navTarget by viewModel.navState.collectAsStateWithLifecycle()

    LaunchedEffect(navTarget) {
        if (nav.currentDestination?.route != navTarget.route) {
            nav.navigate(navTarget.route)
        }
    }

    // fetch the terminal configuration
    LaunchedEffect(Unit) {
        viewModel.fetchConfig()
    }

    NavHost(navController = nav, startDestination = SalePage.ProductSelect.route) {
        composable(SalePage.ProductSelect.route) {
            val scanState = rememberNfcScanDialogState()

            OrderSelection(
                viewModel,
                onAbort = {
                    scope.launch {
                        viewModel.clearOrder()
                    }
                },
                onSubmit = {
                    scope.launch {
                        // TODO: no new scan in refine-state - call viewModel.checkSale() directly
                        scanState.open()
                    }
                },
            )

            NfcScanDialog(
                scanState,
                onScan = { uid ->
                    scope.launch {
                        viewModel.checkSale(uid)
                    }
                },
            )
        }

        // what would be booked, from there one can get back to edit-mode
        composable(SalePage.Confirm.route) {
            OrderConfirmation(
                viewModel,
                onAbort = {
                    scope.launch {
                        viewModel.editOrder()
                    }
                },
                onSubmit = {
                    scope.launch {
                        viewModel.bookSale()
                    }
                },
            )
        }

        // the order was booked successfully.
        composable(SalePage.Done.route) {
            OrderSuccess(
                viewModel,
                onConfirm = {
                    scope.launch {
                        viewModel.clearOrder()
                    }
                }
            )
        }

        // order was aborted
        composable(SalePage.Aborted.route) {
            OrderFailure(onDismiss = {
                scope.launch {
                    viewModel.clearOrder()
                }
            })
        }
    }
}
