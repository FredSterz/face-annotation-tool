# Face Annotation Tool

A lightweight PySide6 (Qt) desktop application for annotating facial keypoints and bounding boxes in video frame sequences. The app supports per-keypoint editing, interactive bounding-box handles, Add/Delete bbox workflows, a crop preview, and fast keyboard-driven replacement modes.

## Features

- Visual annotation canvas with pan and zoom, centered on the mouse cursor.
- Interactive bounding boxes with 8 resize handles.
- Per-keypoint draggable markers and live synchronization with the details panel.
- Add Bbox mode: drag to draw a new bbox, then place all 5 keypoints.
- Del Bbox mode: remove the selected bbox and its 5 associated keypoints.
- Per-keypoint Replace mode and Replace All sequential replacement mode.
- 1-pixel-accurate crop preview with nearest-neighbor scaling.
- Per-video COCO-style save/load under `data/<video_title>/annotations.json`.
- Keyboard shortcuts for frame navigation, bbox cycling, editing, saving, and help.

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
- `gui/main_window.py` - loads the chosen video folder, coordinates add/delete/replace modes, save validation, crop preview, and keyboard shortcuts.
- `gui/annotation_canvas.py` - QGraphicsView-based canvas with bbox selection, resize, drag support, add-bbox drawing, and keypoint placement.
- `graphics/bbox_item.py` - interactive bounding-box item, resize handles, and selected-state styling.
- `graphics/keypoint_item.py` - keypoint graphics items, semantic names/colors, and active-keypoint highlighting.
- `widgets/annotation_details_panel.py` - numeric editors, Add/Del bbox buttons, and Replace buttons.
- `models/coco_loader.py` - simple loader for COCO-style annotations.

## Usage

Create and activate your Python environment, then install dependencies:

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

The app reads and writes to:

- `data/<video_title>/frames/`
- `data/<video_title>/annotations.json`

## Data layout

Place your frames and annotations for a video under `data/<video_title>/`:

```
data/<video_title>/
├─ frames/           # .jpg frames
└─ annotations.json   # COCO-style file for the frames
```

The `annotations.json` file keeps the COCO-style top-level keys used by the app:

- `images`
- `annotations`
- `categories`

Each annotation stores the face bbox plus 5 keypoints and metadata such as `area`, `iscrowd`, `confidence`, and `num_keypoints`.

## Keyboard Shortcuts

- `W` / `S` move to previous / next frame.
- `Tab` cycles to the next bbox in the current frame.
- `B` triggers Add Bbox.
- `Delete` triggers Del Bbox.
- `R` triggers Replace All.
- `C` toggles Edit Keypoints.
- `V` toggles Edit Bounding Box.
- `Ctrl+S` triggers Save Annotations.
- `E` exits the current mode when replacing keypoints or adding a bbox.
- `I` opens the shortcut help dialog.

## Editing Workflow

- Add Bbox: click the button or press `B`, drag a rectangle, then press `E` or click Add Bbox again to commit it.
- After Add Bbox commits, Replace All starts automatically so you can place all 5 keypoints.
- Del Bbox removes the selected bbox and its 5 keypoints from memory.
- Save only writes to the JSON file when the current annotations are complete.
- If a bbox was added but not all 5 keypoints are placed, Save shows an error and does not write the file.

## Notes for developers

- The app uses Qt signals extensively; raw dictionaries are passed with `Signal(object)` to avoid implicit copying of annotation data.
- The canvas keeps keypoint rendering at true single-pixel markers for accuracy.
- Selected bboxes are highlighted with a contrasting outline so selection is clear during edit and replace operations.
- The UI hint below the canvas changes with the current mode and the shortcut help dialog is available with `I`.

## Current Status

- Headless/offscreen validation has been used for save/load, replace flows, add/delete bbox behavior, and shortcut handling.
- The app currently focuses on fast manual annotation of facial bboxes and 5 semantic keypoints per face.

## Contact

If you want help extending the tool or integrating with a different annotation format, open an issue or contact the maintainer.
