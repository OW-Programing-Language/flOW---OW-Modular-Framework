# Three-module modular monolith (OW)

Spring Modulith-style modules: **inventory**, **orders**, **notifications**.
Each owns an api/ interface and an infra/ implementation and functor.

```text
modular_shop/
├── main.ow                      # application composition root
├── contracts.json               # service/interface dependency manifest
├── inventory/
│   ├── api/InventoryApi.ow
│   └── infra/{InventoryModule,InventoryFunctor}.ow
├── orders/
│   ├── api/OrdersApi.ow
│   └── infra/{OrdersModule,OrdersFunctor}.ow
└── notifications/
    ├── api/NotificationsApi.ow
    └── infra/{NotificationsModule,NotificationsFunctor}.ow
```

Inventory owns stock, Orders depends only on InventoryApi and emits
order.placed events, and Notifications subscribes without importing Orders.
Orders must never import inventory/infra/. Only main.ow, as the application
composition root, imports the three infrastructure functors.

Each functor implements Functor.make(app) and constructs a configured Module:
InventoryFunctor uses inventory.start_stock, NotificationsFunctor reads the
notifications.prefix setting, and OrdersFunctor constructs an OrdersModule.
During boot, flOW verifies its name-based and declared typed service dependencies.

## Usage

```bash
python3 tools/verify_contracts.py examples/modular_shop
python3 -m unittest discover -s tests -p test_contracts.py
ow run tests/run.ow
ow run tests/runtime_contracts.ow
ow run examples/modular_shop/main.ow
```

The example starts with 25 items, places two orders (3 and 2), disables
Notifications and places a third order (4), then reloads only Inventory.
Assertions verify service wiring, isolation, events, and reload.

## What is and is not checked

**Static preflight** uses tools/verify_contracts.py to verify public interface
method names, arity, visibility, functors, dependencies, and api/infra boundaries.
**Boot-time validation** rejects missing providers, mismatched contract names,
and duplicate service providers. OW typed variable bindings enforce nominal
interface membership, not method completeness.

Unlike OCaml's module signatures and compile-time functors, flOW's functors
are currently runtime factories parameterized by an App context. OW interfaces
do not yet declare parameter or return types; no full static OCaml module type
system is claimed. Always run the preflight verifier in CI before execution.
