# flOW — a modular framework for OW

**flOW** helps you build applications in the
[OW language](https://github.com/OW-Programing-Language) as a **modular monolith**:
small, self-contained modules that are composed by an application context and
communicate through **services** and **events** instead of referencing each
other directly.

Inspired by **Spring Modulith** (application modules + domain events + dependency
verification), mod-loader style composition (drop in a module, it wires itself),
and **OCaml functors** (modules parameterized by other modules).

Modules are first-class and manageable at runtime: **parameterizable** (config),
**enable / disable**, **reload**, and built via **functors**.

```yaml
main:
  set app: new App()
  call: app.set_config("inventory.stock", 25)   # parameterize
  call: app.apply(new InventoryFunctor())        # functor builds a configured module
  call: app.use(new NotifyModule())
  call: app.use(new OrdersModule())
  call: app.boot()                               # register -> verify -> start
  call: app.disable("notify")                    # toggle a module off
  call: app.reload("inventory")                  # reset a module's state
```

## Concepts

| Piece | File | Role |
|------|------|------|
| **App** | `src/App.ow` | The application context: registers modules, holds the service registry and config, dispatches events, and manages modules (enable/disable/reload). |
| **Module** | `src/Module.ow` | The contract a module implements: `name()`, `requires()`, `register(app)`, `start(app)`, `on_event(type, payload)`, `reload(app)`. |
| **Functor** | `src/Functor.ow` | `make(app)` → builds a configured Module from the app context (OCaml-style). |
| **Registry** | `src/Registry.ow` | Name → value store (used for both services and config). |

## Boot lifecycle
1. **register** — every module wires itself: `app.provide(name, service)`, reads config.
2. **verify** — every service a module declared in `requires()` must exist, or boot aborts.
3. **start** — every module runs: `app.emit(type, payload)`, use services via `app.service(name)`.

## Events
`app.emit(type, payload)` is delivered to **every enabled module's**
`on_event(type, payload)`. Modules never reference each other — a publisher does
not know its subscribers. Disable a module and it stops receiving events.

## Module controls

### Parameterize (config)
```yaml
call: app.set_config("sound.track", "piano1")
# inside a module:
set track: app.config_or("sound.track", "calm1")   # value or default
```

### Enable / disable
```yaml
call: app.disable("notify")      # stops receiving events
call: app.enable("notify")
set on int: app.is_enabled("notify")
```

### Reload
```yaml
call: app.reload("inventory")    # calls the module's reload(app) to reset state
```

### Functors (OCaml-style)
A functor builds a module from the app context, so a module can be parameterized
by config or by other modules/services — like `module Make (Deps) = ...`:
```yaml
class InventoryFunctor:
  fn new():
    return: 0
  fn make(app):
    set n int: app.config_or("inventory.stock", 10)
    set m: new InventoryModule()
    call: m.set_stock(n)
    return: m
# register it:
call: app.apply(new InventoryFunctor())
```

## Writing a module
Implement the six `Module` methods. React to events in `on_event`; reset in `reload`.
```yaml
class InventoryModule:
  field stock
  field start_stock
  fn new():
    set this.start_stock: 10
    set this.stock: 10
  fn name():
    return: "inventory"
  fn requires():
    return: array(0, 0)
  fn set_stock(n):
    set this.start_stock: n
    set this.stock: n
    return: 0
  fn register(app):
    call: app.provide("inventory", this)
    return: 0
  fn start(app):
    return: 0
  fn on_event(type, payload):
    if: type == "order.placed"
      set this.stock: this.stock - payload
    return: 0
  fn reload(app):
    set this.stock: this.start_stock
    return: 0
```

## App API
| Call | Does |
|------|------|
| `app.use(module)` | register a module |
| `app.apply(functor)` | build a module via `functor.make(app)` and register it |
| `app.provide(name, value)` / `app.service(name)` / `app.has_service(name)` | service container |
| `app.set_config(key, value)` / `app.config_or(key, default)` | config |
| `app.enable(name)` / `app.disable(name)` / `app.is_enabled(name)` | toggle a module |
| `app.reload(name)` | reset a module |
| `app.emit(type, payload)` | publish an event to all enabled modules |
| `app.verify()` / `app.boot()` | verify dependencies / register→verify→start |

## Try it
```bash
ow run examples/shop/main.ow   # functor + config + events + disable + reload
ow run tests/run.ow            # the test suite (prints PASS/FAIL)
```

## Layout
```
src/        flOW core (App, Registry, Module, Functor)
examples/   shop/ — a worked modular-monolith example
tests/      run.ow — registry, config, events, enable/disable, reload, functor, verify
```

## License
[MIT](LICENSE).
