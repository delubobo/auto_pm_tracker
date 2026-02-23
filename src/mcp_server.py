from mcp.server.fastmcp import FastMCP
import json
from src.cpm import calculate_critical_path
from src.services import calculate_project_evm

# Initialize the MCP Server
mcp = FastMCP("PM_Tracker_Server")

@mcp.tool()
def get_critical_path() -> str:
    """
    Fetches the project schedule and identifies the critical path.
    Use this tool when asked about schedule bottlenecks, task floats, or project timelines.
    """
    results = calculate_critical_path()
    if not results:
        return "No schedule data found in the database."
    
    # Return as a JSON string so Claude can easily read and analyze it
    return json.dumps(results, indent=2)

@mcp.tool()
def get_financial_health() -> str:
    """
    Calculates the Earned Value Management (EVM) metrics for the project.
    Use this tool when asked about project budget, CPI, SPI, or financial health.
    """
    metrics = calculate_project_evm()
    if not metrics:
        return "No financial data available to calculate EVM."
    
    return json.dumps(metrics, indent=2)

if __name__ == "__main__":
    # Start the FastMCP server
    mcp.run()