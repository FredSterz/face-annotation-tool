import sys
import argparse

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main():
    parser = argparse.ArgumentParser(
        description="Face Annotation Tool"
    )
    parser.add_argument(
        "video_title",
        nargs="?",
        help="Video title folder under data/ (for example: scene1)",
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)

    window = MainWindow(video_title=args.video_title)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()