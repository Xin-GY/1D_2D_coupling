from __future__ import annotations

from pathlib import Path

from scripts._plot_common import ensure_plot_dir, plt, save_figure


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    plot_dir = ensure_plot_dir(root)
    fig, ax = plt.subplots(figsize=(10, 3.8))
    timelines = [
        ('strict', [0.5, 1.0, 1.5, 2.0, 2.5], '#355070'),
        ('yield', [0.8, 1.6, 2.4, 3.2, 4.0], '#6d597a'),
        ('fixed 5 s', [5.0, 10.0, 15.0, 20.0], '#b56576'),
    ]
    for idx, (label, events, color) in enumerate(timelines):
        y = 3 - idx
        ax.hlines(y, 0.0, max(events) + 0.5, color='0.75', lw=2)
        for event in events:
            ax.vlines(event, y - 0.18, y + 0.18, color=color, lw=3)
        ax.text(-0.2, y, label, ha='right', va='center')
    ax.text(1.1, 3.3, 'exchange events', color='#355070')
    ax.annotate('', xy=(0.5, 3.15), xytext=(1.0, 3.28), arrowprops=dict(arrowstyle='->', color='#355070'))
    ax.set_ylim(0.5, 3.5)
    ax.set_xlim(0.0, 20.5)
    ax.set_xlabel('time')
    ax.set_yticks([])
    save_figure(fig, plot_dir / 'scheduler_timeline_schematic.png')


if __name__ == '__main__':
    main()
