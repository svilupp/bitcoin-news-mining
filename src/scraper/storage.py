import json
import os
from datetime import datetime
from pathlib import Path
from typing import List
from urllib.parse import urlparse
from loguru import logger

from .models import RawChunk, CryptoEvent, ScrapingResult
from .downloader import WebDownloader


class StorageManager:
    """Manage storage of raw data and processed events"""
    
    def __init__(self, base_raw_dir: str = "data_raw/scraped", base_output_dir: str = "data_output/scraped"):
        self.base_raw_dir = Path(base_raw_dir)
        self.base_output_dir = Path(base_output_dir)
        self.downloader = WebDownloader()
        
    def get_domain_dir(self, url: str, base_dir: Path) -> Path:
        """Get directory path for a domain"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('www.', '')
        # Clean domain name for filesystem
        domain = domain.replace(':', '_').replace('/', '_')
        return base_dir / domain
    
    async def save_raw_data(self, chunks: List[RawChunk], url: str) -> str:
        """Save raw chunks and download images"""
        domain_dir = self.get_domain_dir(url, self.base_raw_dir)
        domain_dir.mkdir(parents=True, exist_ok=True)
        
        # Create images subdirectory
        images_dir = domain_dir / "images"
        images_dir.mkdir(exist_ok=True)
        
        # Download images and update paths
        await self._download_images(chunks, images_dir)
        
        # Save raw chunks as JSON with datetime serialization
        chunks_data = [chunk.model_dump(mode='json') for chunk in chunks]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"raw_content_{timestamp}.json"
        filepath = domain_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'total_chunks': len(chunks),
                'chunks': chunks_data
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(chunks)} raw chunks to {filepath}")
        return str(filepath)
    
    async def save_extracted_events(self, events: List[CryptoEvent], scraping_result: ScrapingResult) -> str:
        """Save extracted events to JSON"""
        domain_dir = self.get_domain_dir(scraping_result.url, self.base_output_dir)
        domain_dir.mkdir(parents=True, exist_ok=True)
        
        # Check for existing files for this URL
        existing_files = list(domain_dir.glob("extracted_events_*.json"))
        
        # If we have existing files, check if they're for the same URL
        url_hash = hash(scraping_result.url) % 10000  # Simple hash for URL identification
        
        # Look for existing file with same URL
        existing_file = None
        for file_path in existing_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('metadata', {}).get('url') == scraping_result.url:
                        existing_file = file_path
                        break
            except:
                continue
        
        if existing_file:
            # Overwrite existing file for same URL
            filepath = existing_file
            logger.info(f"Overwriting existing file for URL: {existing_file}")
        else:
            # Create new file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"extracted_events_{timestamp}.json"
            filepath = domain_dir / filename
        
        # Prepare data for saving
        output_data = {
            'metadata': scraping_result.model_dump(exclude={'events', 'raw_chunks'}, mode='json'),
            'events': [event.model_dump(mode='json') for event in events],
            'summary': {
                'total_events': len(events),
                'success_rate': scraping_result.successful_extractions / scraping_result.total_chunks if scraping_result.total_chunks > 0 else 0,
                'events_by_year': self._group_events_by_year(events)
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Saved {len(events)} extracted events to {filepath}")
        return str(filepath)
    
    async def _download_images(self, chunks: List[RawChunk], images_dir: Path):
        """Download images referenced in chunks"""
        image_chunks = [chunk for chunk in chunks if chunk.content_type == 'image']
        
        for chunk in image_chunks:
            # Extract image URL from content
            content_parts = chunk.content.split('URL: ')
            if len(content_parts) > 1:
                image_url = content_parts[1].strip()
                
                # Generate filename
                parsed_url = urlparse(image_url)
                filename = os.path.basename(parsed_url.path)
                if not filename or '.' not in filename:
                    filename = f"image_{chunk.chunk_index}.jpg"
                
                # Ensure unique filename
                save_path = images_dir / filename
                counter = 1
                while save_path.exists():
                    name, ext = os.path.splitext(filename)
                    save_path = images_dir / f"{name}_{counter}{ext}"
                    counter += 1
                
                # Download image
                success = await self.downloader.download_image(image_url, str(save_path))
                if success:
                    chunk.image_path = str(save_path)
                    logger.debug(f"Downloaded image for chunk {chunk.chunk_index}: {save_path}")
    
    def _group_events_by_year(self, events: List[CryptoEvent]) -> dict:
        """Group events by year for summary"""
        years = {}
        for event in events:
            try:
                year = str(event.year)
                if year not in years:
                    years[year] = 0
                years[year] += 1
            except:
                if 'unknown' not in years:
                    years['unknown'] = 0
                years['unknown'] += 1
        
        return years
    
    def load_raw_data(self, filepath: str) -> List[RawChunk]:
        """Load raw chunks from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks = []
        for chunk_data in data['chunks']:
            chunk = RawChunk(**chunk_data)
            chunks.append(chunk)
        
        return chunks
    
    def load_extracted_events(self, filepath: str) -> List[CryptoEvent]:
        """Load extracted events from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        events = []
        for event_data in data['events']:
            event = CryptoEvent(**event_data)
            events.append(event)
        
        return events
    
    def list_saved_domains(self) -> dict:
        """List all domains with saved data"""
        domains = {}
        
        # Check raw data
        if self.base_raw_dir.exists():
            for domain_dir in self.base_raw_dir.iterdir():
                if domain_dir.is_dir():
                    domains[domain_dir.name] = {
                        'raw_files': list(domain_dir.glob('raw_content_*.json')),
                        'images': list((domain_dir / 'images').glob('*')) if (domain_dir / 'images').exists() else []
                    }
        
        # Check output data
        if self.base_output_dir.exists():
            for domain_dir in self.base_output_dir.iterdir():
                if domain_dir.is_dir():
                    if domain_dir.name not in domains:
                        domains[domain_dir.name] = {}
                    domains[domain_dir.name]['output_files'] = list(domain_dir.glob('extracted_events_*.json'))
        
        return domains
    
    def cleanup_old_files(self, days_old: int = 30):
        """Clean up files older than specified days"""
        cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        
        for base_dir in [self.base_raw_dir, self.base_output_dir]:
            if not base_dir.exists():
                continue
                
            for domain_dir in base_dir.iterdir():
                if domain_dir.is_dir():
                    for file_path in domain_dir.rglob('*'):
                        if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                            file_path.unlink()
                            logger.info(f"Deleted old file: {file_path}")
                    
                    # Remove empty directories
                    try:
                        if not any(domain_dir.iterdir()):
                            domain_dir.rmdir()
                            logger.info(f"Removed empty directory: {domain_dir}")
                    except OSError:
                        pass  # Directory not empty