"""Run: python3 -m unittest discover -s tests -p test_contracts.py"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from verify_contracts import verify  # noqa: E402


class InterfaceContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name) / "examples" / "modular_shop"
        shutil.copytree(ROOT / "examples" / "modular_shop", self.project)
        shutil.copytree(ROOT / "src", Path(self.tmp.name) / "src")

    def run_verify(self):
        return verify(self.project, Path(self.tmp.name) / "src")

    def mutate(self, name, old, new):
        path = self.project / name
        data = path.read_text(encoding="utf-8")
        self.assertIn(old, data)
        path.write_text(data.replace(old, new), encoding="utf-8")

    def test_valid_three_module_example(self):
        self.assertEqual([], self.run_verify())

    def test_missing_interface_method_rejected(self):
        self.mutate("inventory/infra/InventoryModule.ow", "  fn reserve(quantity):", "  fn reserved(quantity):")
        self.assertIn("does not implement InventoryApi.reserve", "\n".join(self.run_verify()))

    def test_wrong_arity_rejected(self):
        self.mutate("inventory/infra/InventoryModule.ow", "  fn reserve(quantity):", "  fn reserve():")
        self.assertIn("InventoryApi requires 1", "\n".join(self.run_verify()))

    def test_private_method_rejected(self):
        self.mutate("inventory/infra/InventoryModule.ow", "  fn reserve(quantity):", "  fn private reserve(quantity):")
        self.assertIn("is private", "\n".join(self.run_verify()))

    def test_wrong_registered_contract_rejected(self):
        self.mutate("inventory/infra/InventoryModule.ow", 'app.provide_as("inventory", "InventoryApi", api)',
                    'app.provide_as("inventory", "OrdersApi", api)')
        self.assertIn("provide_as must declare exactly", "\n".join(self.run_verify()))

    def test_wrong_consumer_contract_rejected(self):
        self.mutate("orders/infra/OrdersModule.ow", 'app.require_as("orders", "inventory", "InventoryApi")',
                    'app.require_as("orders", "inventory", "OrdersApi")')
        self.assertIn("required contracts mismatch", "\n".join(self.run_verify()))

    def test_dependency_contract_mismatch_in_manifest_rejected(self):
        p = self.project / "contracts.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        data["modules"][1]["requires"][0]["interface"] = "OrdersApi"
        p.write_text(json.dumps(data), encoding="utf-8")
        self.assertIn("expects OrdersApi but provider publishes InventoryApi", "\n".join(self.run_verify()))

    def test_cross_module_infrastructure_import_rejected(self):
        self.mutate("orders/infra/OrdersModule.ow", 'import "../api/OrdersApi.ow"',
                    'import "../../inventory/infra/InventoryModule.ow"\nimport "../api/OrdersApi.ow"')
        self.assertIn("forbidden import of another module's infra", "\n".join(self.run_verify()))

    def test_unknown_interface_rejected(self):
        self.mutate("inventory/infra/InventoryModule.ow", "class InventoryModule(Module, InventoryApi):",
                    "class InventoryModule(Module, ImaginaryApi):")
        self.assertIn("unknown parent ImaginaryApi", "\n".join(self.run_verify()))


if __name__ == "__main__":
    unittest.main()
