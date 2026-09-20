#!/usr/bin/env bash
# macOS / Ubuntu: install Antigravalgia (see antigravalgia/install).
cd "$(dirname "$0")" && exec python3 -m antigravalgia.install "$@"
