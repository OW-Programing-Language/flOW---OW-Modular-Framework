# flOW — typed modular application framework for OW

flOW combines **OW's native, OCaml-inspired module/functor system** with a
**Spring Modulith-inspired runtime** for lifecycle, services and events.

The two formerly separate worlds now have a typed bridge:
`App.use_native()` / `App.use_native_as()` wrap a native OW module for
lifecycle operations while **retaining the original typed module value**
in the service registry.

**Start with the [flOW v2 three-domain shop](examples/flow2_shop/README.md).**

## 1. Native OW functors and modules

OW provides native `module_type`, `module`, `functor`, `functor_type`,
opaque types, `with_type`, generative and applicative identities and
higher-order functors. The `ow check` front end validates known module
expressions without executing `main`. These are **OW language features**,
not features implemented by the flOW class-based runtime.

```ow
# inventory/api/InventoryApi.ow
module_type INVENTORY:
  type sku
  fn issue(value int) -> sku
  fn available(value sku) -> int

# orders/infra/MakeOrders.ow
functor MakeOrders(Stock: INVENTORY) -> ORDERS:
  fn place(quantity int) -> int:
    return: Stock.available(Stock.issue(quantity))
```

The complete [flow2_shop](examples/flow2_shop/README.md) includes additional
lifecycle exports in each public signature so the module can also implement
`NATIVE_LIFECYCLE` structurally.

## 2. flOW runtime bridge

```ow
set orders ORDERS: MakeOrders(Warehouse)
set app: new App()
call: app.use_native_as(orders, "ORDERS")
call: app.use_native_as(Warehouse, "INVENTORY")
call: assert(app.boot() == 1)
set typedInventory INVENTORY: app.service("inventory")
call: app.emit("order.placed", 5)
call: app.stop()
```

`src/NativeLifecycle.ow` is a checked native module signature:
`name, requires, register, start, stop, reload, on_event`.
`NativeModuleAdapter` implements the legacy `Module` class interface.
It delegates lifecycle methods and registers the **original native module**
as a service. `set typedInventory INVENTORY: app.service(...)` verifies the
domain module signature on retrieval, rather than casting it to an untyped
class.

Contract names passed to `use_native_as` remain **runtime labels**; they
are not a substitute for the OW-checked module signature.

Native event payloads are currently `int` with event names of type `string`.
The adapter is an interpreter/runtime mechanism; OW LLVM native codegen does
not yet lower module/functor values.

## 3. Lifecycle and dependency rules

- `app.use(module)` — registers a legacy class-based Module.
- `app.apply(functor)` / `app.apply_to(functor,dependency)` — keeps legacy
  class factories operational.
- `app.use_native(module)` / `use_native_as(module, label)` — registers a
  genuine native OW module with checked lifecycle signature.
- `app.boot()` — registers all providers, verifies contracts, then starts
  in **dependency order**, even if registered in reverse order.
- `app.stop()` — stops started modules in **reverse startup order**.
- `app.disable(name)` — stops a module, but refuses disabling a required
  provider with running dependents.
- `app.enable(name)` — starts a disabled module only when its dependencies
  are running. Repeated enable/disable cycles do not fill the startup array.
- `app.reload(name)` — reloads only a running module.
- `app.emit(type,payload)` — dispatches to currently running, enabled modules.
- `start(app)` returning a **negative integer** aborts boot and rolls back
  successfully started modules. Existing implementations returning `0`
  remain successful.

Module names are unique; all fixed-capacity arrays check bounds rather
than silently overwriting data. The current maximum remains **64 modules**,
**128 typed requirements**, and **64 registry entries** per registry.
A failed boot is one-shot: create a new `App` to retry.

**Migration for class Modules:** implementations must now provide `stop(app)`.
flOW v2 adds it to all shipped legacy examples. Return `0` in modules with
no cleanup.

## 4. Compile-time checks versus legacy validation

```bash
ow check examples/flow2_shop/main.ow   # native compiler check, no execution
ow run examples/flow2_shop/main.ow     # native functors + flOW runtime
ow run tests/flow2_rollback.ow         # dependency rollback test

# Only for older class-based modular_shop service manifests:
python3 tools/verify_contracts.py
python3 -m unittest discover -s tests -p 'test_*.py'
```

The `tools/verify_contracts.py` script remains for **legacy class-based
`contracts.json` validation**, not for native module syntax. CI uses the
real `ow check` tool for native functors and tests negative cases.

CI is pinned to a tested `ow-lang` revision containing PRs #15–#35,
including reusable signature/implementation `include`, transparent module
aliases, lexical nested modules, sealed first-class module packages and
static integer LLVM lowering. See
[advanced flOW integration](examples/flow2_shop/advanced.ow).
See [architecture and OCaml feature comparison](docs/ARCHITECTURE.md).

## Legacy examples

- [shop](examples/shop/main.ow) — config-driven class functor and events.
- [modular_shop](examples/modular_shop/README.md) — three legacy class modules,
  `provide_as` / `require_as` and manifests.
- [native_modular_shop](examples/native_modular_shop/README.md) — original
  native functor demonstration **without runtime integration**.
- [flow2_shop](examples/flow2_shop/README.md) — full native module + runtime
  lifecycle integration (recommended).

## Scope relative to OCaml

flOW is **not the OCaml compiler**. It uses the first-order native module
features implemented by OW and adds application-specific runtime concerns
that OCaml itself does not supply as a framework. Nested modules, aliases,
`include` and complete OCaml module-language inference must be implemented
in the **OW compiler**, not claimed as flOW runtime features.

[MIT License](LICENSE).
