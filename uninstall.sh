#!/usr/bin/env bash
# macOS / Ubuntu: remove Antigravalgia.
cd "$(dirname "$0")" && exec python3 -m antigravalgia.install uninstall
