"""CLI entry point.

  python main.py "Why did Europe's Electronics sales drop in Q4 2024?"
  python main.py --interactive
  python main.py --samples        # runs sample_questions.txt and stores results in sample_outputs/
"""
import argparse
import sys
from pathlib import Path

import config
from graph import build_graph, run_question


def show(state: dict, verbose: bool):
    if verbose:
        print("\n--- Agent trace ---")
        print("\n".join(state.get("trace", [])))
    print("\n" + state.get("report_markdown", "(no report)"))
    if state.get("chart_files"):
        print(f"\nCharts saved in: {state['output_dir']}")


def main():
    ap = argparse.ArgumentParser(description="Multi-Agent Business Data Analytics Platform")
    ap.add_argument("question", nargs="?", help="Business question in natural language")
    ap.add_argument("--interactive", "-i", action="store_true")
    ap.add_argument("--samples", action="store_true", help="Run all questions in sample_questions.txt")
    ap.add_argument("--verbose", "-v", action="store_true", help="Print the agent trace")
    a = ap.parse_args()

    graph = build_graph()
    if a.samples:
        out_root = config.BASE_DIR / "sample_outputs"
        for q in Path("sample_questions.txt").read_text(encoding="utf-8").splitlines():
            if q.strip():
                print(f"\n=== {q} ===")
                show(run_question(q.strip(), graph, out_root), a.verbose)
    elif a.interactive:
        print("Ask a business question (or 'exit').")
        while (q := input("\n> ").strip()).lower() not in {"exit", "quit"}:
            if q:
                show(run_question(q, graph), a.verbose)
    elif a.question:
        show(run_question(a.question, graph), a.verbose)
    else:
        ap.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
