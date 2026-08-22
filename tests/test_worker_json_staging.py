from __future__ import annotations

import json
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT.parent))

from astrbot_plugin_help_typst.core import worker


def test_render_stages_json_as_a_file_and_cleans_it(monkeypatch, tmp_path):
    template = tmp_path / "base.typ"
    template.write_text("#let data = json(sys.inputs.json_path)", encoding="utf-8")
    output = tmp_path / "menu.png"
    payload = json.dumps({"plugins": ["x" * 10_000]})
    observed = {}

    def fake_compile(template_path, **kwargs):
        observed["inputs"] = kwargs["sys_inputs"]
        staged = Path(template_path).parent / kwargs["sys_inputs"]["json_path"]
        observed["path"] = staged
        assert staged.read_text(encoding="utf-8") == payload

    monkeypatch.setattr(worker.typst, "compile", fake_compile)
    monkeypatch.setattr(worker, "process_image_to_webp", lambda **_kwargs: ["ok.webp"])

    result = worker.execute_render_task(
        worker.RenderTask(
            template_path=str(template),
            font_paths=[],
            json_str=payload,
            output_png_path=str(output),
            output_dir=str(tmp_path),
            timestamp="now",
            query=None,
            is_temp=True,
            req_id="request",
        )
    )

    assert result == ["ok.webp"]
    assert "json_string" not in observed["inputs"]
    assert not observed["path"].exists()
