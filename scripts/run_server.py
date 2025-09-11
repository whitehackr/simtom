#!/usr/bin/env python3
"""Development server runner for SIMTOM."""

import uvicorn
from simtom.api import app

if __name__ == "__main__":
    uvicorn.run(
        "simtom.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )