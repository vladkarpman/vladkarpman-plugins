#!/usr/bin/env python3
"""Entry point for device-manager MCP server."""

import asyncio
import sys
from .server import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
