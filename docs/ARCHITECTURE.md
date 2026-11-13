# flOW architecture — OW modules, native functors and runtime services

## Layer separation

```text
OW compiler (ow-lang)
  module_type / module / functor / functor_type
  abstract + manifest types, with_type, checked module application
  ow check: non-executing semantic analysis + diagnostic spans
                 |
                 | Native OW module value (preserves signature)
                 v
flOW NativeModuleAdapter : Module
  NATIVE_LIFECYCLE structural check; delegates 7 methods
                 |
                 v
flOW App
  lifecycle / topological startup / reverse stop / rollback
  registry (original native module value) / events / contracts
```

## Native modules vs class-based factories

The older `Functor.make(app)` and `ModuleFunctor.make(dependency)` are
**runtime class factories**, not OCaml-style functors. They remain for
backward compatibility. The new `MakeOrders(Stock: INVENTORY) -> ORDERS`
construct is an actual OW native functor checked by `ow check`.

A native module can have its typed domain signature and also be accepted
as a `NATIVE_LIFECYCLE` via structural signature width matching. flOW
does not convert the value to a class for service consumers: the adapter
is internal to lifecycle management and the registry retains the module
value as an OW native object.

## Features vs OCaml

| Feature | OW compiler | flOW |
| --- | --- | --- |
| Typed `module_type` / `module` | Yes | Uses native signatures |
| Parameterized functors | Yes | Uses as module instances |
| Abstract/manifest types, `with_type` | Supported subset | Preserved in native services |
| Functor type parameters and higher-order functors | Supported subset | Driven by OW |
| Generative / applicative identities | Runtime-checked subset | Unmodified native values |
| `ow check` semantic preflight | Yes | CI executes it |
| `api/infra` import boundaries | Checked by OW loader | Uses conventions |
| Signature `include` composition | Yes (OW PR #29) | Reuses NATIVE_LIFECYCLE in domain APIs |
| Transparent module aliases and dotted namespace aliases | Yes (OW PR #30) | Used in flow2_shop |
| Qualified native module definitions (e.g. Shop.Warehouse) | Yes (OW PR #31) | Used in flow2_shop |
| Full lexical nested module scopes and implementation include | Not yet | **Needs further OW language work** |
| Full static OCaml type inference | No | Not claimed |
| Lifecycle stop/restart/rollback, events | Not OCaml language constructs | Yes |
| Full LLVM native codegen for module values | No | Interpreter only |

## Current limitations

- Native `NATIVE_LIFECYCLE` requires `on_event(type string, payload int)`;
  generalized event payload types would require changes in OW.
- `use_native_as(module, "LABEL")` takes a human-provided contract label;
  typed OW bindings (e.g., `set inventory INVENTORY: app.service(...)`)
  provide the actual compiler/runtime guarantee. Labels are not proof.
- Fixed capacity is guarded, but dynamically sized registries are not
  available yet.
- `start` must signal failure with a negative return code; exceptions
  thrown inside a start callback aren't yet transactional.
- `stop()` is one-shot with respect to `boot()`; create a new App to
  restart an entire application.
- `tools/verify_contracts.py` is legacy-only. Avoid regex-based validation
  for new `module_type` source.

## Next OW language evolution

To match more of OCaml, add `include` for implementations,
lexically nested module implementations/signatures, module first-class
packing/unpacking and more complete type-equality inference to
`OW-Programing-Language/ow-lang`, with compiler tests. flOW can adopt
those capabilities when they exist, but cannot enforce their semantics
inside its application runtime.
