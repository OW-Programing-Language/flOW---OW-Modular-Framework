# flOW v2 — native functors + runtime lifecycle

Three separated business domains with public `api/` signatures and private
`infra/` implementations:

```text
flow2_shop/
├── main.ow                   # composition root (the only place that imports infra)
├── inventory/
│   ├── api/InventoryApi.ow   # INVENTORY + opaque sku type
│   └── infra/Warehouse.ow    # implementation (sku is privately an int)
├── orders/
│   ├── api/OrdersApi.ow      # ORDERS
│   └── infra/MakeOrders.ow   # INVENTORY -> ORDERS
└── notifications/
    ├── api/NotificationsApi.ow
    └── infra/MakeNotifications.ow # ORDERS -> NOTIFICATIONS
```

## Why this is different from the old flOW example

`module Inventory = Warehouse` and `module Shop.Inventory = Inventory`
are true OW aliases preserving Warehouse's opaque SKU identity. The application
passes `Shop.Inventory` to `MakeOrders` and registers `Inventory` with flOW,
but both still refer to the exact same typed module value.

`module_type INVENTORY`, `ORDERS` and `NOTIFICATIONS` each use
`include NATIVE_LIFECYCLE` to reuse the lifecycle signature instead of
repeating seven method declarations. The compiler expands included public
methods before validating the implementations and functors.

`MakeOrders` and `MakeNotifications` are **native OW functors**, not
`class Functor.make(app)` factories. The compiler validates their module
signatures, arguments, abstract SKU identity and public exports. A private
`Inventory.sku` representation cannot be accessed by consumers.

```ow
set orders ORDERS: MakeOrders(Warehouse)
set notifications NOTIFICATIONS: MakeNotifications(orders)
```

The flOW runtime can then manage these native values without converting
them into untyped services:

```ow
set app: new App()
call: app.use_native_as(notifications, "NOTIFICATIONS")
call: app.use_native_as(orders, "ORDERS")
call: app.use_native_as(Warehouse, "INVENTORY")
call: assert(app.boot() == 1)
set inventory INVENTORY: app.service("inventory")
```

The bridge validates its `NATIVE_LIFECYCLE` signature structurally and stores
the **original OW module value** in the registry, keeping its domain signature.
The optional contract label in `use_native_as` is a runtime service label;
the compiler proves the module contract at the typed service binding.

## Guarantees in this example

- Registration is deliberately *reverse dependency order*.
- flOW verifies services and starts **Inventory → Orders → Notifications**.
- Events reach only started, enabled native modules.
- Disabling a provider with running consumers is rejected.
- Disabling/re-enabling Notifications calls its stop/start methods.
- Shutdown runs **Notifications → Orders → Inventory**.
- A negative start result triggers rollback (separate regression fixture).
- Native functor types are checked with `ow check` before any `main`.

```bash
ow check examples/flow2_shop/main.ow
ow run examples/flow2_shop/main.ow
```

See `tests/` for positive and negative integration fixtures. Native modules
use an integer event payload in the current `NATIVE_LIFECYCLE` signature,
and adapter calls are interpreter-managed. OW's native LLVM backend does
not yet compile module/functor values.
