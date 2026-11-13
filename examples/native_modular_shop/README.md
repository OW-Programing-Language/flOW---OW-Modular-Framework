# Native module/functor architecture for flOW

Three business domains (**Inventory**, **Orders**, **Notifications**) each
have `api/` and `infra/` folders. Inventory exposes an **abstract SKU**
through `module_type INVENTORY`. Its private `Warehouse` implementation
uses `int` internally, but consumers never see the concrete type.

`MakeOrders` and `MakeNotifications` are **native OW functors**, not
configuration factories. Each accepts a genuine module implementing INVENTORY
and constructs a module matching its public output signature:

```ow
functor MakeOrders(Stock: INVENTORY) -> ORDERS:
  fn place(quantity int) -> int:
    return: Stock.check(Stock.issue(quantity))
```

Run from repository root after installing a recent OW compiler:

```sh
ow run examples/native_modular_shop/main.ow
```

The independent event-driven `App` and its runtime `Functor.make(app)`
contract remain available for lifecycle control, service injection and
event dispatch. This example exercises the **native** OW language module
calculus; it does not pretend the native functor is already an `App.Module`
instance. A future integration can bridge those two models explicitly.

The native module language supports checked signatures, opaque type members,
applicative/generative identities, and explicit manifest sharing; it does not
yet provide OCaml's full higher-order/type-dependent functors or `with type`
path sharing.
