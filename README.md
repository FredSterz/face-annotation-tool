# Face Annotation Tool

A lightweight PySide6 (Qt) desktop application for annotating facial keypoints and bounding boxes in video frame sequences. The tool supports per-keypoint editing, interactive bounding-box handles, a crop preview, and "Replace" workflows for updating keypoints quickly.

## Features

- Visual annotation canvas with pan & zoom (mouse wheel centered on cursor).
- Interactive bounding boxes with 8 resize handles.
- Per-keypoint draggable markers and live synchronization with the details panel.
- Per-keypoint "Replace" (point-and-click) and "Replace All" sequential replacement modes.
- Keyboard navigation during Replace-All: `E` advances, `Q` steps back. `E` exits single-key Replace.
- 1-pixel-accurate crop preview with nearest-neighbor scaling to avoid blurring.
- Save/load COCO-style `annotations.json` per video folder.
- Project data organized under `data/<video_title>/` with `frames/` and `annotations.json`.

## Repo layout

Root:

```
.
├─ data/                        # Video folders (each contains frames/ and annotations.json)
├─ gui/                         # Main window and canvas
├─ graphics/                    # QGraphics items (bbox, keypoint)
├─ models/                      # Annotation loader (COCO)
├─ widgets/                     # Right-hand annotation details panel
├─ main.py                      # App entrypoint (accepts optional video title)
├─ requirements.txt
└─ README.md
```

Important files:

- `main.py` - application entrypoint. Accepts an optional positional `video_title` argument.
- `gui/main_window.py` - main window and wiring between canvas and details panel.
- `gui/annotation_canvas.py` - QGraphicsView-based canvas, keypoint and bbox rendering & interaction.
- `graphics/bbox_item.py` - interactive bounding-box item and resize handles.
- `graphics/keypoint_item.py` - keypoint graphics items and colors.
- `widgets/annotation_details_panel.py` - numeric editors and Replace buttons.
- `models/coco_loader.py` - simple loader for COCO-style annotations.

## Usage

Create/activate your Python environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the app for a specific video (folder name under `data/`):

```bash
python main.py scene1
```

If no `video_title` is provided, the first folder under `data/` will be used.

## Data layout

Place your frames and annotations for a video under `data/<video_title>/`:

```
data/<video_title>/
├─ frames/           # .jpg frames
└─ annotations.json   # COCO-style file for the frames
```

## Notes for developers

- The app uses Qt signals extensively; be careful passing raw dictionaries across Qt signals — this code uses `Signal(object)` to avoid implicit copying of annotation dicts.
- The canvas keeps keypoint rendering at true single-pixel markers for accuracy.
- UI text for Replace modes is shown below the canvas and is updated centrally from `gui/main_window.py`.

## Next steps / TODOs

- Add tests and CI to validate headless (offscreen) behaviors.
- Add an explicit export/backup command for annotations.
- Add undo/redo for small edits.

## Contact

If you want help extending the tool or integrating with a different annotation format, open an issue or contact the maintainer.
