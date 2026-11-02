#!/usr/bin/env python3
"""
brain_chat_backend.py - Gestor de ciclo de vida de llama-server y conector de streaming.
Garantiza arranque rápido (<1s) y apagado 100% limpio sin procesos residuales.
"""

import os
import sys
import time
import atexit
import signal
import json
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from brain_common import get_brain_home

SERVER_PORT = 8089
SERVER_HOST = "127.0.0.1"


class LlamaServerManager:
    def __init__(self, port: int = SERVER_PORT):
        self.port = port
        self.host = SERVER_HOST
        self.process = None
        self.base_url = f"http://{self.host}:{self.port}"
        atexit.register(self.stop)

    def is_running(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/health", method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def start(self, progress_callback=None) -> bool:
        if self.is_running():
            return True

        brain_home = get_brain_home()
        bin_dir = brain_home / "tools" / "bin"
        server_exe = bin_dir / "llama-server.exe"
        if not server_exe.exists():
            server_exe = bin_dir / "llama-server"

        model_file = bin_dir / "qwen2.5-1.5b-instruct-q4_k_m.gguf"

        if not server_exe.exists() or not model_file.exists():
            raise FileNotFoundError(f"Binario ({server_exe.name}) o modelo ({model_file.name}) no encontrados en {bin_dir}.")

        if progress_callback:
            progress_callback("Iniciando motor llama.cpp...")

        cmd = [
            str(server_exe),
            "-m", str(model_file),
            "--host", self.host,
            "--port", str(self.port),
            "-c", "4096",
            "--n-predict", "1024",
            "-ngl", "99",
            "--no-warmup",
            "-t", "4",
            "--repeat-penalty", "1.15",
            "--repeat-last-n", "64",
            "--presence-penalty", "0.15",
            "--frequency-penalty", "0.20",
            "--log-disable"
        ]

        # En Windows ocultar completamente la ventana de consola
        creationflags = 0
        if sys.platform == "win32":
            creationflags = 0x08000000  # CREATE_NO_WINDOW

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags
        )

        # Esperar a que el servidor esté listo (arranca en ~500ms gracias a mmap / VRAM)
        start_time = time.time()
        while time.time() - start_time < 25.0:
            if self.is_running():
                return True
            time.sleep(0.1)

        return False

    def stop(self):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=1.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

            if sys.platform == "win32" and self.process.pid:
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=0x08000000
                    )
                except Exception:
                    pass

            self.process = None

        if sys.platform == "win32":
            # Garantizar 0 procesos residuales de llama-server en reposo
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", "llama-server.exe"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=0x08000000
                )
            except Exception:
                pass


def stream_chat_completion(messages: list[dict], on_token_callback, port: int = SERVER_PORT):
    """
    Envía mensajes a llama-server y emite los tokens vía streaming.
    """
    url = f"http://{SERVER_HOST}:{port}/v1/chat/completions"
    payload = {
        "messages": messages,
        "temperature": 0.3,
        "top_p": 0.85,
        "repeat_penalty": 1.15,
        "repeat_last_n": 64,
        "presence_penalty": 0.15,
        "frequency_penalty": 0.20,
        "stream": True,
        "max_tokens": 1024
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60.0) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            ret = on_token_callback(content)
                            if ret is False:
                                break
                except Exception:
                    continue
    except Exception as e:
        on_token_callback(f"\n[Error en comunicación con el motor local: {e}]")
