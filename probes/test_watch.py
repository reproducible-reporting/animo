# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Live preview: typst serves and reloads the HTML itself*.

Animo ships nothing for live preview because typst already does it.
What it owes in return is that the deck's state survives a reload,
which it does because the injected reload is a plain `location.reload()`
and the fragment survives that.
"""

import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from harness import ROOT, TypstRunner

RELOAD_SCRIPT = 'new EventSource("/__events").addEventListener("reload", () => location.reload())'


def free_port() -> int:
    """A port nothing is listening on, so that two runs cannot collide."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def serve(source: Path, output: Path, port: int) -> subprocess.Popen:
    """Start `typst watch` on a document and return the process."""
    return subprocess.Popen(
        [
            "typst",
            "watch",
            "--root",
            str(ROOT),
            "--ignore-system-fonts",
            "--features",
            "html",
            "--format",
            "html",
            "--port",
            str(port),
            str(source),
            str(output),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def fetch(port: int, attempts: int = 100) -> str:
    """Fetch the served document, waiting for the server to come up."""
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1) as response:
                return response.read().decode()
        except urllib.error.URLError, ConnectionError, TimeoutError:
            time.sleep(0.1)
    raise AssertionError(f"typst watch did not serve anything on port {port}")


@pytest.mark.parametrize("flag", ["--port", "--no-serve", "--no-reload"])
def test_the_server_flags_exist(flag):
    """The three flags the manual has to be able to mention."""
    proc = subprocess.run(["typst", "watch", "--help"], capture_output=True, text=True, check=True)
    assert flag in proc.stdout


def test_the_reload_script_is_injected_into_the_served_document_only(typst: TypstRunner):
    """The file written to disk never contains the script, so a published deck is clean.

    And because the reload is a plain `location.reload()`, the URL survives it,
    fragment included, so a deck whose subslide lives in `location.hash`
    comes back on the same subslide after every recompile.
    """
    source = typst.source("Hello watch\n")
    output = typst.scratch / "watched.html"
    port = free_port()
    process = serve(source, output, port)
    try:
        served = fetch(port)
    finally:
        process.terminate()
        process.wait(timeout=20)
    assert RELOAD_SCRIPT in served
    assert "</body>" in served
    assert served.index(RELOAD_SCRIPT) < served.index("</body>")
    assert RELOAD_SCRIPT not in output.read_text()
