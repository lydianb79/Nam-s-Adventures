#!/bin/zsh
# Batch-mode build of the native macOS (Metal) app into Build/.
cd "$(dirname "$0")/.."
UNITY="/Applications/Unity/Hub/Editor/6000.6.9f1/Unity.app/Contents/MacOS/Unity"
LOG="${1:-Logs/build.log}"
"$UNITY" -batchmode -quit -projectPath "$PWD" -executeMethod BuildTools.BuildMac -logFile "$LOG"
code=$?
grep -E "error CS|BUILD_RESULT" "$LOG"
exit $code
