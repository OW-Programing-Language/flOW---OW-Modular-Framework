"""Regression tests for module-parameterized functors."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from verify_contracts import verify


class ModuleFunctorTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.project = Path(self.work.name) / "examples" / "modular_shop"
        shutil.copytree(ROOT / "examples" / "modular_shop", self.project)
        shutil.copytree(ROOT / "src", Path(self.work.name) / "src")

    def errors(self):
        return "\n".join(verify(self.project, Path(self.work.name) / "src"))

    def change(self, path, old, new):
        file = self.project / path
        data = file.read_text(encoding="utf-8")
        self.assertIn(old, data)
        file.write_text(data.replace(old, new), encoding="utf-8")

    def test_correct_module_functor(self):
        self.assertEqual("", self.errors())

    def test_factory_must_implement_module_functor(self):
        self.change("orders/infra/OrdersFunctor.ow",
                    "class OrdersFunctor(ModuleFunctor):", "class OrdersFunctor(Functor):")
        self.assertIn("must implement ModuleFunctor", self.errors())

    def test_wrong_input_interface_rejected(self):
        self.change("orders/infra/OrdersFunctor.ow", "set dependency InventoryApi: inventory",
                    "set dependency NotificationsApi: inventory")
        self.assertIn("functor input must bind its dependency as InventoryApi", self.errors())

    def test_wrong_output_interface_rejected(self):
        self.change("orders/infra/OrdersFunctor.ow",
                    "set result OrdersApi: new OrdersModule(dependency)",
                    "set result InventoryApi: new OrdersModule(dependency)")
        self.assertIn("functor output must be typed OrdersApi", self.errors())

    def test_factory_arity_rejected(self):
        self.change("orders/infra/OrdersFunctor.ow", "fn make(inventory):", "fn make():")
        self.assertIn("parameterized functor must have make(dependency)", self.errors())

    def test_parameter_contract_mismatch_rejected(self):
        path = self.project / "contracts.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        config["modules"][1]["parameter"]["interface"] = "NotificationsApi"
        path.write_text(json.dumps(config), encoding="utf-8")
        self.assertIn("functor parameter must match declared required service", self.errors())


if __name__ == "__main__":
    unittest.main()
