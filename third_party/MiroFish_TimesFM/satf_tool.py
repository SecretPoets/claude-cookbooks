#!/usr/bin/env python3
"""
SATF Tool — Swarm-Augmented Time Series Forecasting CLI

Run a multi-agent swarm simulation on any business idea or scenario.
Uses Claude API for agent simulation and optional TimesFM for quantitative forecasting.

Usage:
    python satf_tool.py "Your business idea description here"
    python satf_tool.py --file idea.txt
    python satf_tool.py --file idea.txt --agents 10 --rounds 5 --output ./report
    python satf_tool.py --file idea.txt --historical data.csv  # adds TimesFM forecast

Requires:
    - ANTHROPIC_API_KEY environment variable
    - pip install anthropic matplotlib numpy
    - pip install timesfm[torch]  (optional, for quantitative forecasting)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import anthropic
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use("Agg")  # Non-interactive backend for saving charts

MODEL = "claude-sonnet-4-6"
client = anthropic.Anthropic()


# ============================================================
# AGENT GENERATION
# ============================================================


def generate_agents(idea: str, num_agents: int = 8) -> list[dict]:
    """Use Claude to generate diverse, relevant agent personas for the given idea."""
    prompt = f"""Generate {num_agents} expert personas to evaluate this business idea.
Each persona should have a DIFFERENT perspective and natural bias.
Include at least: one industry veteran/skeptic, one investor/VC, one target user,
one competitor/failed founder, one market analyst, and one domain specialist.

Make them realistic — real-sounding names, specific backgrounds, concrete biases.

BUSINESS IDEA:
{idea}

Respond with a JSON array. Each object must have exactly these fields:
- "name": full name
- "role": their professional title/role (keep short)
- "bias": their analytical tendency in 3-5 words
- "background": 1-2 sentences on their specific experience

Return ONLY the JSON array, no other text."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        temperature=0.7,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Extract JSON array from response
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text)


# ============================================================
# SWARM SIMULATION
# ============================================================


def run_swarm_round(
    agents: list[dict],
    idea: str,
    round_num: int,
    previous_debate: list[dict],
    num_rounds: int,
) -> list[dict]:
    """Run one round of swarm debate, collecting each agent's structured response."""
    round_results = []

    debate_history = ""
    if previous_debate:
        debate_history = "\n\n--- PREVIOUS ROUND ARGUMENTS ---\n"
        for entry in previous_debate[-len(agents) :]:
            debate_history += (
                f"\n**{entry['name']}** ({entry['role']}): {entry['argument']}\n"
                f"  Sentiment: {entry['sentiment']}/10 | "
                f"Direction: {entry['direction']}\n"
            )

    for agent in agents:
        prompt = f"""You are {agent["name"]}, a {agent["role"]}.

Background: {agent["background"]}
Your natural analytical bias: {agent["bias"]}

BUSINESS IDEA TO EVALUATE:
{idea}

This is Round {round_num} of {num_rounds} in a multi-expert debate.
{debate_history}

Provide your analysis. If others made good points, you may shift your position.
Stay in character.

Respond in this exact JSON format:
{{
    "argument": "your analysis in 2-3 sentences — be specific, cite reasoning",
    "sentiment": <1-10, where 1=will definitely fail, 10=will definitely succeed>,
    "direction": "UP" or "FLAT" or "DOWN",
    "confidence": <0-100>,
    "key_risk": "single biggest risk you see"
}}"""

        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            temperature=0.8,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text.strip()
        json_match = re.search(r"\{[^{}]*\}", response_text, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                parsed["name"] = agent["name"]
                parsed["role"] = agent["role"]
                parsed["round"] = round_num
                round_results.append(parsed)
                print(
                    f"    {agent['name']:25s} "
                    f"sentiment={parsed['sentiment']}/10  "
                    f"direction={parsed['direction']}"
                )
            except json.JSONDecodeError:
                print(f"    {agent['name']:25s} [parse error, skipping]")
        else:
            print(f"    {agent['name']:25s} [no JSON found, skipping]")

    return round_results


def run_simulation(idea: str, agents: list[dict], num_rounds: int = 5) -> list[dict]:
    """Run the full multi-round swarm simulation."""
    all_results = []

    for round_num in range(1, num_rounds + 1):
        print(f"\n  Round {round_num}/{num_rounds}")
        round_results = run_swarm_round(agents, idea, round_num, all_results, num_rounds)
        all_results.extend(round_results)

    return all_results


# ============================================================
# ANALYSIS
# ============================================================


def compute_trajectories(results: list[dict], agents: list[dict], num_rounds: int) -> dict:
    """Compute sentiment trajectories and consensus metrics."""
    agent_names = [a["name"] for a in agents]
    trajectories = {
        "rounds": list(range(1, num_rounds + 1)),
        "agent_sentiment": {},
        "avg_sentiment": [],
        "weighted_sentiment": [],
        "consensus": [],
        "bullish_ratio": [],
    }

    for name in agent_names:
        trajectories["agent_sentiment"][name] = []

    for r in range(1, num_rounds + 1):
        round_data = [d for d in results if d["round"] == r]
        sentiments = []
        confidences = []

        for name in agent_names:
            agent_data = [d for d in round_data if d["name"] == name]
            if agent_data:
                trajectories["agent_sentiment"][name].append(agent_data[0]["sentiment"])
                sentiments.append(agent_data[0]["sentiment"])
                confidences.append(agent_data[0]["confidence"] / 100.0)

        avg = np.mean(sentiments) if sentiments else 5.0
        weighted = np.average(sentiments, weights=confidences) if sentiments else 5.0
        std = np.std(sentiments) if sentiments else 1.0
        consensus = 1.0 / (1.0 + std)
        bullish = (
            sum(1 for d in round_data if d.get("direction") == "UP") / len(round_data)
            if round_data
            else 0.0
        )

        trajectories["avg_sentiment"].append(avg)
        trajectories["weighted_sentiment"].append(weighted)
        trajectories["consensus"].append(consensus)
        trajectories["bullish_ratio"].append(bullish)

    return trajectories


# ============================================================
# SYNTHESIS
# ============================================================


def generate_synthesis(idea: str, results: list[dict], trajectories: dict, num_rounds: int) -> str:
    """Use Claude to produce the meta-synthesis report."""
    final_round = [d for d in results if d["round"] == num_rounds]
    debate_summary = "\n".join(
        f"- {d['name']} ({d['role']}, sentiment {d['sentiment']}/10, "
        f"direction {d['direction']}): {d['argument']} "
        f"KEY RISK: {d.get('key_risk', 'N/A')}"
        for d in final_round
    )

    prompt = f"""You are a meta-analyst producing a final investment-grade assessment.

BUSINESS IDEA:
{idea}

SWARM SIMULATION RESULTS ({len(final_round)} agents, {num_rounds} rounds):

Sentiment trajectory:
- Round 1 average: {trajectories["avg_sentiment"][0]:.1f}/10
- Final round average: {trajectories["avg_sentiment"][-1]:.1f}/10
- Final consensus strength: {trajectories["consensus"][-1]:.3f}
- Final bullish ratio: {trajectories["bullish_ratio"][-1]:.0%}

Final round expert positions:
{debate_summary}

Produce a structured report with:
1. OVERALL VERDICT — score out of 10, one-line summary
2. WHERE AGENTS AGREE — 3-5 high-confidence consensus points
3. WHERE AGENTS DIVERGE — key uncertainty zones as a table
4. CONDITIONS FOR SUCCESS — 3-5 non-negotiable requirements
5. REVENUE MODEL — if applicable, year 1/2/3 projections with assumptions
6. TOP 3 RISKS — ranked by impact
7. RECOMMENDED NEXT STEPS — 3 specific actions

Be specific. Reference agent arguments by name. Use numbers where possible."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


# ============================================================
# VISUALISATION
# ============================================================


def generate_charts(trajectories: dict, agents: list[dict], output_dir: Path) -> None:
    """Generate and save analysis charts."""
    rounds = np.array(trajectories["rounds"])
    colors = [
        "#d32f2f",
        "#1976d2",
        "#388e3c",
        "#f57c00",
        "#7b1fa2",
        "#00796b",
        "#c2185b",
        "#455a64",
        "#e64a19",
        "#0097a7",
        "#689f38",
        "#5d4037",
    ]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Top-left: Individual trajectories
    for i, agent in enumerate(agents):
        name = agent["name"]
        if name in trajectories["agent_sentiment"]:
            axes[0, 0].plot(
                rounds,
                trajectories["agent_sentiment"][name],
                "o-",
                color=colors[i % len(colors)],
                label=name.split()[0],
                linewidth=2,
                markersize=5,
            )
    axes[0, 0].axhline(y=5.5, color="gray", linestyle="--", alpha=0.5)
    axes[0, 0].set_xlabel("Debate Round")
    axes[0, 0].set_ylabel("Sentiment (1-10)")
    axes[0, 0].set_title("Individual Agent Trajectories")
    axes[0, 0].legend(fontsize=7, loc="best")
    axes[0, 0].set_ylim(0, 10)
    axes[0, 0].grid(True, alpha=0.3)

    # Top-right: Swarm average
    axes[0, 1].plot(
        rounds,
        trajectories["avg_sentiment"],
        "ro-",
        linewidth=2.5,
        markersize=8,
        label="Average",
    )
    axes[0, 1].plot(
        rounds,
        trajectories["weighted_sentiment"],
        "bs-",
        linewidth=2.5,
        markersize=8,
        label="Confidence-Weighted",
    )
    axes[0, 1].axhline(y=5.5, color="gray", linestyle="--", alpha=0.5)
    axes[0, 1].set_xlabel("Debate Round")
    axes[0, 1].set_ylabel("Sentiment (1-10)")
    axes[0, 1].set_title("Swarm Consensus Trajectory")
    axes[0, 1].legend()
    axes[0, 1].set_ylim(0, 10)
    axes[0, 1].grid(True, alpha=0.3)

    # Bottom-left: Consensus
    axes[1, 0].bar(rounds, trajectories["consensus"], color="#2e7d32", alpha=0.8)
    axes[1, 0].set_xlabel("Debate Round")
    axes[1, 0].set_ylabel("Consensus Strength")
    axes[1, 0].set_title("Agent Agreement Over Time")
    axes[1, 0].grid(True, alpha=0.3)

    # Bottom-right: Bullish ratio
    axes[1, 1].bar(rounds, trajectories["bullish_ratio"], color="#1565c0", alpha=0.8)
    axes[1, 1].axhline(y=0.5, color="gray", linestyle="--", alpha=0.5)
    axes[1, 1].set_xlabel("Debate Round")
    axes[1, 1].set_ylabel("Bullish Ratio")
    axes[1, 1].set_title("% of Agents Predicting UP")
    axes[1, 1].set_ylim(0, 1)
    axes[1, 1].grid(True, alpha=0.3)

    plt.suptitle("SATF Swarm Analysis", fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()

    chart_path = output_dir / "satf_analysis.png"
    plt.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  Chart saved: {chart_path}")


# ============================================================
# TIMESFM INTEGRATION (OPTIONAL)
# ============================================================


def run_timesfm_forecast(csv_path: str, horizon: int = 12) -> dict | None:
    """Run TimesFM forecast on historical data if available."""
    try:
        import timesfm
        import torch
    except ImportError:
        print("  TimesFM not installed — skipping quantitative forecast")
        print("  Install with: pip install timesfm[torch]")
        return None

    # Load CSV — expects a single column of numerical values
    data = np.loadtxt(csv_path, delimiter=",", skiprows=1)
    if data.ndim > 1:
        data = data[:, -1]  # Use last column

    torch.set_float32_matmul_precision("high")

    model = timesfm.TimesFM_2p5_200M_torch.from_pretrained("google/timesfm-2.5-200m-pytorch")
    model.compile(
        timesfm.ForecastConfig(
            max_context=512,
            max_horizon=horizon,
            normalize_inputs=True,
            use_continuous_quantile_head=True,
            force_flip_invariance=True,
            infer_is_positive=True,
            fix_quantile_crossing=True,
        )
    )

    point_forecast, quantile_forecast = model.forecast(horizon=horizon, inputs=[data])

    return {
        "historical": data.tolist(),
        "forecast": point_forecast[0].tolist(),
        "quantiles": quantile_forecast[0].tolist(),
    }


# ============================================================
# REPORT GENERATION
# ============================================================


def save_report(
    idea: str,
    agents: list[dict],
    results: list[dict],
    trajectories: dict,
    synthesis: str,
    output_dir: Path,
    timesfm_results: dict | None = None,
) -> None:
    """Save the complete analysis report."""
    report_path = output_dir / "satf_report.md"

    with open(report_path, "w") as f:
        f.write("# SATF Swarm Analysis Report\n\n")
        f.write("## Business Idea\n\n")
        f.write(f"{idea}\n\n")

        f.write("## Swarm Agents\n\n")
        for a in agents:
            f.write(f"- **{a['name']}** — {a['role']} ({a['bias']})\n")
        f.write("\n")

        f.write("## Sentiment Trajectory\n\n")
        f.write("| Round | Avg Sentiment | Consensus | Bullish % |\n")
        f.write("|-------|--------------|-----------|----------|\n")
        for i, r in enumerate(trajectories["rounds"]):
            f.write(
                f"| {r} | {trajectories['avg_sentiment'][i]:.1f} | "
                f"{trajectories['consensus'][i]:.3f} | "
                f"{trajectories['bullish_ratio'][i]:.0%} |\n"
            )
        f.write("\n")

        f.write("## Full Debate Record\n\n")
        num_rounds = max(d["round"] for d in results)
        for r in range(1, num_rounds + 1):
            f.write(f"### Round {r}\n\n")
            round_data = [d for d in results if d["round"] == r]
            for d in round_data:
                f.write(
                    f"**{d['name']}** ({d['role']}) — "
                    f"Sentiment: {d['sentiment']}/10 | "
                    f"Direction: {d['direction']} | "
                    f"Confidence: {d['confidence']}%\n\n"
                    f"> {d['argument']}\n\n"
                    f"> Key risk: {d.get('key_risk', 'N/A')}\n\n"
                )

        if timesfm_results:
            f.write("## TimesFM Quantitative Forecast\n\n")
            f.write(f"Historical data points: {len(timesfm_results['historical'])}\n\n")
            f.write("Forecast:\n")
            for i, val in enumerate(timesfm_results["forecast"]):
                f.write(f"- Period {i + 1}: {val:.2f}\n")
            f.write("\n")

        f.write("## Meta-Synthesis\n\n")
        f.write(synthesis)
        f.write("\n")

    print(f"  Report saved: {report_path}")

    # Also save raw data as JSON
    data_path = output_dir / "satf_data.json"
    with open(data_path, "w") as f:
        json.dump(
            {
                "idea": idea,
                "agents": agents,
                "results": results,
                "trajectories": trajectories,
                "timesfm": timesfm_results,
            },
            f,
            indent=2,
        )
    print(f"  Raw data saved: {data_path}")


# ============================================================
# MAIN
# ============================================================


def main():
    parser = argparse.ArgumentParser(
        description="SATF Tool — Swarm-Augmented Business Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python satf_tool.py "A marketplace for freelance mining consultants"
  python satf_tool.py --file business_plan.txt --agents 10 --rounds 7
  python satf_tool.py --file idea.txt --historical revenue.csv --output ./report
        """,
    )
    parser.add_argument("idea", nargs="?", help="Business idea description")
    parser.add_argument("--file", "-f", help="Read idea from a text file")
    parser.add_argument("--agents", "-a", type=int, default=8, help="Number of agents (default: 8)")
    parser.add_argument(
        "--rounds", "-r", type=int, default=5, help="Number of debate rounds (default: 5)"
    )
    parser.add_argument(
        "--output", "-o", default="./satf_output", help="Output directory (default: ./satf_output)"
    )
    parser.add_argument("--historical", help="CSV file with historical data for TimesFM forecast")

    args = parser.parse_args()

    # Get the business idea
    if args.file:
        idea = Path(args.file).read_text()
    elif args.idea:
        idea = args.idea
    else:
        print("Error: provide a business idea as an argument or via --file")
        sys.exit(1)

    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("SATF — Swarm-Augmented Business Analysis")
    print("=" * 60)

    # Step 1: Generate agents
    print(f"\n[1/5] Generating {args.agents} expert agents...")
    agents = generate_agents(idea, args.agents)
    for a in agents:
        print(f"    {a['name']:25s} — {a['role']} ({a['bias']})")

    # Step 2: Run simulation
    print(f"\n[2/5] Running {args.rounds}-round swarm debate...")
    results = run_simulation(idea, agents, args.rounds)

    # Step 3: Compute trajectories
    print("\n[3/5] Computing sentiment trajectories...")
    trajectories = compute_trajectories(results, agents, args.rounds)
    print(
        f"    Round 1 avg: {trajectories['avg_sentiment'][0]:.1f}/10 → "
        f"Round {args.rounds} avg: {trajectories['avg_sentiment'][-1]:.1f}/10"
    )
    print(f"    Final bullish ratio: {trajectories['bullish_ratio'][-1]:.0%}")
    print(f"    Final consensus: {trajectories['consensus'][-1]:.3f}")

    # Step 3b: TimesFM forecast (optional)
    timesfm_results = None
    if args.historical:
        print("\n[3b] Running TimesFM quantitative forecast...")
        timesfm_results = run_timesfm_forecast(args.historical)

    # Step 4: Generate synthesis
    print("\n[4/5] Generating meta-synthesis...")
    synthesis = generate_synthesis(idea, results, trajectories, args.rounds)

    # Step 5: Save outputs
    print("\n[5/5] Saving outputs...")
    generate_charts(trajectories, agents, output_dir)
    save_report(idea, agents, results, trajectories, synthesis, output_dir, timesfm_results)

    # Print synthesis to terminal
    print("\n" + "=" * 60)
    print("META-SYNTHESIS")
    print("=" * 60)
    print(synthesis)
    print("\n" + "=" * 60)
    print(f"Full report: {output_dir / 'satf_report.md'}")
    print(f"Charts: {output_dir / 'satf_analysis.png'}")
    print(f"Raw data: {output_dir / 'satf_data.json'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
