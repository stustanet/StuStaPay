package de.stustapay.stustapay.ui.ticket

import android.app.Activity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import de.stustapay.api.models.NewTicketScan
import de.stustapay.api.models.PaymentMethod
import de.stustapay.api.models.PendingTicketSale
import de.stustapay.api.models.UserTagScan
import de.stustapay.libssp.model.NfcTag
import de.stustapay.libssp.net.Response
import de.stustapay.libssp.util.ResourcesProvider
import de.stustapay.libssp.util.mapState
import de.stustapay.stustapay.R
import de.stustapay.stustapay.ec.ECPayment
import de.stustapay.stustapay.repository.ECPaymentRepository
import de.stustapay.stustapay.repository.ECPaymentResult
import de.stustapay.stustapay.repository.InfallibleRepository
import de.stustapay.stustapay.repository.TerminalConfigRepository
import de.stustapay.stustapay.repository.TicketRepository
import de.stustapay.stustapay.ui.common.TerminalLoginState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import java.math.BigDecimal
import javax.inject.Inject


enum class TicketPage(val route: String) {
    Scan("scan"), Confirm("confirm"), Done("done"), Error("aborted"),
}

sealed interface TagScanStatus {
    object NoScan : TagScanStatus
    object Scan : TagScanStatus
    object Duplicate : TagScanStatus
}


@HiltViewModel
class TicketViewModel @Inject constructor(
    private val ticketRepository: TicketRepository,
    terminalConfigRepository: TerminalConfigRepository,
    private val ecPaymentRepository: ECPaymentRepository,
    private val resourcesProvider: ResourcesProvider,
    private val infallibleRepository: InfallibleRepository
) : ViewModel() {

    // navigation in views
    private val _navState = MutableStateFlow(TicketPage.Scan)
    val navState = _navState.asStateFlow()

    private val _status = MutableStateFlow("")
    val status = _status.asStateFlow()

    // tag scanning
    private val _tagScanStatus = MutableStateFlow<TagScanStatus>(TagScanStatus.Scan)
    val tagScanStatus = _tagScanStatus.asStateFlow()

    // ticket purchase selection
    private val _ticketDraft = MutableStateFlow(TicketDraft())
    val ticketDraft = _ticketDraft.asStateFlow()

    // when we finished a ticket sale
    private val _saleCompleted = MutableStateFlow<PendingTicketSale?>(null)
    val saleCompleted = _saleCompleted.asStateFlow()

    // configuration infos from backend
    val terminalLoginState = terminalConfigRepository.terminalConfigState.mapState(
        initialValue = TerminalLoginState(), scope = viewModelScope
    ) { terminal ->
        TerminalLoginState(terminal = terminal)
    }

    val infallibleBusy = infallibleRepository.busy.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5_000),
        initialValue = false,
    )

    fun navTo(page: TicketPage) {
        _navState.update { page }
    }

    /**
     * how much do we have to pay? we get this from the PendingTicketSale
     */
    fun getPrice(): UInt {
        val price = _ticketDraft.value.checkedSale?.totalPrice ?: 0.0
        return (price * 100).toUInt()
    }

    /**
     *  test if a tag scan was successful, i.e. we didn't scan it previously.
     * if this returns false, the scan dialog will remain open.
     */
    fun checkTagScan(tag: NfcTag): Boolean {
        return if (_ticketDraft.value.tagKnown(tag)) {
            _tagScanStatus.update {
                TagScanStatus.Duplicate
            }
            false
        } else {
            _tagScanStatus.update {
                TagScanStatus.Scan
            }
            true
        }
    }

    /**
     * when checkTagScan above returned true, we end up here after a successful tag scan.
     * this function is only called if the tag is not already known.
     */
    suspend fun tagScanned(tag: NfcTag) {
        val response =
            ticketRepository.checkTicketScan(NewTicketScan(customerTags = listOf(tag).mapNotNull {
                UserTagScan(
                    it.uid, it.pin ?: return@mapNotNull null
                )
            }))

        when (response) {
            is Response.OK -> {
                _ticketDraft.update { status ->
                    val scanned = response.data.scannedTickets
                    if (scanned.isEmpty()) {
                        _status.update { resourcesProvider.getString(R.string.ticket_unknown) }
                        return
                    }

                    val scanResult = scanned[0]
                    if (scanResult.customerTagUid != tag.uid) {
                        _status.update { "returned ticket id != ticket unknown" }
                        return
                    }

                    val newStatus = status.copy()
                    val ret = newStatus.addTicket(
                        ScannedTicket(
                            tag = tag, ticket = scanResult.ticket
                        )
                    )
                    if (!ret) {
                        _status.update { "failed to store new ticket" }
                    }
                    newStatus
                }
                _status.update { resourcesProvider.getString(R.string.ticket_valid) }
            }

            is Response.Error.Service -> {
                _status.update { response.msg() }
            }

            is Response.Error -> {
                _status.update { response.msg() }
            }
        }
    }

    /** when the delete-selections button is clicked */
    fun clearDraft() {
        _status.update { "cleared" }
        _tagScanStatus.update { TagScanStatus.Scan }
        _ticketDraft.update { TicketDraft() }
    }

    fun dismissSuccess() {
        clearTicketSale(success = true)
    }

    fun dismissError() {
        _navState.update { TicketPage.Scan }
    }

    /** once the sale was booked completely */
    private fun clearTicketSale(success: Boolean = false) {
        _ticketDraft.update { TicketDraft() }
        _navState.update { TicketPage.Scan }
        _saleCompleted.update { null }

        if (success) {
            _status.update { resourcesProvider.getString(R.string.ticket_order_cleared_success) }
        } else {
            _status.update { resourcesProvider.getString(R.string.ticket_order_cleared) }
        }
    }

    /** test if we can sell this */
    suspend fun checkSale() {
        val selection = _ticketDraft.value

        _status.update { resourcesProvider.getString(R.string.order_checking) }
        _saleCompleted.update { null }

        // check if the sale is nice and well
        val response = ticketRepository.checkTicketSale(
            selection.getNewTicketSale(null)
        )

        when (response) {
            is Response.OK -> {
                _ticketDraft.update { status ->
                    val newSale = status.copy()
                    newSale.updateWithPendingTicketSale(response.data)
                    newSale
                }
                _status.update { resourcesProvider.getString(R.string.ticket_order_validated) }
                _saleCompleted.update { response.data }
                _navState.update { TicketPage.Confirm }
            }

            is Response.Error.Service -> {
                _status.update { response.msg() }
                _navState.update { TicketPage.Error }
            }

            is Response.Error -> {
                _status.update { response.msg() }
            }
        }
    }

    /** let's start the payment process */
    suspend fun processSale(context: Activity, paymentMethod: PaymentMethod) {
        // checks
        if (_ticketDraft.value.scans.isEmpty()) {
            _status.update { "Not all tags were scanned!" }
            return
        }

        val checkedSale = _ticketDraft.value.checkedSale
        if (checkedSale == null) {
            _status.update { "no ticket sale check present" }
            return
        }


        // if we do cash payment, the confirmation was already presented by CashECPay
        if (paymentMethod == PaymentMethod.cash) {
            bookSale(paymentMethod = PaymentMethod.cash)
            return
        }

        // otherwise, perform ec payment
        val payment = ECPayment(
            id = "${checkedSale.uuid}_${_ticketDraft.value.ecRetry}",
            amount = BigDecimal(checkedSale.totalPrice),
            tag = _ticketDraft.value.scans[0].tag,
        )

        when (val ecResult = ecPaymentRepository.pay(context = context, ecPayment = payment)) {
            is ECPaymentResult.Failure -> {
                _ticketDraft.update { status ->
                    val newSale = status.copy()
                    newSale.ecFailure()
                    newSale
                }
                _status.update { ecResult.msg }
            }

            is ECPaymentResult.Success -> {
                _status.update { ecResult.result.msg }
                bookSale(PaymentMethod.sumup)
            }
        }
    }

    private suspend fun bookSale(paymentMethod: PaymentMethod) {
        infallibleRepository.bookTicketSale(_ticketDraft.value.getNewTicketSale(paymentMethod))

        clearDraft()
        _status.update { resourcesProvider.getString(R.string.ticket_order_booked) }
        _navState.update { TicketPage.Done }
    }
}