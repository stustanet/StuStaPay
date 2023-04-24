package de.stustanet.stustapay.ui.sale

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
fun SaleView(viewModel: SaleViewModel = hiltViewModel()) {
    val scope = rememberCoroutineScope()
    val nav = rememberNavController()
    val scanState = rememberNfcScanDialogState()

    val navTarget by viewModel.navState.collectAsStateWithLifecycle()
    val enableScan by viewModel.enableScan.collectAsStateWithLifecycle()

    LaunchedEffect(navTarget) {
        if (nav.currentDestination?.route != navTarget.route) {
            nav.navigate(navTarget.route)
        }
    }

    // fetch the terminal configuration
    LaunchedEffect(Unit) {
        viewModel.fetchConfig()
    }

    LaunchedEffect(enableScan) {
        if (enableScan) {
            scanState.open()
        }
        else {
            scanState.close()
        }
    }

    NfcScanDialog(
        scanState,
        onScan = { uid ->
            scope.launch {
                viewModel.tagScanned(uid)
            }
        },
        onDismiss = {
            viewModel.tagScanDismissed()
        }
    )

    NavHost(navController = nav, startDestination = SalePage.ProductSelect.route) {
        composable(SalePage.ProductSelect.route) {

            SaleSelection(
                viewModel,
                onAbort = {
                    scope.launch {
                        viewModel.clearSale()
                    }
                },
                onSubmit = {
                    scope.launch {
                        viewModel.checkSale()
                    }
                },
            )
        }

        // what would be booked, from there one can get back to edit-mode
        composable(SalePage.Confirm.route) {
            SaleConfirm(
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
        composable(SalePage.Success.route) {
            SaleSuccess(
                viewModel,
                onConfirm = {
                    scope.launch {
                        viewModel.clearSale()
                    }
                }
            )
        }

        // something failed when validating or booking the order
        composable(SalePage.Error.route) {
            SaleError(
                onDismiss = {
                    scope.launch {
                        viewModel.errorDismissed()
                    }
                },
                viewModel = viewModel,
            )
        }
    }
}
