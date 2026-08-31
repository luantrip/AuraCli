"""
Optional embedding support package for auxiliary semantic capabilities.

This package provides the lightweight HTTP client/server pair and helper
utilities used when Aura CLI enables embedding-backed semantic features.
It is useful, but it is not the canonical semantic center of the product.

Primary runtime meaning still comes from:

- `aura_cli.core.context`
- `aura_cli.core.memory`
- `aura_cli.core.llm`
"""
# This file makes the 'embeddings' directory a Python package.

# Unique embedding server port (avoids conflict with other services on 8765)
EMBEDDING_SERVER_PORT = 1333
