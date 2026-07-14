"""Safe telnet client for ISEEVY decoder. No /set.cgi ever. Off-site: verify via netstat/pro.ini.

Per skill operational rule (user 2026-07-13) and iseevy-decoder-interaction:
  * raw socket telnet, CRLF login (root/unisheen)
  * send CTRL-C x2 to drop the app's console -> real shell (-sh)
  * VERIFY the shell broke (sentinel echo SHELL_OK) BEFORE trusting any output;
    if you skip this the decoder's external operation degrades (flaky switching, stalled
    streams, misbehaving API).
  * bracket every command with markers; a background drainer captures all output.
  * close the socket cleanly (re-break) so the device stays in its good external state.
"""
from __future__ import annotations

import asyncio
import logging
import re
import secrets
from typing import Optional

_LOGGER = logging.getLogger(__name__)


class ISEEVYTelnetError(OSError):
    """Raised when the telnet shell-break/verify fails (subclass of OSError so the
    api-layer `except OSError` handlers convert it to ISEEVYAPIError)."""


class ISEEVYTelnetClient:
    """Minimal async telnet client.

    The decoder's main app floods /dev/console, so a plain command returns buried output.
    This client escapes to a real shell with CTRL-C x2, verifies the break with a sentinel
    echo, runs a background drainer that captures ALL output, and brackets each command with
    unique markers so the flood can't hide the result.
    """

    def __init__(
        self,
        host: str,
        username: str = "root",
        password: str = "unisheen",
        port: int = 23,
        timeout: int = 15,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._capture: list[bytes] = []
        self._task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port), timeout=self.timeout
        )
        self._task = asyncio.create_task(self._drain())
        # Timing mirrors the proven blocking iseevy_truth.py sequence:
        # an initial settle delay is REQUIRED before sending the username, otherwise
        # the login handshake races and the device re-prompts for a second password,
        # leaving us stuck at a `Password:` prompt instead of a shell.
        await asyncio.sleep(1.0)
        await self._send_line(self.username)
        await asyncio.sleep(1.0)
        await self._send_line(self.password)
        await asyncio.sleep(2.0)
        # Drop the app's console: CTRL-C x2 -> real shell
        self._writer.write(b"\x03\x03")
        await self._writer.drain()
        await asyncio.sleep(1.5)
        # VERIFY the shell broke (operational rule: device degrades if skipped).
        # Send a random token via `echo`; the shell prints it on its OWN line, while the
        # typed `echo TOKEN` input line contains "echo " and therefore does NOT match a
        # standalone output line. This avoids the false-positive of matching the input echo
        # (a bare `echo SHELL_OK_$$` check matched the echoed command, not real execution).
        # Retry the break a few times: under concurrent device load (e.g. the web poll
        # hitting getpro.cgi) the console flood can swallow the first CTRL-C break, leaving
        # the app console attached and every subsequent command to fail.
        for _ in range(3):
            token = "SHELLREADY_" + secrets.token_hex(4)
            self._capture.clear()
            await self._send_line(f"echo {token}")
            if await self._wait_for_line(token, timeout=8.0):
                return
            # break failed — re-issue CTRL-C x2 and try again
            self._writer.write(b"\x03\x03")
            await self._writer.drain()
            await asyncio.sleep(1.0)
        raise ISEEVYTelnetError(
            "Shell break failed on %s; app console still attached" % self.host
        )

    async def _wait_for(self, needle: bytes, timeout: float = 8.0) -> bool:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            if needle in b"".join(self._capture):
                return True
            await asyncio.sleep(0.2)
        return False

    async def _wait_for_line(self, token: str, timeout: float = 8.0) -> bool:
        """True only if a STANDALONE output line equals `token` (excludes the
        `echo TOKEN` input echo, which contains 'echo ')."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            for line in b"".join(self._capture).decode("latin-1", "replace").splitlines():
                if line.strip() == token:
                    return True
            await asyncio.sleep(0.2)
        return False

    async def _drain(self) -> None:
        try:
            while self._reader is not None:
                data = await self._reader.read(4096)
                if not data:
                    break
                self._capture.append(data)
        except Exception:  # connection closed / cancelled
            pass

    async def _send_line(self, text: str) -> None:
        if self._writer is None:
            return
        self._writer.write((text + "\r\n").encode())
        await self._writer.drain()

    async def _send_cmd(self, cmd: str, marker: str) -> None:
        """Send a bracketed command: START marker, the command, END marker (separate lines).

        Separate lines (not a single `;`-joined one-liner) match the proven iseevy_truth.py
        pattern that actually reaches the decoder shell.
        """
        await self._send_line(f"echo ###{marker}_START###")
        await asyncio.sleep(0.3)
        await self._send_line(cmd)
        await asyncio.sleep(0.5)
        await self._send_line(f"echo ###{marker}_END###")
        await asyncio.sleep(0.3)

    async def _collect(self, marker: str, timeout: int = 12) -> str:
        start, end = f"###{marker}_START###", f"###{marker}_END###"
        for _ in range(timeout * 4):
            buf = b"".join(self._capture).decode("latin-1", "replace")
            if start in buf and end in buf:
                seg = buf.split(start, 1)[1].split(end, 1)[0]
                seg = seg.split("\n", 1)[-1] if "\n" in seg else seg
                return seg.strip()
            await asyncio.sleep(0.25)
        return b"".join(self._capture).decode("latin-1", "replace")[-2000:]

    async def run(self, cmd: str, marker: str = "STEP", timeout: int = 12) -> str:
        """Run one command, return text captured between markers. Flood-proof."""
        self._capture.clear()
        await self._send_cmd(cmd, marker)
        return await self._collect(marker, timeout)

    @staticmethod
    def _clean_cfg_lines(text: str) -> list[str]:
        """Keep only real key=value lines; drop echoed commands, markers, console noise.

        Needed because the shell echoes the typed command and the flood/markers appear in the
        capture. Writing those back into cfg.ini would corrupt the device config.
        """
        out: list[str] = []
        for ln in text.splitlines():
            s = ln.strip()
            if not s or s.startswith(("#", "echo", "cat ")) or "###" in s:
                continue
            if "=" in s and s[0].isalpha():
                out.append(s)
        return out

    async def get_rtsp_peer(self) -> Optional[str]:
        """Return the ESTABLISHED RTSP peer IP (ground truth of current stream)."""
        out = await self.run("netstat -an | grep 554 | grep ESTABLISHED", marker="NET")
        for line in out.splitlines():
            m = re.search(r"(\d+\.\d+\.\d+\.\d+):554\s+ESTABLISHED", line)
            if m:
                return m.group(1)
        return None

    async def read_cfg_ini(self) -> str:
        raw = await self.run("cat /mnt/cfg.ini", marker="CFG")
        return "\n".join(self._clean_cfg_lines(raw))

    async def read_pro_ini(self) -> str:
        """App output file = ground truth for the CURRENT stream (curplay_title/curplay_url)."""
        raw = await self.run("cat /mnt/pro.ini", marker="PRO")
        return "\n".join(self._clean_cfg_lines(raw))

    async def write_cfg_ini(self, text: str) -> bool:
        """Write cfg.ini preserving ALL fields. Caller supplies the FULL corrected file."""
        self._capture.clear()
        self._writer.write(b"cat > /mnt/cfg.ini <<'EOF'\r\n")
        await self._writer.drain()
        for ln in text.splitlines():
            self._writer.write((ln + "\r\n").encode())
            await self._writer.drain()
        self._writer.write(b"EOF\r\n")
        await self._writer.drain()
        await asyncio.sleep(1.0)
        return True

    async def set_cfg_field(self, field: str, value: str, reboot: bool = False) -> bool:
        """SAFE: read cfg.ini, change ONE field, preserve everything else, write back.

        NO reboot by default — cfg.ini changes are applied live (verified: get.cgi reflects the
        new value immediately and the UI updates without reboot). Pass reboot=True only for
        settings that the app reads solely at boot (e.g. network/DHCP changes).
        NEVER touches /set.cgi. field/value example: ('volume', '20').
        """
        raw = await self.read_cfg_ini()
        lines = self._clean_cfg_lines(raw)
        found = False
        for i, ln in enumerate(lines):
            if ln.startswith(f"{field}="):
                lines[i] = f"{field}={value}"
                found = True
                break
        if not found:
            lines.append(f"{field}={value}")
        new_cfg = "\n".join(lines) + "\n"
        await self.write_cfg_ini(new_cfg)
        if reboot:
            await self.reboot()
        return True

    async def reboot(self) -> None:
        await self._send_line("reboot")
        await asyncio.sleep(1.0)

    async def close(self) -> None:
        if self._writer is not None:
            try:
                # Re-break to shell so the decoder stays in its good external state.
                self._writer.write(b"\x03\x03")
                await self._writer.drain()
            except Exception:
                pass
        if self._task:
            self._task.cancel()
        if self._writer:
            try:
                self._writer.close()
            except Exception:
                pass
