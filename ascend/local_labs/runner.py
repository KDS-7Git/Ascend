"""Private HTTP service and CLI for a dedicated lab runner host."""

import argparse
import asyncio
import hmac
import os
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from ascend.local_labs.hosted import RECIPES, Controller
from ascend.local_labs.runner_protocol import Action


def create_runner(root, key, *, controller=None):
    if len(key) < 32:
        raise ValueError("ASCEND_RUNNER_KEY must contain at least 32 characters")
    controller = controller or Controller(root)

    async def sweep():
        while True:
            await asyncio.sleep(30)
            await asyncio.to_thread(controller.reconcile)

    @asynccontextmanager
    async def lifespan(app):
        await asyncio.to_thread(controller.reconcile, True)
        task = asyncio.create_task(sweep())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            await asyncio.to_thread(controller.close)

    app = FastAPI(
        title="Ascend private lab runner",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.controller = controller

    @app.middleware("http")
    async def boundary(request, call_next):
        auth = request.headers.get("authorization", "")
        if not hmac.compare_digest(auth.encode(), ("Bearer " + key).encode()):
            return JSONResponse(
                {"detail": "Runner authentication required"}, status_code=401
            )
        if request.method == "POST":
            body = bytearray()
            async for chunk in request.stream():
                if len(body) + len(chunk) > 1048576:
                    return JSONResponse(
                        {"detail": "Runner input exceeds 1 MiB"}, status_code=413
                    )
                body.extend(chunk)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ValueError)
    async def invalid(request, error):
        return JSONResponse({"detail": str(error)}, status_code=400)

    def scope(account: str):
        controller.account(account)
        return account

    @app.get("/v1/capabilities")
    def capabilities():
        return controller.capabilities()

    @app.get("/v1/accounts/{account}/runs")
    def runs(account=Depends(scope)):
        return controller.status(account)

    @app.post("/v1/accounts/{account}/runs")
    def start(body: Action, account=Depends(scope)):
        return controller.queue(
            account, "start", data=body.model_dump(exclude_none=True)
        )

    @app.post("/v1/accounts/{account}/runs/{run_id}/{action}")
    def action(run_id: str, action: str, body: Action, account=Depends(scope)):
        if action == "start":
            raise HTTPException(404, "Unknown action")
        return controller.queue(
            account, action, run_id, body.model_dump(exclude_none=True)
        )

    @app.get("/v1/accounts/{account}/runs/{run_id}/files")
    def file(run_id: str, name: str, account=Depends(scope)):
        return controller.read(account, run_id, name)

    return app


def main():
    parser = argparse.ArgumentParser(prog="ascend-lab-runner")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8421)
    parser.add_argument(
        "--home",
        default=os.environ.get("ASCEND_RUNNER_HOME", "~/.local/share/ascend-runner"),
    )
    parser.add_argument(
        "--max-active",
        type=int,
        default=int(os.environ.get("ASCEND_RUNNER_MAX_ACTIVE", "2")),
    )
    parser.add_argument(
        "--reserve-gib",
        type=int,
        default=int(os.environ.get("ASCEND_RUNNER_RESERVE_GIB", "10")),
    )
    parser.add_argument("--lifetime", type=int, default=7200)
    args = parser.parse_args()
    os.umask(0o077)
    key = os.environ.get("ASCEND_RUNNER_KEY", "")
    try:
        selected = os.environ.get("ASCEND_RUNNER_RECIPES")
        controller = Controller(
            args.home,
            recipes=selected.split(",") if selected else RECIPES,
            max_active=args.max_active,
            reserve_bytes=args.reserve_gib * 1024**3,
            lifetime=args.lifetime,
        )
        app = create_runner(args.home, key, controller=controller)
    except ValueError as error:
        parser.exit(2, f"{error}\n")
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, workers=1)


if __name__ == "__main__":
    main()
