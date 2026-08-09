import asyncio

from mcp import Client

from peopleops_mcp.schemas import EmployeeProfileResult, PolicySearchResult
from peopleops_mcp.server import PHASE4_TOOL_NAMES, mcp_server


def test_official_mcp_client_discovers_and_invokes_phase4_tools() -> None:
    async def exercise_tools() -> tuple[set[str], EmployeeProfileResult, PolicySearchResult]:
        async with Client(mcp_server) as client:
            discovered = await client.list_tools()
            profile_call = await client.call_tool(
                "lookup_employee_profile",
                {"employee_id": "E-1007"},
            )
            policy_call = await client.call_tool(
                "search_policy_documents",
                {"query": "Can I work remotely from Germany for six weeks?"},
            )
        assert profile_call.structured_content is not None
        assert policy_call.structured_content is not None
        return (
            {tool.name for tool in discovered.tools},
            EmployeeProfileResult.model_validate(profile_call.structured_content),
            PolicySearchResult.model_validate(policy_call.structured_content),
        )

    tool_names, profile, policy = asyncio.run(exercise_tools())

    assert tool_names == PHASE4_TOOL_NAMES
    assert profile.found is True
    assert profile.profile is not None
    assert profile.profile.employee_id == "E-1007"
    assert profile.profile.home_office.province_or_state == "British Columbia"
    assert policy.sufficient_evidence is True
    assert {match.section_id for match in policy.matches} == {
        "INT-4",
        "INT-5",
        "INT-13",
        "RWK-5",
    }
    assert all(
        match.source_path.startswith("policy_corpus/runtime_corpus/")
        for match in policy.matches
    )


def test_phase4_tools_return_safe_empty_results_for_unknown_inputs() -> None:
    async def exercise_tools() -> tuple[EmployeeProfileResult, PolicySearchResult]:
        async with Client(mcp_server) as client:
            profile_call = await client.call_tool(
                "lookup_employee_profile",
                {"employee_id": "E-9999"},
            )
            policy_call = await client.call_tool(
                "search_policy_documents",
                {"query": "What is the office holiday schedule?"},
            )
        assert profile_call.structured_content is not None
        assert policy_call.structured_content is not None
        return (
            EmployeeProfileResult.model_validate(profile_call.structured_content),
            PolicySearchResult.model_validate(policy_call.structured_content),
        )

    profile, policy = asyncio.run(exercise_tools())

    assert profile.found is False
    assert profile.profile is None
    assert policy.sufficient_evidence is False
    assert policy.matches == []
