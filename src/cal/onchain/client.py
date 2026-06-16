"""On-chain context: a thin, read-only eth_call facade over the vendored deployment.

The on-chain simulations only ever call ``ctx.call(contract, fn, *args)`` and read
addresses via ``ctx.addr(name)`` — they never touch web3 directly. That keeps them
trivially testable with :class:`FakeContext` (no network) and keeps web3 an optional,
lazily-imported dependency.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

DEFAULT_DEPLOYMENT = Path(__file__).resolve().parents[3] / "data" / "onchain" / "nexus_sepolia.json"

# Deterministic synthetic probe addresses for read-only behavioral checks.
DEAD_ADDRESS = "0x000000000000000000000000000000000000dEaD"
OTHER_ADDRESS = "0x0000000000000000000000000000000000001234"


class Context(Protocol):
    def call(self, contract: str, fn: str, *args: Any) -> Any: ...
    def addr(self, name: str) -> str: ...


def _load_web3():
    try:
        from web3 import Web3

        return Web3
    except ImportError:
        return None


@dataclass
class OnchainContext:
    """Live read-only context backed by web3 against a public testnet RPC."""

    deployment: dict
    _w3: Any
    _Web3: Any

    @property
    def chain(self) -> dict:
        return self.deployment["chain"]

    def addr(self, name: str) -> str:
        return self._Web3.to_checksum_address(self.deployment["addresses"][name])

    def _contract(self, name: str):
        return self._w3.eth.contract(address=self.addr(name), abi=self.deployment["abis"][name])

    def call(self, contract: str, fn: str, *args: Any) -> Any:
        checksummed = [
            self._Web3.to_checksum_address(a) if isinstance(a, str) and a.startswith("0x") else a
            for a in args
        ]
        return getattr(self._contract(contract).functions, fn)(*checksummed).call()

    @classmethod
    def connect(
        cls, rpc_url: str | None = None, deployment_path: Path | str = DEFAULT_DEPLOYMENT
    ) -> OnchainContext | None:
        """Return a live context, or None if web3 is missing / RPC is unreachable."""
        Web3 = _load_web3()  # noqa: N806 — Web3 is a class
        if Web3 is None:
            return None
        deployment = json.loads(Path(deployment_path).read_text())
        url = rpc_url or os.getenv("CAL_ONCHAIN_RPC_URL") or deployment["chain"]["rpc_url"]
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 12}))
            if not w3.is_connected():
                return None
            # Confirm we're on the expected chain.
            if w3.eth.chain_id != deployment["chain"]["chain_id"]:
                return None
        except Exception:
            return None
        return cls(deployment=deployment, _w3=w3, _Web3=Web3)


@dataclass
class FakeContext:
    """Deterministic offline context for unit tests. Maps (contract, fn) -> value."""

    responses: dict[tuple[str, str], Any]
    addresses: dict[str, str]

    def addr(self, name: str) -> str:
        return self.addresses[name]

    def call(self, contract: str, fn: str, *args: Any) -> Any:
        value = self.responses[(contract, fn)]
        return value(*args) if callable(value) else value
