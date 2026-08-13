import ctypes
import gc
import platform
import re
import tempfile
import traceback
from dataclasses import dataclass
from pathlib import Path

import typst

from ..domain import DefaultCFG
from ..utils import process_image_to_webp


def force_memory_release():
    # Python 层
    gc.collect()

    # glibc 层
    if platform.system() == "Linux":
        try:
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
        except Exception:
            pass


@dataclass
class RenderTask:
    template_path: str
    font_paths: list[str]
    json_str: str
    output_png_path: str
    output_dir: str
    timestamp: str
    query: str | None
    is_temp: bool
    req_id: str
    webp_limit: int = DefaultCFG.LIMIT_WEBP
    split_height: int = DefaultCFG.LIMIT_SIDE
    ppi: float = DefaultCFG.LIMIT_PPI


def execute_render_task(task: RenderTask) -> list[str]:
    """渲染子进程"""
    staged_json_path: Path | None = None
    try:
        # 1. 准备参数
        template_dir = Path(task.template_path).parent
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=".help_typst_",
            suffix=".json",
            dir=template_dir,
            delete=False,
        ) as staged_json:
            staged_json.write(task.json_str)
            staged_json_path = Path(staged_json.name)

        sys_inputs = {
            "json_path": staged_json_path.name,
            "timestamp": task.timestamp,
        }
        if task.query:
            sys_inputs["query_regex"] = re.escape(task.query)

        # 2. 执行 Typst 编译
        typst.compile(
            task.template_path,
            output=task.output_png_path,
            font_paths=task.font_paths,
            format="png",
            ppi=task.ppi,
            sys_inputs=sys_inputs,
        )

        # 3. 调用图片处理
        # 计算文件名 stem
        src_path = Path(task.output_png_path)
        final_stem = f"temp_{task.req_id}" if task.is_temp else src_path.stem

        return process_image_to_webp(
            source_path=task.output_png_path,
            output_dir=task.output_dir,
            stem_name=final_stem,
            webp_limit=task.webp_limit,
            split_height=task.split_height,
        )

    except Exception:
        return [f"ERROR: {traceback.format_exc()}"]

    finally:
        if staged_json_path:
            try:
                staged_json_path.unlink(missing_ok=True)
            except OSError:
                pass

        # 4. 强制内存回收
        force_memory_release()
