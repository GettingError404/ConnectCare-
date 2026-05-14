from __future__ import annotations

import traceback
from typing import Iterable

from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

from app.main import app


def route_key(route: APIRoute) -> tuple[str, str, str]:
    methods = ",".join(sorted(route.methods or []))
    return (route.path, methods, route.name)


def format_route(route: APIRoute) -> str:
    methods = ",".join(sorted(route.methods or []))
    return f"{methods} {route.path} -> {route.endpoint.__module__}.{route.endpoint.__name__}"


def sorted_api_routes(routes: Iterable[object]) -> list[APIRoute]:
    api_routes = [r for r in routes if isinstance(r, APIRoute)]
    return sorted(api_routes, key=route_key)


def try_generate(routes: list[APIRoute], title: str) -> tuple[bool, str | None]:
    try:
        get_openapi(title=title, version="debug", routes=routes)
        return True, None
    except Exception:
        return False, traceback.format_exc()


def main() -> int:
    all_routes = sorted_api_routes(app.routes)
    print(f"[debug_openapi] APIRoutes detected: {len(all_routes)}")

    ok, tb = try_generate(all_routes, "full")
    if ok:
        print("[debug_openapi] Full OpenAPI generation succeeded.")
        return 0

    print("[debug_openapi] Full OpenAPI generation failed. Starting isolation...")

    for route in all_routes:
        ok_single, tb_single = try_generate([route], f"single::{route.path}")
        if not ok_single:
            print("[debug_openapi] FIRST FAILING ROUTE (single-route test):")
            print(format_route(route))
            print("[debug_openapi] Traceback:")
            print(tb_single)
            return 1

    selected: list[APIRoute] = []
    for route in all_routes:
        selected.append(route)
        ok_partial, tb_partial = try_generate(selected, "cumulative")
        if not ok_partial:
            print("[debug_openapi] FIRST FAILING ROUTE (cumulative-order test):")
            print(format_route(route))
            print("[debug_openapi] Traceback:")
            print(tb_partial)
            return 1

    print("[debug_openapi] Could not isolate route with incremental tests; failure may be cross-route interaction.")
    print("[debug_openapi] Full traceback:")
    print(tb)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
