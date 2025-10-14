"""Vault package interface."""

from .vault import KeyVault, VaultAccessError, KeyHandle
from .vault_interface import VaultInterface

__all__ = ["KeyVault", "VaultAccessError", "KeyHandle", "VaultInterface"]
