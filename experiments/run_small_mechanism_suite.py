from __future__ import annotations

from pathlib import Path

from coupling.runtime_env import repair_anuga_editable_build_env

repair_anuga_editable_build_env()

from experiments.chapter_suite import parse_args, run_chapter_analysis


def main() -> None:
    args = parse_args()
    run_chapter_analysis(
        output_root=Path(args.output_root),
        profile=args.profile,
        include_test7=False,
        include_small=True,
        allow_download=False,
        run_mesh=False,
        generate_plots=False,
    )


if __name__ == '__main__':
    main()
