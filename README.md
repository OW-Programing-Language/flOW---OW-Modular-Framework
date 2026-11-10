# flOW — a modular framework for OW

**flOW** helps you build applications in the
[OW language](https://github.com/OW-Programing-Language) as a **modular monolith**:
small, self-contained modules that are composed by an application context and
communicate through **services** and **events** instead of referencing each
other directly.

It is inspired by **Spring Modulith** (application modules + domain events +
dependency verification) and by mod-loader style composition (drop in a module,
it wires itself).

```yaml
main:
  set app: new App()
  call: app.use(new InventoryModule())
  call: app.use(new NotifyModule())
  call: app.use(new OrdersModule())
  call: app.boot()
```

```
[inventory] ready with 10 items
[orders] placing orders...
[inventory] -3 -> 7 left
[notify] order confirmed for 3 item(s)
...
flOW: booted 3 module(s).
```

## Why

A growing OW program tends to turn into one big ball of mud. flOW gives you
**boundaries** without the weight of microservices:

- each feature is a **module** with explicit dependencies,
- modules expose capabilities as named **services**,
- modules react to each other through **events** (no direct references),
- the app **verifies** every declared dependency at boot.

## Concepts

| Piece | File | Role |
|------|------|------|
| **App** | `src/App.ow` | The application context. Registers modules, holds the service registry and the event bus, and boots them. |
| **Module** | `src/Module.ow` | The contract a module implements: `name()`, `requires()`, `register(app)`, `start(app)`. |
| **Registry** | `src/Registry.ow` | Name → service store (the service container). |
| **EventBus** | `src/EventBus.ow` | Publish/subscribe events so modules stay decoupled. |
| **Listener** | `src/Listener.ow` | The `on_event(type, payload)` contract for event subscribers. |

### Boot lifecycle

1. **register** — every module wires itself: `app.provide(name, service)` and
   `app.on(listener)`.
2. **verify** — every service a module declared in `requires()` must be present,
   or boot aborts with a clear message.
3. **start** — every module runs: `app.emit(type, payload)`, use resolved
   services via `app.service(name)`.

## Writing a module

A module is any object with the four `Module` methods. It can also be a
`Listener` (add `on_event`) to react to events.

```yaml
class InventoryModule:
  field stock
  fn new():
    set this.stock: 10

  fn name():
    return: "inventory"

  fn requires():
    return: array(0, 0)          # no dependencies

  fn register(app):
    call: app.provide("inventory", this)   # expose a service
    call: app.on(this)                      # subscribe to events
    return: 0

  fn start(app):
    return: 0

  fn on_event(type, payload):
    if: type == "order.placed"
      set this.stock: this.stock - payload
    return: 0
```

Publish an event from anywhere you have the `app`:

```yaml
call: app.emit("order.placed", 3)
```

## App API

| Call | Does |
|------|------|
| `app.use(module)` | register a module |
| `app.provide(name, value)` | register a service |
| `app.service(name)` | resolve a service |
| `app.has_service(name)` | is a service present? (1/0) |
| `app.on(listener)` | subscribe a listener to events |
| `app.emit(type, payload)` | publish an event |
| `app.verify()` | check all declared dependencies (1 = ok) |
| `app.boot()` | register → verify → start (1 = booted, 0 = aborted) |

## Try it

Install OW (see the [ow-lang releases](https://github.com/OW-Programing-Language)),
then from this folder:

```bash
ow run examples/shop/main.ow   # a 3-module modular monolith
ow run tests/run.ow            # the test suite (prints PASS/FAIL)
```

(Or open a file in **OwIDE** and click **Run ▶**.)

## Layout

```
src/        flOW core (App, Registry, EventBus, Module, Listener)
examples/   shop/ — a worked modular-monolith example
tests/      run.ow — registry, event bus and dependency-verification tests
```

## License

[MIT](LICENSE).
