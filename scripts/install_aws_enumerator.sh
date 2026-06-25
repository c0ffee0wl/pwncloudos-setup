#!/bin/bash
# Install/update aws-enumerator via `go install` (the project ships no release binaries).
set -e
export GOPROXY="${GOPROXY:-https://proxy.golang.org,direct}"
echo "Installing aws-enumerator via go install..."
go install github.com/shabarkin/aws-enumerator@latest
echo "aws-enumerator installed to $(go env GOPATH 2>/dev/null || echo "$HOME/go")/bin"
