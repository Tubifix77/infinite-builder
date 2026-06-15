"""
Infinite Builder -- autonomous LLM goldplating loop.
Usage: python main.py "your goal here"
       python main.py "your goal here" --dir D:\\Projects
       python main.py "your goal here" --max 10
"""
import argparse, asyncio
from builder.loop import run

def main():
    parser = argparse.ArgumentParser(description="Infinite Builder")
    parser.add_argument("goal", nargs="+", help="What to build")
    parser.add_argument("--dir", default=r"D:\Projects", help="Output directory")
    parser.add_argument("--max", type=int, default=None, help="Max iterations (default: forever)")
    parser.add_argument("--ollama", action="store_true", help="Enable Ollama as a provider (opt-in)")
    args = parser.parse_args()
    goal = " ".join(args.goal)
    print(f"\n[infinite-builder]")
    print(f"   Goal:   {goal}")
    print(f"   Output: {args.dir}")
    print(f"   Ctrl+C to stop\n")
    try:
        asyncio.run(run(goal=goal, output_dir=args.dir, max_iterations=args.max, use_ollama=args.ollama))
    except KeyboardInterrupt:
        print("\n[stopped]")

if __name__ == "__main__":
    main()
