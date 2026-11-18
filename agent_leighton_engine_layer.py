"""
agent_leighton_engine_layer.py — leighton-engine-layer's agent: it knows, checks and reports on itself

Function:
    leighton-engine-layer's agent (agent-layer SPEC.md 0.1.0). It reads this
    repository's card from its own headers; checks its git state, its
    tests, VERSION against the CHANGELOG, dev markers, its sealed
    capsules, its archive and its file names; checks the siblings it
    depends on; and reports what needs James. It never edits, commits,
    pushes, signs or seals anything. The runtime is ../agent-layer/agent.py.

    python agent_leighton_engine_layer.py [--no-tests] [--json]

Public API:
    1. DECLARATION — what this agent is and watches

Tier:     the Agent runtime (agent-layer), for P14 — Leighton Engine, V3
Depends:  ../agent-layer/agent.py
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RUNTIME = os.path.join(os.path.dirname(_HERE), "agent-layer")
if _RUNTIME not in sys.path:
    sys.path.insert(0, _RUNTIME)

# 1. DECLARATION
DECLARATION = {
    "repo": "leighton-engine-layer",
    "role": "P14 — Leighton Engine, V3",
    "main": ["leighton_engine_v3.py"],
    "tests": True,
    "watches": ["leighton_engine_v3.py"],
    "may_propose": True,
}

if __name__ == "__main__":
    import agent
    sys.exit(agent.main(_HERE, DECLARATION, sys.argv[1:]))
