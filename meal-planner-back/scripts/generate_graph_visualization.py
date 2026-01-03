"""
Generate visual representation of the meal planner agent graph.

This script creates three types of graph visualizations:
1. PNG image (using matplotlib backend)
2. Mermaid source code (for GitHub rendering)
3. ASCII text fallback (for terminals)

Usage:
    python scripts/generate_graph_visualization.py

Output:
    - docs/agent_graph.png (PNG visualization)
    - docs/agent_graph.mmd (Mermaid source)
    - docs/agent_graph.txt (ASCII fallback)

Requirements:
    - pygraphviz>=1.11
    - matplotlib>=3.8.0
    - pillow>=10.0.0
    - graphviz (system package)
"""

import os
import sys
from pathlib import Path

# Fix Windows console encoding for emoji support
if sys.platform == "win32":
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass  # Fallback to default encoding

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agents.graphs.main_graph import create_main_graph


def main():
    """Main execution function"""
    # Create output directory
    output_dir = project_root / "docs"
    output_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("Meal Planner Agent Graph Visualization")
    print("=" * 60)
    print()

    # Create graph instance
    print("📊 Creating meal planner graph...")
    try:
        graph = create_main_graph()
        graph_repr = graph.get_graph()
        print("✅ Graph created successfully\n")
    except Exception as e:
        print(f"❌ Failed to create graph: {e}")
        return 1

    # Generate PNG visualization
    output_path_png = output_dir / "agent_graph.png"
    print(f"🎨 Generating PNG visualization: {output_path_png}")

    # Try multiple PNG generation methods
    png_generated = False

    for method in ["api", "pyppeteer"]:
        if png_generated:
            break

        try:
            print(f"   Trying method: {method}")
            png_data = graph_repr.draw_mermaid_png(
                draw_method=method,
                output_file_path=str(output_path_png)
            )
            print(f"✅ PNG saved: {output_path_png}")
            file_size = output_path_png.stat().st_size / 1024  # KB
            print(f"   Size: {file_size:.1f} KB")
            print(f"   Method: {method}\n")
            png_generated = True
        except Exception as e:
            print(f"   {method} failed: {e}")

    if not png_generated:
        print("⚠️  PNG generation failed with all methods")
        print("   This is expected - will use Mermaid for GitHub rendering\n")

        # Generate ASCII fallback instead
        print("📝 Generating ASCII fallback...")
        try:
            ascii_graph = graph_repr.draw_ascii()
            ascii_path = output_dir / "agent_graph.txt"
            ascii_path.write_text(ascii_graph, encoding="utf-8")
            print(f"✅ ASCII saved: {ascii_path}\n")
        except Exception as e2:
            print(f"   ASCII generation also failed: {e2}")
            print("   (This is OK - Mermaid diagram is the primary output)\n")

    # Generate Mermaid markdown
    mermaid_path = output_dir / "agent_graph.mmd"
    print(f"📐 Generating Mermaid source: {mermaid_path}")

    try:
        mermaid_code = graph_repr.draw_mermaid()
        mermaid_content = f"""# Meal Planner Agent Graph (Mermaid)

This file contains the Mermaid diagram source code for the agent graph.
It will render automatically on GitHub.

```mermaid
{mermaid_code}
```

## Legend

- **Blue nodes**: Supervisor nodes (Send API for parallel execution)
- **Green nodes**: Expert agents (LLM-powered)
- **Yellow nodes**: Validators (rule-based)
- **Orange nodes**: Routing/control flow
- **Dashed edges**: Conditional routes

## Node Descriptions

### Supervisors
- `meal_planning_supervisor`: Dispatches 3 expert agents in parallel
- `validation_supervisor`: Dispatches 5 validators in parallel

### Expert Agents
- `nutritionist`: Macro-focused meal recommendations
- `chef`: Cooking skill & time-based recommendations
- `budget`: Cost-optimized recommendations with real pricing

### Validators
- `nutrition_checker`: Verifies calories (±20%) and macros (±30%)
- `allergy_checker`: Checks dietary restrictions
- `time_checker`: Validates cooking time limits
- `health_checker`: Enforces health condition constraints
- `budget_checker`: Ensures budget compliance (±10%)

### Control Flow
- `decision_maker`: Routes to retry or next meal
- `retry_router`: Selectively re-runs failed experts
- `day_iterator`: Advances to next meal or day
"""
        mermaid_path.write_text(mermaid_content, encoding="utf-8")
        print(f"✅ Mermaid saved: {mermaid_path}")
        print(f"   Lines: {len(mermaid_code.splitlines())}\n")
    except Exception as e:
        print(f"❌ Mermaid generation failed: {e}\n")

    # Summary
    print("=" * 60)
    print("✨ Visualization Complete")
    print("=" * 60)
    print()
    print("Generated files:")

    if output_path_png.exists():
        print(f"  📊 PNG: {output_path_png}")
        print("     Use in README: ![Graph](docs/agent_graph.png)")

    if mermaid_path.exists():
        print(f"  📐 Mermaid: {mermaid_path}")
        print("     Renders automatically on GitHub")

    ascii_path = output_dir / "agent_graph.txt"
    if ascii_path.exists():
        print(f"  📝 ASCII: {ascii_path}")
        print("     Fallback for terminals")

    print()
    print("Next steps:")
    print("  1. Verify PNG quality (should be >1200px wide)")
    print("  2. Insert into README after 'Technical Architecture' section")
    print("  3. Commit visualization files to repository")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
