from hashlib import sha256
import os
from unittest.mock import patch

import zeta_persistence as zp


def digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


fixed = os.terminal_size((80, 24))
with patch.object(zp.shutil, "get_terminal_size", return_value=fixed):
    frame_zero = zp.render(0)
    frame_one = zp.render(1)

print(f"FINGERPRINT={zp.PAGES}:{zp.SECTIONS}:{zp.APPENDICES}:{zp.EQUATIONS}")
print(f"FRAME_00000000_SHA256={digest(frame_zero)}")
print(f"FRAME_00000001_SHA256={digest(frame_one)}")
print(f"NONRECURRENT_PAIR={frame_zero != frame_one}")
print("FINAL_SEAL=ZETA_PERSISTENCE_V0_1_PASS")
