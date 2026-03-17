from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from experiments.io import read_csv
from scripts._plot_common import blank_image_audit


def test_blank_image_audit_detects_truly_blank_images(tmp_path: Path):
    blank_path = tmp_path / 'blank.png'
    textured_path = tmp_path / 'textured.png'

    Image.fromarray(np.full((200, 300, 3), 255, dtype=np.uint8)).save(blank_path)
    image = np.full((200, 300, 3), 255, dtype=np.uint8)
    image[20:180, 40:260, :] = np.array([180, 200, 230], dtype=np.uint8)
    image[::10, :, :] = 160
    image[:, ::10, :] = 160
    Image.fromarray(image).save(textured_path)

    blank_audit = blank_image_audit(blank_path, is_2d_map=True)
    textured_audit = blank_image_audit(textured_path, is_2d_map=True)

    assert blank_audit['is_approximately_blank']
    assert not textured_audit['is_approximately_blank']


def test_chapter_blank_plot_audit_reports_zero_failures(chapter_analysis_artifacts: Path):
    audit_rows = read_csv(chapter_analysis_artifacts / 'logs' / 'blank_plot_audit.csv')
    assert audit_rows, 'blank plot audit is missing'
    assert all(str(row['is_approximately_blank']).lower() in {'false', '0'} for row in audit_rows)


def test_fastest_exact_blank_plot_audit_reports_zero_failures(fastest_exact_chapter_artifacts: Path):
    audit_rows = read_csv(fastest_exact_chapter_artifacts / 'logs' / 'blank_plot_audit.csv')
    assert audit_rows, 'blank plot audit is missing'
    assert all(str(row['is_approximately_blank']).lower() in {'false', '0'} for row in audit_rows)
