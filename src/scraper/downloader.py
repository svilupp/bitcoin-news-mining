import asyncio
import aiohttp
from typing import Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class WebDownloader:
    """Async web downloader for scraping websites"""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        
    async def download_url(self, url: str) -> Optional[str]:
        """Download HTML content from a URL with retries"""
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.text()
                            logger.info(f"Successfully downloaded {url}")
                            return content
                        else:
                            logger.warning(f"HTTP {response.status} for {url}")
                            
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    
        logger.error(f"Failed to download {url} after {self.max_retries} attempts")
        return None
    
    async def download_image(self, image_url: str, save_path: str) -> bool:
        """Download an image file"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(save_path, 'wb') as f:
                            f.write(content)
                        logger.info(f"Downloaded image: {image_url} -> {save_path}")
                        return True
                    else:
                        logger.warning(f"Failed to download image {image_url}: HTTP {response.status}")
                        
        except Exception as e:
            logger.error(f"Error downloading image {image_url}: {e}")
            
        return False


class HTMLParser:
    """Parse HTML content and extract structured sections"""
    
    def __init__(self):
        self.section_tags = ['article', 'section', 'main', 'div']
        self.heading_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        
    def parse_html(self, html_content: str, base_url: str) -> dict:
        """Parse HTML and extract sections with text and images"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        sections = []
        images = []
        
        # Extract main content sections
        content_sections = self._find_content_sections(soup)
        
        for i, section in enumerate(content_sections):
            section_text = self._extract_text(section)
            section_heading = self._find_section_heading(section)
            
            if section_text.strip():
                sections.append({
                    'index': i,
                    'type': 'text',
                    'content': section_text,
                    'heading': section_heading,
                    'tokens_estimate': len(section_text.split()) * 1.3  # Rough token estimate
                })
            
            # Extract images from this section
            section_images = self._extract_images(section, base_url)
            images.extend(section_images)
        
        return {
            'sections': sections,
            'images': images,
            'title': self._extract_title(soup),
            'total_sections': len(sections)
        }
    
    def _find_content_sections(self, soup: BeautifulSoup) -> list:
        """Find main content sections in the HTML"""
        # Try to find main content container
        main_content = soup.find('main') or soup.find('article')
        if main_content:
            return self._split_by_headings(main_content)
        
        # Fallback: find all sections/articles
        sections = soup.find_all(self.section_tags)
        if sections:
            return sections
        
        # Last resort: split body by headings
        body = soup.find('body')
        if body:
            return self._split_by_headings(body)
        
        return [soup]
    
    def _split_by_headings(self, container) -> list:
        """Split content by heading tags"""
        sections = []
        current_section = []
        
        for element in container.children:
            if hasattr(element, 'name') and element.name in self.heading_tags:
                if current_section:
                    sections.append(self._create_section_element(current_section))
                    current_section = []
                current_section.append(element)
            else:
                current_section.append(element)
        
        if current_section:
            sections.append(self._create_section_element(current_section))
        
        return [s for s in sections if s is not None]
    
    def _create_section_element(self, elements):
        """Create a section element from a list of elements"""
        if not elements:
            return None
        
        # Create a temporary container
        container = BeautifulSoup('', 'html.parser')
        section = container.new_tag('div')
        
        for element in elements:
            if hasattr(element, 'name'):
                section.append(element)
        
        return section if section.get_text(strip=True) else None
    
    def _extract_text(self, element) -> str:
        """Extract clean text from an element"""
        if not element:
            return ""
        
        # Get text and clean it up
        text = element.get_text(separator=' ', strip=True)
        # Remove multiple whitespaces
        text = ' '.join(text.split())
        return text
    
    def _find_section_heading(self, element) -> Optional[str]:
        """Find the heading for a section"""
        if not element:
            return None
            
        heading = element.find(self.heading_tags)
        if heading:
            return heading.get_text(strip=True)
        
        return None
    
    def _extract_images(self, element, base_url: str) -> list:
        """Extract image URLs from an element"""
        images = []
        
        if not element:
            return images
        
        img_tags = element.find_all('img')
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            if src:
                # Convert relative URLs to absolute
                full_url = urljoin(base_url, src)
                alt_text = img.get('alt', '')
                
                images.append({
                    'url': full_url,
                    'alt_text': alt_text
                })
        
        return images
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title"""
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text(strip=True)
        
        return "Unknown Title"