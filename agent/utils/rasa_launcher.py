import asyncio
import logging
import os
import signal
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RasaLauncherConfig:
    conda_env_name: str
    rasa_workdir: str
    # Where the HTTP server should be reachable
    rasa_url: str = "http://localhost:5005"
    # Command to launch Rasa server
    rasa_command: str = "rasa"
    # If true, tries to start rasa even if already reachable
    force_start: bool = False


class RasaServerLauncher:
    """Starts the Rasa server using `conda run -n <env> ...`.

    This repo calls Rasa over HTTP (see pipeline/nlp_hybrid.py). So this launcher
    ensures the Rasa server is up before the pipeline starts.
    """

    def __init__(self, config: RasaLauncherConfig):
        self.config = config
        self._proc: Optional[asyncio.subprocess.Process] = None

    async def _http_is_reachable(self) -> bool:
        # Import lazily to keep startup fast
        import aiohttp

        url = self.config.rasa_url.rstrip("/") + "/"
        try:
            timeout = aiohttp.ClientTimeout(total=2.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    return resp.status in (200, 404)
        except Exception:
            return False

    async def start_if_needed(self) -> None:
        if not self.config.force_start:
            reachable = await self._http_is_reachable()
            if reachable:
                logger.info("Rasa server already reachable; not starting")
                return

        # If a process is already running, do nothing
        if self._proc and self._proc.returncode is None:
            return

        # Rasa server command; must be run from the directory containing config.yml/domain.yml.
        # Use `conda run` so it uses the `rasa_env` environment.
        cmd = (
            f"conda run -n {self.config.conda_env_name} "
            f"{self.config.rasa_command} run --enable-api --cors '*' --debug"
        )

        # Windows: subprocess with shell=True so `conda` resolution works.
        logger.info(
            "Starting Rasa server with conda env '%s' (workdir=%s) ...",
            self.config.conda_env_name,
            self.config.rasa_workdir,
        )
        self._proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=self.config.rasa_workdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait until reachable (or fail)
        for attempt in range(60):
            if await self._http_is_reachable():
                logger.info("Rasa server is reachable")
                return
            await asyncio.sleep(0.5)

        raise RuntimeError("Rasa server did not become reachable within timeout")

    async def shutdown(self) -> None:
        if self._proc and self._proc.returncode is None:
            logger.info("Shutting down Rasa server process")
            try:
                self._proc.send_signal(signal.SIGTERM)
            except Exception:
                pass
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=10)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass

