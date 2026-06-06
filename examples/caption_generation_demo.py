from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    caption_for_m_matrix,
    caption_for_v_vector,
    caption_for_shot_scaling,
    caption_for_matching_failure,
    save_captions,
)

print("AZM-QOS v2.2 Caption Generation Demo")
print("=" * 70)

captions = [
    caption_for_m_matrix(),
    caption_for_v_vector(),
    caption_for_shot_scaling(),
    caption_for_matching_failure(),
]

out_dir = ROOT / "outputs" / "caption_generation_demo"
artifacts = save_captions(captions, out_dir)

for caption in captions:
    print(caption.markdown())
    print()

print("Saved captions:")
for key, value in artifacts.items():
    print(f"  {key}: {value}")
