import asyncio
from .main import RenderServer

server = RenderServer()

with asyncio.Runner() as runner:
    try:
        runner.run(server.main_loop())
    except (KeyboardInterrupt, RuntimeError, asyncio.CancelledError):
        runner.run(server.on_exit())
    finally:
        runner.close()
