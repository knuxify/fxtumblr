import asyncio
import traceback
from .main import RenderServer

server = RenderServer()

with asyncio.Runner() as runner:
    try:
        runner.run(server.main_loop())
    except (KeyboardInterrupt, RuntimeError, asyncio.CancelledError):
        try:
            runner.run(server.on_exit())
        except:
            traceback.print_exc()
    finally:
        runner.close()
