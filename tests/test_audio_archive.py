from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_site  # noqa: E402


class AudioArchiveTests(unittest.TestCase):
    def test_discover_audio_exports_lyrics_and_optional_metadata(self) -> None:
        lyrics = "İlk dize.\\nİkinci dize.\\n\\nYeni kıta."
        with tempfile.TemporaryDirectory() as directory:
            audio_root = Path(directory)
            relative = Path("Marşlar") / "Türklerin Marşları" / "Deneme.mp3"
            source = audio_root / relative
            source.parent.mkdir(parents=True)
            source.write_bytes(b"test audio placeholder")
            (audio_root / "_metadata.json").write_text(
                json.dumps({
                    "audio": {
                        relative.as_posix(): {
                            "title": "Deneme Marşı",
                            "country": "turkish",
                            "category": "Marşlar",
                            "subcategory": "Türklerin Marşları",
                            "archive_type": "marches",
                            "lyrics": lyrics,
                            "performer": "Deneme Korosu",
                            "language": "tr",
                            "order": 1,
                        }
                    }
                }, ensure_ascii=False),
                encoding="utf-8",
            )

            with patch.object(build_site, "AUDIO_ROOT", audio_root):
                result = build_site.discover_audio()

        self.assertEqual(len(result["audio"]), 1)
        record = result["audio"][0]
        self.assertEqual(record["archive_type"], "marches")
        self.assertEqual(record["lyrics"], lyrics)
        self.assertEqual(record["performer"], "Deneme Korosu")
        self.assertEqual(record["language"], "tr")


if __name__ == "__main__":
    unittest.main()
