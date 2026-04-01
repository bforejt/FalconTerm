#!/bin/bash
# FalconTerm — GitHub repo initialization
# Run this from the directory containing the project files.
#
# Prerequisites:
#   - gh CLI installed and authenticated (brew install gh && gh auth login)
#   - git configured with your identity

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "==> Creating GitHub repo: bforejt/FalconTerm"
gh repo create bforejt/FalconTerm \
    --public \
    --description "Native macOS SSH terminal for Apple Silicon — SwiftUI + SwiftTerm + SwiftNIO SSH" \
    --license apache-2.0 \
    --clone=false

echo "==> Initializing local git repo"
git init
git branch -M main

echo "==> Adding remote"
git remote add origin git@github.com:bforejt/FalconTerm.git

echo "==> Initial commit"
git add -A
git commit -m "Initial scaffold: Package.swift, app entry point, SSHEngine/SessionManager stubs

- SwiftUI app shell with menu commands
- SSHEngine module with connection config types
- SessionManager module with Codable session profiles
- SwiftTerm, SwiftNIO SSH, SwiftNIO, ArgumentParser dependencies
- MIT license, README with architecture overview and roadmap"

echo "==> Pushing to GitHub"
git push -u origin main

echo ""
echo "Done! https://github.com/bforejt/FalconTerm"
