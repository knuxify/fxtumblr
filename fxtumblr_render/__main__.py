# SPDX-License-Identifier: MIT
"""Execute the server mainloop."""

import asyncio
import traceback

from .server import Server

server = Server()

with asyncio.Runner() as runner:
    try:
        runner.run(server.main_loop())
    except (KeyboardInterrupt, RuntimeError, asyncio.CancelledError):
        try:
            runner.run(server.on_close())
        except:  # noqa: E722
            traceback.print_exc()
    finally:
        runner.close()
