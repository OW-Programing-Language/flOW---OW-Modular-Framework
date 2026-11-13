#!/usr/bin/env python3
"""Legacy flOW contracts.json verifier for class-based Modules.

The native OW compiler now supports module_type / functor_type / with_type,
opaque type checking and import boundaries via 'ow check'. This Python verifier
is retained ONLY for legacy class-based flOW manifests and service declarations.
It is not an OW language type checker or an alternative to native ow check.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

DECL = re.compile(r"^(interface|class)\s+(\w+)(?:\(([^)]*)\))?:\s*$")
METHOD = re.compile(r"^  fn\s+(?:(private|public)\s+)?(\w+)\(([^)]*)\)\s*:\s*$")
SIGNATURE = re.compile(r"^  fn\s+(\w+)\(([^)]*)\)\s*$")
IMPORT = re.compile(r'^import\s+"([^"]+)"\s*$')
PROVIDE = re.compile(r'app\.provide_as\("([^"]+)",\s*"([^"]+)",\s*\w+\)')
REQUIRE = re.compile(r'app\.require_as\("([^"]+)",\s*"([^"]+)",\s*"([^"]+)"\)')
BIND = re.compile(r'set\s+\w+\s+(\w+):\s*app\.service\("([^"]+)"\)')


@dataclass
class Decl:
    kind: str
    name: str
    parents: tuple[str, ...]
    methods: dict[str, tuple[int, bool]]
    path: Path


def count_params(value: str) -> int:
    return len([p for p in value.split(",") if p.strip()])


def parse(path: Path) -> tuple[list[Decl], list[str]]:
    declarations: list[Decl] = []
    imports: list[str] = []
    current: Decl | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if match := IMPORT.match(line):
            imports.append(match.group(1))
        if match := DECL.match(line):
            parents = tuple(p.strip() for p in (match.group(3) or "").split(",") if p.strip())
            current = Decl(match.group(1), match.group(2), parents, {}, path)
            declarations.append(current)
            continue
        if line and not line.startswith(" ") and not line.startswith("#"):
            current = None
        if current is None:
            continue
        if current.kind == "interface":
            if match := SIGNATURE.match(line):
                current.methods[match.group(1)] = (count_params(match.group(2)), False)
        elif match := METHOD.match(line):
            current.methods[match.group(2)] = (count_params(match.group(3)), match.group(1) == "private")
    return declarations, imports


def verify(project: Path, core: Path | None = None) -> list[str]:
    project = project.resolve()
    core = (core or Path(__file__).resolve().parents[1] / "src").resolve()
    errors: list[str] = []
    manifest_path = project / "contracts.json"
    try:
        modules = json.loads(manifest_path.read_text(encoding="utf-8"))["modules"]
        if not isinstance(modules, list) or not modules:
            raise ValueError("modules must be a non-empty array")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return [f"{manifest_path}: invalid module manifest: {exc}"]

    sources = sorted(set(project.rglob("*.ow")) | set(core.glob("*.ow")))
    decl: dict[str, Decl] = {}
    imports_by_file: dict[Path, list[str]] = {}
    for source in sources:
        entries, imports = parse(source)
        imports_by_file[source] = imports
        for item in entries:
            if item.name in decl:
                errors.append(f"duplicate declaration {item.name}: {item.path} and {decl[item.name].path}")
            else:
                decl[item.name] = item

    def inherits(child: Decl, interface: str, seen: set[str] | None = None) -> bool:
        seen = set() if seen is None else seen
        if child.name in seen:
            return False
        seen.add(child.name)
        for name in child.parents:
            if name == interface:
                return True
            if name in decl and inherits(decl[name], interface, seen):
                return True
        return False

    def find_method(child: Decl, method: str, seen: set[str] | None = None) -> tuple[int, bool] | None:
        seen = set() if seen is None else seen
        if child.name in seen:
            return None
        seen.add(child.name)
        if method in child.methods:
            return child.methods[method]
        for name in child.parents:
            parent = decl.get(name)
            if parent and parent.kind == "class":
                found = find_method(parent, method, seen)
                if found is not None:
                    return found
        return None

    for item in decl.values():
        if item.kind != "class":
            continue
        for parent in item.parents:
            if parent not in decl:
                errors.append(f"{item.path}: class {item.name} has unknown parent {parent}")
        for iface in decl.values():
            if iface.kind != "interface" or not inherits(item, iface.name):
                continue
            for method, (arity, _) in iface.methods.items():
                actual = find_method(item, method)
                if actual is None:
                    errors.append(f"{item.path}: {item.name} does not implement {iface.name}.{method}/{arity}")
                elif actual[0] != arity:
                    errors.append(f"{item.path}: {item.name}.{method} has {actual[0]} args; {iface.name} requires {arity}")
                elif actual[1]:
                    errors.append(f"{item.path}: {item.name}.{method} is private; {iface.name} requires public")

    providers: dict[str, dict] = {}
    names: set[str] = set()
    for module in modules:
        try:
            name = module["name"]
            service = module["service"]
            iface = module["interface"]
            klass = module["class"]
            factory = module["factory"]
            reqs = module["requires"]
            paths = {
                "api": (project / module["api"]).resolve(),
                "implementation": (project / module["implementation"]).resolve(),
                "functor": (project / module["functor"]).resolve(),
            }
            if not all(p.is_relative_to(project) for p in paths.values()):
                errors.append(f"{name}: file escapes project boundary")
                continue
        except (KeyError, TypeError) as exc:
            errors.append(f"invalid module entry: {exc}")
            continue

        if name in names:
            errors.append(f"duplicate module name {name}")
        names.add(name)
        if service in providers:
            errors.append(f"duplicate provider for service {service}")
        providers[service] = module
        for path in paths.values():
            if not path.is_file():
                errors.append(f"{name}: missing file {path}")
        if not all(p.is_file() for p in paths.values()):
            continue
        if f"{name}/api/" not in paths["api"].as_posix():
            errors.append(f"{name}: API must be in {name}/api")
        if any(f"{name}/infra/" not in paths[k].as_posix() for k in ("implementation", "functor")):
            errors.append(f"{name}: implementation and functor must be in {name}/infra")

        api_decl = decl.get(iface)
        impl_decl = decl.get(klass)
        fac_decl = decl.get(factory)
        if not api_decl or api_decl.kind != "interface" or api_decl.path != paths["api"]:
            errors.append(f"{name}: missing public interface {iface}")
        if not impl_decl or impl_decl.kind != "class" or impl_decl.path != paths["implementation"]:
            errors.append(f"{name}: missing implementation class {klass}")
        elif not inherits(impl_decl, "Module") or not inherits(impl_decl, iface):
            errors.append(f"{name}: {klass} must implement Module and {iface}")
        if not fac_decl or fac_decl.kind != "class" or fac_decl.path != paths["functor"]:
            errors.append(f"{name}: missing functor class {factory}")
        elif not inherits(fac_decl, module.get("factory_type", "Functor")):
            errors.append(f"{name}: {factory} must implement {module.get('factory_type', 'Functor')}")

        factory_text = paths["functor"].read_text(encoding="utf-8")
        if not re.search(r"\bnew\s+" + re.escape(klass) + r"\s*\(", factory_text):
            errors.append(f"{name}: {factory} does not construct {klass}")
        parameter = module.get("parameter")
        if parameter:
            param_iface = parameter.get("interface")
            source = parameter.get("source_service")
            functor_sig = fac_decl.methods.get("make") if fac_decl else None
            if functor_sig is None or functor_sig[0] != 1:
                errors.append(f"{name}: parameterized functor must have make(dependency)")
            if not re.search(r"set\s+\w+\s+" + re.escape(param_iface or "") + r":\s*\w+", factory_text):
                errors.append(f"{name}: functor input must bind its dependency as {param_iface}")
            if not re.search(r"set\s+\w+\s+" + re.escape(iface) +
                             r":\s*new\s+" + re.escape(klass) + r"\s*\(", factory_text):
                errors.append(f"{name}: functor output must be typed {iface}")
            if (source, param_iface) not in {(x["service"], x["interface"]) for x in reqs}:
                errors.append(f"{name}: functor parameter must match declared required service {source}:{param_iface}")
        impl_text = paths["implementation"].read_text(encoding="utf-8")
        provided = set(PROVIDE.findall(impl_text))
        if provided != {(service, iface)}:
            errors.append(f"{name}: provide_as must declare exactly {service}:{iface}, got {provided}")
        expected = {(name, req["service"], req["interface"]) for req in reqs}
        actual = set(REQUIRE.findall(impl_text))
        if expected != actual:
            errors.append(f"{name}: required contracts mismatch: expected {expected}, got {actual}")
        bindings = set(BIND.findall(impl_text))
        for req in reqs:
            if not parameter and (req["interface"], req["service"]) not in bindings:
                errors.append(f"{name}: missing typed binding of {req['service']} to {req['interface']}")

    for module in modules:
        for req in module.get("requires", []):
            provider = providers.get(req["service"])
            if provider is None:
                errors.append(f"{module['name']}: no provider for {req['service']}")
            elif provider["interface"] != req["interface"]:
                errors.append(f"{module['name']}: {req['service']} expects {req['interface']} but provider publishes {provider['interface']}")

    # Cross-module imports must target public API, never another module's infra.
    for source, imports in imports_by_file.items():
        for imp in imports:
            target = (source.parent / imp).resolve()
            if not target.is_file():
                errors.append(f"{source}: missing import {imp}")
                continue
            if not source.is_relative_to(project):
                continue
            origin = source.relative_to(project).parts
            if len(origin) < 3:
                continue  # application composition root may wire infra functors
            target_rel = target.relative_to(project).parts if target.is_relative_to(project) else ()
            if len(target_rel) >= 3 and target_rel[0] != origin[0] and target_rel[1] == "infra":
                errors.append(f"{source}: forbidden import of another module's infra: {imp}")

    return errors


def main() -> int:
    cli = argparse.ArgumentParser(description="Validate flOW typed contracts and module boundaries")
    cli.add_argument("project", nargs="?", type=Path,
                     default=Path(__file__).resolve().parents[1] / "examples" / "modular_shop")
    args = cli.parse_args()
    errors = verify(args.project)
    if errors:
        for error in errors:
            print("FAIL " + error, file=sys.stderr)
        print(f"{len(errors)} contract violation(s)", file=sys.stderr)
        return 1
    print(f"PASS flOW contracts and module boundaries: {args.project}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
