from mcp.server import MCPServer

from peopleops_mcp.schemas import EmployeeProfileResult, PolicySearchResult
from peopleops_mcp.tools import lookup_employee_profile_data, search_policy_documents_data

PHASE4_TOOL_NAMES = frozenset({"lookup_employee_profile", "search_policy_documents"})

mcp_server = MCPServer(
    name="peopleops-assistant",
    title="PeopleOps Assistant MCP Server",
    description="Read-only tools over synthetic employee records and policy evidence.",
    version="0.1.0",
)


@mcp_server.tool(structured_output=True)
def lookup_employee_profile(employee_id: str) -> EmployeeProfileResult:
    """Return the minimal synthetic employee profile needed for PeopleOps guidance."""
    return lookup_employee_profile_data(employee_id)


@mcp_server.tool(structured_output=True)
def search_policy_documents(query: str) -> PolicySearchResult:
    """Find cited policy sections for the Phase 4 international remote-work workflow."""
    return search_policy_documents_data(query)
