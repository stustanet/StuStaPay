# pylint: disable=attribute-defined-outside-init,unexpected-keyword-arg,missing-kwoa
import pytest
from sftkit.error import AccessDenied

from stustapay.core.schema.tax_rate import NewTaxRate
from stustapay.core.schema.tree import Node
from stustapay.core.service.tax_rate import TaxRateService

from .conftest import Cashier


async def test_basic_tax_rate_workflow(
    tax_rate_service: TaxRateService, event_node: Node, event_admin_token: str, cashier: Cashier
):
    tax_rates = await tax_rate_service.list_tax_rates(token=event_admin_token, node_id=event_node.id)
    start_num_tax_rates = len(tax_rates)

    tax_rate = await tax_rate_service.create_tax_rate(
        token=event_admin_token,
        node_id=event_node.id,
        tax_rate=NewTaxRate(name="krass", rate=0.5, description="Krasse UST"),
    )
    assert tax_rate.name == "krass"

    with pytest.raises(AccessDenied):
        await tax_rate_service.create_tax_rate(
            token=cashier.token,
            node_id=event_node.id,
            tax_rate=NewTaxRate(name="Krasse UST", rate=0.5, description="Krasse UST"),
        )

    updated_tax_rate = await tax_rate_service.update_tax_rate(
        token=event_admin_token,
        tax_rate_id=tax_rate.id,
        node_id=event_node.id,
        tax_rate=NewTaxRate(name="krass", rate=0.6, description="Noch Krassere UST"),
    )
    assert updated_tax_rate.rate == 0.6
    assert updated_tax_rate.description == "Noch Krassere UST"

    tax_rates = await tax_rate_service.list_tax_rates(token=event_admin_token, node_id=event_node.id)
    assert len(tax_rates) == start_num_tax_rates + 1
    assert updated_tax_rate in tax_rates

    with pytest.raises(AccessDenied):
        await tax_rate_service.delete_tax_rate(token=cashier.token, node_id=event_node.id, tax_rate_id=tax_rate.id)

    deleted = await tax_rate_service.delete_tax_rate(
        token=event_admin_token, node_id=event_node.id, tax_rate_id=tax_rate.id
    )
    assert deleted
