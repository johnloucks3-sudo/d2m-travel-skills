#!/usr/bin/env python3
"""
Thunderbird OS - Unified Command Line Interface
================================================

Single CLI entry point for all Dreams2Memories intelligence operations:
- Ship intelligence sweeps
- World intelligence (advisories, weather, news)
- Ship comparison reports
- Weekly client reports

Usage:
    thunderbird --sweep-ship-intel
    thunderbird --sweep-world-intel
    thunderbird --compare "Silver Nova" "Seven Seas Grandeur"
    thunderbird --weekly-report --interactive
    thunderbird --status
"""

import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

# Add module paths
sys.path.append(str(Path(__file__).parent))

# Import intelligence modules
try:
    from thunderbird_ship_intel import run_ship_intelligence_sweep
    from thunderbird_world_intel import run_world_intelligence_sweep
    from thunderbird_ship_compare import (
        create_comparison_docx,
        generate_comparison_pdf,
        SHIP_DATABASE,
        ComparisonConfig
    )
    from thunderbird_weekly_report import (
        interactive_report_builder,
        generate_html_report,
        generate_pdf_report,
        ClientReportRequest,
        ReportConfig
    )
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    print("Make sure all Thunderbird modules are in the same directory.")
    sys.exit(1)

# ============================================================================
# VERSION INFO
# ============================================================================

VERSION = "4.0.0"
CODENAME = "Goose-Powered Intelligence Suite"

# ============================================================================
# STATUS DISPLAY
# ============================================================================

def display_status():
    """Display system status and last run information"""
    print("="*70)
    print(f"  THUNDERBIRD OS v{VERSION}")
    print(f"  {CODENAME}")
    print("="*70)
    print()
    print("🔧 SYSTEM STATUS:")
    print("  ✅ Ship Intelligence Module: Ready")
    print("  ✅ World Intelligence Module: Ready")
    print("  ✅ Ship Comparison Module: Ready")
    print("  ✅ Weekly Report Generator: Ready")
    print()
    print("📊 AVAILABLE SHIPS FOR COMPARISON:")
    for ship_name, ship_data in list(SHIP_DATABASE.items())[:5]:
        print(f"  • {ship_name} ({ship_data['line']})")
    print(f"  ... and {len(SHIP_DATABASE) - 5} more")
    print()
    print("📁 OUTPUT DIRECTORIES:")
    print(f"  Ship Comparisons: {ComparisonConfig.OUTPUT_DIR}")
    print(f"  Weekly Reports: {ReportConfig.OUTPUT_DIR}")
    print()

# ============================================================================
# COMMAND HANDLERS
# ============================================================================

async def handle_ship_intel_sweep():
    """Run ship intelligence sweep"""
    print("🚢 INITIATING SHIP INTELLIGENCE SWEEP")
    print("="*70 + "\n")
    
    result = await run_ship_intelligence_sweep()
    
    print("\n" + "="*70)
    print("📊 SWEEP SUMMARY:")
    print(f"  Voyages Scraped: {result['voyages_scraped']}")
    print(f"  Pricing Alerts: {result['pricing_alerts']}")
    print(f"  Availability Alerts: {result['availability_alerts']}")
    print(f"  Cruise Lines: {', '.join(result['cruise_lines_monitored'])}")
    print("="*70)

async def handle_world_intel_sweep():
    """Run world intelligence sweep"""
    print("🌍 INITIATING WORLD INTELLIGENCE SWEEP")
    print("="*70 + "\n")
    
    result = await run_world_intelligence_sweep()
    
    print("\n" + "="*70)
    print("📊 SWEEP SUMMARY:")
    print(f"  Travel Advisories: {result['travel_advisories_total']}")
    print(f"  High-Level Advisories: {result['high_level_advisories']}")
    print(f"  Weather Forecasts: {result['weather_forecasts']}")
    print(f"  News Articles: {result['news_articles']}")
    print(f"  Urgent News: {result['urgent_news']}")
    print("="*70)

def handle_ship_comparison(ship1: str, ship2: str, output_format: str = "both"):
    """Generate ship comparison report"""
    print(f"⛴️  GENERATING COMPARISON: {ship1} vs {ship2}")
    print("="*70 + "\n")
    
    # Validate ships exist in database
    if ship1 not in SHIP_DATABASE:
        print(f"❌ Error: '{ship1}' not found in ship database")
        print(f"Available ships: {', '.join(SHIP_DATABASE.keys())}")
        return
    
    if ship2 not in SHIP_DATABASE:
        print(f"❌ Error: '{ship2}' not found in ship database")
        print(f"Available ships: {', '.join(SHIP_DATABASE.keys())}")
        return
    
    # Generate outputs
    timestamp = datetime.now().strftime("%Y%m%d")
    filename_base = f"{ship1.replace(' ', '_')}_vs_{ship2.replace(' ', '_')}_{timestamp}"
    
    outputs = []
    
    if output_format in ["docx", "both"]:
        docx_path = ComparisonConfig.OUTPUT_DIR / f"{filename_base}.docx"
        success = create_comparison_docx(ship1, ship2, docx_path)
        if success:
            outputs.append(str(docx_path))
    
    if output_format in ["pdf", "both"]:
        pdf_path = ComparisonConfig.OUTPUT_DIR / f"{filename_base}.pdf"
        success = generate_comparison_pdf(ship1, ship2, pdf_path)
        if success:
            outputs.append(str(pdf_path))
    
    print("\n" + "="*70)
    print("✅ COMPARISON COMPLETE")
    print("="*70)
    print("\nGenerated files:")
    for file in outputs:
        print(f"  • {file}")
    print()

def handle_weekly_report(interactive: bool, client: str = None, ships: str = None):
    """Generate weekly client report"""
    if interactive or not client:
        interactive_report_builder()
    else:
        print(f"📊 GENERATING WEEKLY REPORT FOR: {client}")
        print("="*70 + "\n")
        
        target_ships = ships.split(',') if ships else ReportConfig.DEFAULT_SHIPS
        
        request = ClientReportRequest(
            client_name=client,
            target_ships=target_ships,
            output_format="both"
        )
        
        html = generate_html_report(request)
        
        timestamp = datetime.now().strftime("%Y%m%d")
        safe_name = client.replace(' ', '_')
        
        html_path = ReportConfig.OUTPUT_DIR / f"Weekly_Report_{safe_name}_{timestamp}.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        pdf_path = ReportConfig.OUTPUT_DIR / f"Weekly_Report_{safe_name}_{timestamp}.pdf"
        generate_pdf_report(html, pdf_path)
        
        print("\n" + "="*70)
        print("✅ REPORT COMPLETE")
        print("="*70)
        print(f"\n  HTML: {html_path}")
        print(f"  PDF: {pdf_path}\n")

def handle_full_sweep():
    """Run all intelligence sweeps"""
    print("🔥 FULL INTELLIGENCE SWEEP - ALL SYSTEMS")
    print("="*70 + "\n")
    
    asyncio.run(handle_ship_intel_sweep())
    print("\n")
    asyncio.run(handle_world_intel_sweep())
    
    print("\n" + "="*70)
    print("✅ FULL SWEEP COMPLETE")
    print("="*70)

# ============================================================================
# MAIN CLI
# ============================================================================

def main():
    """Main CLI entry point"""
    
    parser = argparse.ArgumentParser(
        description=f"Thunderbird OS v{VERSION} - Dreams2Memories Intelligence Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  thunderbird --status
  thunderbird --sweep-ship-intel
  thunderbird --sweep-world-intel
  thunderbird --full-sweep
  thunderbird --compare "Silver Nova" "Seven Seas Grandeur"
  thunderbird --compare "Silver Nova" "Seven Seas Grandeur" --format pdf
  thunderbird --weekly-report --interactive
  thunderbird --weekly-report --client "John Smith" --ships "Silver Nova,Seven Seas Grandeur"
  
For more information, visit: www.d2mtravel.luxury
        """
    )
    
    # General commands
    parser.add_argument('--status', action='store_true', help='Show system status')
    parser.add_argument('--version', action='store_true', help='Show version')
    
    # Intelligence sweeps
    parser.add_argument('--sweep-ship-intel', action='store_true', help='Run ship intelligence sweep')
    parser.add_argument('--sweep-world-intel', action='store_true', help='Run world intelligence sweep')
    parser.add_argument('--full-sweep', action='store_true', help='Run all intelligence sweeps')
    
    # Ship comparison
    parser.add_argument('--compare', nargs=2, metavar=('SHIP1', 'SHIP2'), help='Compare two ships')
    parser.add_argument('--format', choices=['docx', 'pdf', 'both'], default='both', help='Output format for comparison')
    parser.add_argument('--list-ships', action='store_true', help='List available ships')
    
    # Weekly reports
    parser.add_argument('--weekly-report', action='store_true', help='Generate weekly client report')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    parser.add_argument('--client', type=str, help='Client name for report')
    parser.add_argument('--ships', type=str, help='Comma-separated ship names to monitor')
    
    args = parser.parse_args()
    
    # Handle commands
    if args.version:
        print(f"Thunderbird OS v{VERSION}")
        print(f"{CODENAME}")
        return
    
    if args.status or len(sys.argv) == 1:
        display_status()
        return
    
    if args.list_ships:
        print("📋 AVAILABLE SHIPS FOR COMPARISON:")
        print("="*70)
        for ship_name, ship_data in SHIP_DATABASE.items():
            print(f"\n{ship_name}")
            print(f"  Line: {ship_data['line']}")
            print(f"  Launched: {ship_data['launched']}")
            print(f"  Guests: {ship_data['specs']['max_guests']}")
            print(f"  Space Ratio: {ship_data['ratios']['space_to_guest']}:1")
        return
    
    if args.sweep_ship_intel:
        asyncio.run(handle_ship_intel_sweep())
        return
    
    if args.sweep_world_intel:
        asyncio.run(handle_world_intel_sweep())
        return
    
    if args.full_sweep:
        handle_full_sweep()
        return
    
    if args.compare:
        handle_ship_comparison(args.compare[0], args.compare[1], args.format)
        return
    
    if args.weekly_report:
        handle_weekly_report(args.interactive, args.client, args.ships)
        return
    
    # No command specified
    parser.print_help()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        sys.exit(1)
