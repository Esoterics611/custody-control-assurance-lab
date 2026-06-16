"""Live on-chain assurance target.

Points the SAME control-validation discipline at a REAL deployed institutional
digital-asset protocol (nexus-protocol on Base Sepolia). Strictly READ-ONLY
(eth_call) — the lab never sends a transaction, holds no key, and degrades to
SKIPPED when web3 isn't installed or the RPC is unreachable, so offline/CI stays
green.
"""
