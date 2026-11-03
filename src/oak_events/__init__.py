"""oak-events: privacy-first events from Luxonis OAK cameras for AI agents.

The camera detects, tracks and measures depth on its own chip. oak-events turns
that into JSON lines and serves them to agents over MCP. Agents never receive a
picture, and no picture is ever written to disk.
"""

__version__ = "0.1.2"
