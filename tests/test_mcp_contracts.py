from peopleops_mcp.contracts import REQUIRED_TOOL_CONTRACTS


def test_required_tool_contracts_are_unique_and_complete() -> None:
    names = [contract.name for contract in REQUIRED_TOOL_CONTRACTS]

    assert len(names) == 8
    assert len(set(names)) == len(names)
    assert "search_policy_documents" in names
    assert "lookup_employee_profile" in names
    assert "create_mock_hr_ticket" in names


def test_mock_ticket_contract_requires_confirmation() -> None:
    ticket_contract = next(
        contract for contract in REQUIRED_TOOL_CONTRACTS if contract.name == "create_mock_hr_ticket"
    )

    assert ticket_contract.requires_confirmation is True
