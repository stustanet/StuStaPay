package de.stustapay.stustapay.ui.ticket

import android.app.Activity
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.Divider
import androidx.compose.material.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import de.stustapay.api.models.PaymentMethod
import de.stustapay.stustapay.R
import de.stustapay.stustapay.ui.common.StatusText
import de.stustapay.stustapay.ui.common.pay.CashECCallback
import de.stustapay.stustapay.ui.common.pay.CashECPay
import de.stustapay.stustapay.ui.common.pay.NoCashRegisterWarning
import de.stustapay.stustapay.ui.common.pay.ProductConfirmItem
import de.stustapay.stustapay.ui.common.pay.ProductConfirmLineItem
import de.stustapay.stustapay.ui.nav.NavScaffold
import kotlinx.coroutines.launch

@Composable
fun TicketConfirm(
    goBack: () -> Unit,
    viewModel: TicketViewModel
) {
    val status by viewModel.status.collectAsStateWithLifecycle()
    val config by viewModel.terminalLoginState.collectAsStateWithLifecycle()
    val ticketDraft by viewModel.ticketDraft.collectAsStateWithLifecycle()
    val infallibleBusy by viewModel.infallibleBusy.collectAsStateWithLifecycle()

    val scope = rememberCoroutineScope()
    val context = LocalContext.current as Activity

    val checkedSale = ticketDraft.checkedSale
    if (checkedSale == null) {
        Column {
            Text(status)
            Text("no sale check present!")
        }
        return
    }

    NavScaffold(
        title = { Text(config.title().title) },
        navigateBack = goBack
    ) { pv ->
        Column {
            if (!config.canHandleCash()) {
                NoCashRegisterWarning(modifier = Modifier.padding(10.dp))
            }
            CashECPay(
                modifier = Modifier.padding(pv),
                status = { StatusText(status) },
                onPaymentRequested = CashECCallback.NoTag(
                    onEC = {
                        scope.launch {
                            viewModel.processSale(
                                context = context,
                                paymentMethod = PaymentMethod.sumup
                            )
                        }
                    },
                    onCash = {
                        scope.launch {
                            viewModel.processSale(
                                context = context,
                                paymentMethod = PaymentMethod.cash
                            )
                        }
                    },
                ),
                ready = config.isTerminalReady() && !infallibleBusy,
                getAmount = { viewModel.getPrice() },
            ) { paddingValues ->
                // TODO: pending ticket sale display

                LazyColumn(
                    modifier = Modifier
                        .padding(bottom = paddingValues.calculateBottomPadding())
                        .padding(horizontal = 10.dp)
                        .fillMaxSize()
                ) {

                    item {
                        ProductConfirmItem(
                            name = stringResource(R.string.price),
                            price = checkedSale.totalPrice,
                            bigStyle = true,
                        )
                        Divider(thickness = 2.dp)
                    }

                    for (lineItem in checkedSale.lineItems) {
                        item {
                            ProductConfirmLineItem(lineItem = lineItem)
                        }
                    }
                }
            }
        }
    }
}