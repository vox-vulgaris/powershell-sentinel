import json
import argparse
import collections
from rich.console import Console
from rich.table import Table
from rich.padding import Padding

def analyze_log(log_path: str):
    """
    Parses and analyzes the audit.jsonl file to produce a summary report.
    """
    console = Console()

    primitive_stats = collections.defaultdict(lambda: {'success': 0, 'failure': 0, 'total': 0})
    technique_stats = collections.defaultdict(lambda: {'success': 0, 'failure': 0, 'total': 0})
    failure_type_counts = collections.Counter()
    failure_detail_counts = collections.Counter()

    total_lines = 0
    total_success = 0

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                total_lines += 1
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    console.print(f"[bold red]Warning: Skipping malformed JSON line: {line.strip()}[/bold red]")
                    continue
                
                is_success = data['status'] == 'success'
                if is_success:
                    total_success += 1
                
                # --- Aggregate Stats by Primitive ---
                primitive_id = data['primitive_id']
                primitive_stats[primitive_id]['total'] += 1
                if is_success:
                    primitive_stats[primitive_id]['success'] += 1
                else:
                    primitive_stats[primitive_id]['failure'] += 1
                
                # --- Aggregate Stats by Technique ---
                recipe = data.get('recipe', [])
                if not recipe: # Handle the "no obfuscation" case
                    recipe = ['[NONE]']
                
                for tech in recipe:
                    technique_stats[tech]['total'] += 1
                    if is_success:
                        technique_stats[tech]['success'] += 1
                    else:
                        technique_stats[tech]['failure'] += 1

                # --- Aggregate Failure Details ---
                if not is_success:
                    failure_type_counts[data['status']] += 1
                    if data['status'] == 'failure_lab':
                        # Extract the core error message for better grouping
                        details = data.get('details', 'Unknown Lab Error')
                        if "Stderr:" in details:
                            core_error = details.split("Stderr:")[-1].strip().splitlines()[0]
                        else:
                            core_error = details.strip().splitlines()[0]
                        failure_detail_counts[core_error] += 1

    except FileNotFoundError:
        console.print(f"[bold red]FATAL: Log file not found at '{log_path}'[/bold red]")
        return

    # --- Print The Report ---
    
    console.print(Padding(f"[bold cyan]Analysis Report for '{log_path}'[/bold cyan]", (2, 0, 1, 0)))

    # Overall Summary
    total_failures = total_lines - total_success
    overall_success_rate = (total_success / total_lines * 100) if total_lines > 0 else 0
    summary_table = Table(title="Overall Generation Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="magenta", justify="right")
    summary_table.add_row("Total Attempts", f"{total_lines:,}")
    summary_table.add_row("Successful Pairs", f"{total_success:,}")
    summary_table.add_row("Failed Attempts", f"{total_failures:,}")
    summary_table.add_row("Overall Success Rate", f"{overall_success_rate:.2f}%")
    console.print(summary_table)

    # Primitive Stats
    primitive_table = Table(title="Success Rate by Primitive")
    primitive_table.add_column("Primitive ID", style="cyan", justify="left")
    primitive_table.add_column("Success", style="green", justify="right")
    primitive_table.add_column("Failure", style="red", justify="right")
    primitive_table.add_column("Total", style="magenta", justify="right")
    primitive_table.add_column("Success Rate", style="bold blue", justify="right")

    for pid, stats in sorted(primitive_stats.items()):
        rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
        primitive_table.add_row(pid, str(stats['success']), str(stats['failure']), str(stats['total']), f"{rate:.1f}%")
    console.print(primitive_table)

    # Technique Stats
    technique_table = Table(title="Success Rate by Obfuscation Technique (Appearance in Recipe)")
    technique_table.add_column("Technique", style="cyan", justify="left")
    technique_table.add_column("Success", style="green", justify="right")
    technique_table.add_column("Failure", style="red", justify="right")
    technique_table.add_column("Total Appearances", style="magenta", justify="right")
    technique_table.add_column("Success Rate", style="bold blue", justify="right")

    for tech, stats in sorted(technique_stats.items()):
        rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
        technique_table.add_row(tech, str(stats['success']), str(stats['failure']), str(stats['total']), f"{rate:.1f}%")
    console.print(technique_table)
    
    # Failure Analysis
    failure_type_table = Table(title="Failure Analysis by Type")
    failure_type_table.add_column("Failure Type", style="cyan", justify="left")
    failure_type_table.add_column("Count", style="red", justify="right")

    for f_type, count in failure_type_counts.most_common():
        failure_type_table.add_row(f_type, str(count))
    console.print(failure_type_table)

    # Lab Failure Details
    failure_detail_table = Table(title="Top Lab Failure Reasons")
    failure_detail_table.add_column("Error Message", style="cyan", justify="left")
    failure_detail_table.add_column("Count", style="red", justify="right")
    
    for detail, count in failure_detail_counts.most_common(10): # Show top 10
        failure_detail_table.add_row(detail, str(count))
    console.print(failure_detail_table)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Analyze the audit log from the V2 data factory.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "log_path",
        nargs='?',
        default="data/generated/audit_log.jsonl",
        help="Path to the audit_log.jsonl file (default: data/generated/audit_log.jsonl)"
    )
    args = parser.parse_args()
    analyze_log(args.log_path)