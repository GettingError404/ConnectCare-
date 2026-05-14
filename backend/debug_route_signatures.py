from __future__ import annotations

import inspect
from typing import Any, Callable, get_args, get_origin

from fastapi.params import Depends as DependsParam
from fastapi.routing import APIRoute
from starlette.requests import Request

from app.main import app


def is_callable_annotation(annotation: Any) -> bool:
    if annotation is Callable:
        return True

    origin = get_origin(annotation)
    if origin is Callable:
        return True

    if origin is not None:
        return any(is_callable_annotation(arg) for arg in get_args(annotation))

    text = str(annotation)
    return "typing.Callable" in text or "collections.abc.Callable" in text


def is_any_annotation(annotation: Any) -> bool:
    return annotation is Any or str(annotation) == "typing.Any"


def route_header(route: APIRoute) -> str:
    methods = ",".join(sorted(route.methods or []))
    return f"{methods} {route.path} -> {route.endpoint.__module__}.{route.endpoint.__name__}"


def inspect_callable(fn: Any, context: str) -> list[str]:
    issues: list[str] = []
    try:
        sig = inspect.signature(fn)
    except Exception as exc:
        issues.append(f"{context}: failed to inspect signature: {exc}")
        return issues

    for name, param in sig.parameters.items():
        ann = param.annotation
        default = param.default

        if is_callable_annotation(ann):
            issues.append(f"{context}: parameter '{name}' has Callable annotation: {ann}")

        if is_any_annotation(ann):
            issues.append(f"{context}: parameter '{name}' has Any annotation")

        if isinstance(default, DependsParam):
            dep = default.dependency
            if ann is Request:
                issues.append(f"{context}: Request parameter '{name}' incorrectly wrapped with Depends()")
            if dep is None:
                issues.append(f"{context}: parameter '{name}' uses Depends() with no callable")

        if ann is inspect._empty and isinstance(default, DependsParam):
            dep = default.dependency
            if dep is None:
                issues.append(f"{context}: dependency parameter '{name}' has no annotation and Depends() with no callable")

    return issues


def main() -> int:
    routes = sorted([r for r in app.routes if isinstance(r, APIRoute)], key=lambda r: (r.path, sorted(r.methods or []), r.name))
    print(f"[debug_route_signatures] APIRoutes detected: {len(routes)}")

    total = 0

    for route in routes:
        route_issues = inspect_callable(route.endpoint, f"route {route_header(route)}")

        for dep in route.dependant.dependencies:
            dep_call = dep.call
            dep_name = getattr(dep_call, "__name__", repr(dep_call))
            dep_issues = inspect_callable(dep_call, f"dependency {route.path}::{dep_name}")
            route_issues.extend(dep_issues)

        if route.response_model is not None and is_callable_annotation(route.response_model):
            route_issues.append(f"route {route_header(route)}: response_model is Callable-like: {route.response_model}")

        if route_issues:
            print("-" * 88)
            print(route_header(route))
            for issue in route_issues:
                print(f"  [suspicious] {issue}")
            total += len(route_issues)

    print("-" * 88)
    print(f"[debug_route_signatures] Suspicious items found: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
