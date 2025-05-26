#!/usr/bin/env python3
"""
Export scraped cryptocurrency events to CSV format
"""

import csv
import json
import argparse
from pathlib import Path
from datetime import datetime
from loguru import logger


def load_scraped_events(domain_dir: Path) -> list:
    """Load all scraped events from a domain directory"""
    all_events = []
    
    # Find all extracted event files
    event_files = sorted(domain_dir.glob("extracted_events_*.json"))
    
    for event_file in event_files:
        try:
            with open(event_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                events = data.get('events', [])
                
                # Add source file info to each event
                for event in events:
                    event['source_file'] = event_file.name
                    event['domain'] = domain_dir.name
                
                all_events.extend(events)
                logger.info(f"Loaded {len(events)} events from {event_file.name}")
                
        except Exception as e:
            logger.error(f"Error loading {event_file}: {e}")
    
    return all_events


def export_to_csv(events: list, output_path: Path):
    """Export events to CSV file"""
    if not events:
        logger.warning("No events to export")
        return
    
    # Deduplicate events based on date, brief_description, and source_url
    seen_events = set()
    deduplicated_events = []
    
    for event in events:
        # Create a unique key for each event
        event_key = (
            event.get('date', ''),
            event.get('brief_description', '')[:30],
            event.get('source_url', '')
        )
        
        if event_key not in seen_events:
            seen_events.add(event_key)
            deduplicated_events.append(event)
        else:
            logger.debug(f"Skipping duplicate event: {event.get('brief_description', '')[:50]}...")
    
    logger.info(f"Deduplicated {len(events)} events to {len(deduplicated_events)} unique events")
    
    # Define CSV columns
    fieldnames = [
        'date',
        'year',
        'month',
        'day',
        'description',  # This is the 100-110 character brief description
        'content',      # This is the full_text
        'source_url',
        'domain',
        'extraction_timestamp',
        'source_file'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for event in deduplicated_events:
            row = {
                'date': event.get('date', ''),
                'year': event.get('year', ''),
                'month': event.get('month', ''),
                'day': event.get('day', ''),
                'description': event.get('brief_description', ''),  # The 100-110 char highlight
                'content': event.get('full_text', ''),              # The full detail
                'source_url': event.get('source_url', ''),
                'domain': event.get('domain', ''),
                'extraction_timestamp': event.get('extraction_timestamp', ''),
                'source_file': event.get('source_file', '')
            }
            writer.writerow(row)
    
    logger.info(f"Exported {len(deduplicated_events)} unique events to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Export scraped cryptocurrency events to CSV")
    parser.add_argument("--domain", help="Specific domain to export (e.g., bitcoin.org)")
    parser.add_argument("--output", default="data_processed/scraped_events.csv", 
                        help="Output CSV file path")
    parser.add_argument("--output-dir", default="data_output/scraped", 
                        help="Directory containing scraped data")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        logger.error(f"Output directory {output_dir} does not exist")
        return
    
    all_events = []
    
    if args.domain:
        # Export specific domain
        domain_dir = output_dir / args.domain
        if domain_dir.exists():
            events = load_scraped_events(domain_dir)
            all_events.extend(events)
        else:
            logger.error(f"Domain directory {domain_dir} does not exist")
            return
    else:
        # Export all domains
        for domain_dir in output_dir.iterdir():
            if domain_dir.is_dir():
                events = load_scraped_events(domain_dir)
                all_events.extend(events)
    
    # Sort events by date
    all_events.sort(key=lambda x: x.get('date', ''))
    
    # Create output directory if needed
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Export to CSV
    export_to_csv(all_events, output_path)
    
    # Print summary
    print(f"\nExport Summary:")
    print(f"Total events exported: {len(all_events)}")
    print(f"Output file: {output_path}")
    
    # Group by year
    years = {}
    for event in all_events:
        year = str(event.get('year', 'unknown'))
        years[year] = years.get(year, 0) + 1
    
    print(f"\nEvents by year:")
    for year in sorted(years.keys()):
        print(f"  {year}: {years[year]} events")


if __name__ == "__main__":
    main()