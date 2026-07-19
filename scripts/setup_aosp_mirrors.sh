#!/usr/bin/env bash
# setup_aosp_mirrors.sh — Configure AOSP source mirror for use within mainland China.
#
# Rewrites https://android.googlesource.com/ to a domestic mirror via
# `git config --global url.<mirror>.insteadOf`, so that `repo sync` works
# without VPN. Also exports REPO_URL pointing to a GitHub mirror of the
# repo tool itself (gerrit.googlesource.com is also blocked).
#
# Usage:
#   bash scripts/setup_aosp_mirrors.sh                 # default: USTC mirror
#   AOSP_MIRROR=tuna bash scripts/setup_aosp_mirrors.sh
#   AOSP_MIRROR=none bash scripts/setup_aosp_mirrors.sh  # clear rewrite, use source
#
# Designed to run inside build_twrp_selfhosted.yml before `repo init`.

set -euo pipefail

AOSP_MIRROR="${AOSP_MIRROR:-ustc}"
AOSP_MIRROR=$(echo "$AOSP_MIRROR" | tr '[:upper:]' '[:lower:]')

case "$AOSP_MIRROR" in
  ustc)
    MIRROR_URL="https://mirrors.ustc.edu.cn/aosp/"
    ;;
  tuna)
    MIRROR_URL="https://aosp.tuna.tsinghua.edu.cn/"
    ;;
  none)
    # Clear any existing insteadOf rules for known mirrors, then exit.
    git config --global --unset-all url."https://mirrors.ustc.edu.cn/aosp/".insteadOf 2>/dev/null || true
    git config --global --unset-all url."https://aosp.tuna.tsinghua.edu.cn/".insteadOf 2>/dev/null || true
    echo "AOSP_MIRROR=none, using source googlesource directly"
    exit 0
    ;;
  *)
    echo "Unknown AOSP_MIRROR: $AOSP_MIRROR, supported: ustc|tuna|none" >&2
    exit 1
    ;;
esac

# Idempotent: clear both mirrors first, then set the chosen one.
git config --global --unset-all url."https://mirrors.ustc.edu.cn/aosp/".insteadOf 2>/dev/null || true
git config --global --unset-all url."https://aosp.tuna.tsinghua.edu.cn/".insteadOf 2>/dev/null || true
git config --global url."${MIRROR_URL}".insteadOf "https://android.googlesource.com/"

# repo tool itself: gerrit.googlesource.com is also blocked in mainland China.
export REPO_URL="https://github.com/GerritCodeReview/git-repo"

echo "AOSP_MIRROR=${AOSP_MIRROR}"
echo "Mirror URL: ${MIRROR_URL}"
echo "REPO_URL=${REPO_URL}"
echo "--- git config url.*.insteadOf ---"
git config --global --get-regexp 'url\..*\.insteadof' || echo "(no insteadOf rules)"

# Reachability check (non-blocking).
echo "--- mirror reachability ---"
curl -sS --max-time 10 -o /dev/null -w "HTTP %{http_code}\n" "${MIRROR_URL}" || echo "(network check skipped or failed)"
