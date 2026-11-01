from pathlib import Path

from wdf.dictionary import render_data_dictionary


ROOT = Path(__file__).resolve().parents[1]
(ROOT / "docs" / "DATA_DICTIONARY.md").write_text(
    render_data_dictionary(), encoding="utf-8", newline="\n"
)
