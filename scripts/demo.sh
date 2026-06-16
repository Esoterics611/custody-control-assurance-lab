#!/usr/bin/env bash
# 3-minute interview demo: prove a control holds, regress it, watch the harness
# catch the drift, then restore. Pure CLI — no server required.
#
#   ./scripts/demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."

pause() { echo; read -rp "  ↵ press enter to continue…" _; echo; }

echo "============================================================"
echo "  CUSTODY CONTROL ASSURANCE — live drift demo"
echo "============================================================"

echo
echo "1) BASELINE — validate every control against the reference policy"
pause
uv run python scripts/run_assurance.py
cp reports/assurance.json reports/baseline.json
echo "  (saved this clean run as the drift baseline)"
pause

echo
echo "2) REGRESSION — a change loosens the policy (amount ceiling raised,"
echo "   velocity cap removed). In production this would ship through the"
echo "   admin-quorum-gated change path; here we point the harness at the"
echo "   weakened policy file directly."
pause

echo
echo "3) RE-VALIDATE — same simulations, now against the loosened policy."
echo "   The harness flags regressed controls as DRIFT and exits non-zero:"
pause
set +e
uv run python scripts/run_assurance.py \
    --policy policies/loosened_policy.yaml \
    --baseline reports/baseline.json
echo "  (exit code: $? — CI would fail this build)"
set -e
echo "  Open reports/assurance.html to see the red cells + drift banner."
pause

echo
echo "4) RESTORE — back to the reference policy: all controls green again."
pause
uv run python scripts/run_assurance.py
rm -f reports/baseline.json
echo
echo "  That is the validate → regress → detect → restore loop, automated."
echo "============================================================"
