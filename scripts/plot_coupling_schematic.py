from __future__ import annotations

from pathlib import Path

from scripts._plot_common import ensure_plot_dir, plt, save_figure


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    plot_dir = ensure_plot_dir(root)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5), sharey=True)
    titles = ['Frontal', 'Lateral', 'Mixed']
    for ax, title in zip(axes, titles):
        ax.set_title(title)
        ax.add_patch(plt.Rectangle((0.05, 0.42), 0.90, 0.16, facecolor='#4a6fa5', alpha=0.9))
        ax.text(0.50, 0.50, '1D River', color='white', ha='center', va='center', fontsize=11)
        ax.add_patch(plt.Rectangle((0.08, 0.06), 0.84, 0.26, facecolor='#c6d9f1', alpha=0.95))
        ax.text(0.50, 0.18, '2D Floodplain', ha='center', va='center', fontsize=10)
        if title in {'Lateral', 'Mixed'}:
            ax.plot([0.35, 0.65], [0.40, 0.40], color='#b85c38', lw=4)
            ax.annotate('', xy=(0.52, 0.34), xytext=(0.48, 0.42), arrowprops=dict(arrowstyle='->', color='#b85c38', lw=2))
            ax.annotate('', xy=(0.42, 0.44), xytext=(0.46, 0.34), arrowprops=dict(arrowstyle='->', color='#7c3f58', lw=2))
            ax.text(0.50, 0.31, 'weir Qex', ha='center', fontsize=9)
        if title in {'Frontal', 'Mixed'}:
            ax.plot([0.92, 0.92], [0.32, 0.68], color='#355070', lw=4)
            ax.annotate('', xy=(0.91, 0.56), xytext=(0.82, 0.56), arrowprops=dict(arrowstyle='->', color='#355070', lw=2))
            ax.text(0.77, 0.60, 'Q from 1D', fontsize=9)
            ax.annotate('', xy=(0.82, 0.47), xytext=(0.91, 0.47), arrowprops=dict(arrowstyle='->', color='#6d597a', lw=2))
            ax.text(0.75, 0.41, 'stage from 2D', fontsize=9)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
    save_figure(fig, plot_dir / 'coupling_schematic.png')


if __name__ == '__main__':
    main()
