"""Timeline assembly utilities to align assets for NLE import."""

from __future__ import annotations

import json
import shutil
from tempfile import TemporaryDirectory
from pathlib import Path
from typing import Dict, List

from ..config import ANALYSIS_DIR
from ..schemas import TimelineItem, TimelineRequest, TimelineResponse


def _load_analysis(video_id: str) -> Dict:
    analysis_paths = sorted(ANALYSIS_DIR.glob("analysis_*/metadata.json"), reverse=True)
    for path in analysis_paths:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("video_id") == video_id:
            return data
    raise FileNotFoundError("Analysis metadata not found. Run analysis first.")


def build_timeline(request: TimelineRequest) -> TimelineResponse:
    analysis_data = _load_analysis(request.video_id)
    scenes = analysis_data.get("scenes", [])

    items: List[TimelineItem] = []

    # Video base layer
    items.append(
        TimelineItem(
            asset_type="video",
            path=analysis_data.get("video_path"),
            start=0.0,
            duration=analysis_data["metadata"].get("duration", 0.0),
            metadata={"scenes": scenes},
        )
    )

    # Narration layer spans entire script
    items.append(
        TimelineItem(
            asset_type="narration",
            path=request.narration_path,
            start=0.0,
            duration=analysis_data["metadata"].get("duration", 0.0),
            metadata={"beat_alignment": request.beat_alignment},
        )
    )

    if request.music_path:
        items.append(
            TimelineItem(
                asset_type="music",
                path=request.music_path,
                start=0.0,
                duration=analysis_data["metadata"].get("duration", 0.0),
                metadata={"duck_under_dialogue": True},
            )
        )

    for idx, ambient_path in enumerate(request.ambient_paths, start=1):
        start_time = scenes[idx % len(scenes)]["start_time"] if scenes else 0.0
        items.append(
            TimelineItem(
                asset_type="ambient",
                path=ambient_path,
                start=start_time,
                duration=min(15.0, analysis_data["metadata"].get("duration", 0.0) - start_time),
                metadata={"label": Path(ambient_path).stem},
            )
        )

    export_dir = ANALYSIS_DIR / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    export_path = export_dir / f"{request.video_id}_timeline.json"

    with export_path.open("w", encoding="utf-8") as f:
        json.dump({"video_id": request.video_id, "items": [item.dict() for item in items]}, f, indent=2)

    bundle_path = None
    if request.bundle_assets:
        asset_paths = [request.narration_path]
        if request.music_path:
            asset_paths.append(request.music_path)
        asset_paths.extend(request.ambient_paths)

        with TemporaryDirectory() as tmp_dir:
            staging = Path(tmp_dir)
            timeline_target = staging / export_path.name
            shutil.copy2(export_path, timeline_target)

            assets_dir = staging / "assets"
            assets_dir.mkdir(exist_ok=True)

            for asset in asset_paths:
                source = Path(asset).resolve()
                if not source.exists():
                    continue
                destination = assets_dir / source.name
                shutil.copy2(source, destination)

            archive_base = export_dir / f"{request.video_id}_bundle"
            bundle_file = shutil.make_archive(str(archive_base), "zip", root_dir=staging)
            bundle_path = Path(bundle_file)

    return TimelineResponse(video_id=request.video_id, items=items, export_path=str(export_path), bundle_path=str(bundle_path) if bundle_path else None)

