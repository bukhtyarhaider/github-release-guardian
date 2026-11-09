import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

SHA = "a" * 40
OTHER = "b" * 40


def handoff():
    from guardian.release import HANDOFF, handoff as render
    return render({h: "Observed evidence and next action." for h in HANDOFF})
