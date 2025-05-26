import asyncio
import httpx
import re
from typing import Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from loguru import logger


class WebDownloader:
    """Async web downloader for scraping websites"""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        
    async def download_url(self, url: str) -> Optional[str]:
        """Download HTML content from a URL with retries"""
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        content = response.text
                        logger.info(f"Successfully downloaded {url}")
                        return content
                    else:
                        logger.warning(f"HTTP {response.status_code} for {url}")
                            
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    
        logger.error(f"Failed to download {url} after {self.max_retries} attempts")
        return None
    
    async def download_image(self, image_url: str, save_path: str) -> bool:
        """Download an image file"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(image_url)
                if response.status_code == 200:
                    content = response.content
                    with open(save_path, 'wb') as f:
                        f.write(content)
                    logger.info(f"Downloaded image: {image_url} -> {save_path}")
                    return True
                else:
                    logger.warning(f"Failed to download image {image_url}: HTTP {response.status_code}")
                        
        except Exception as e:
            logger.error(f"Error downloading image {image_url}: {e}")
            
        return False


class HTMLParser:
    """Parse HTML content and extract structured sections"""
    
    def __init__(self, deduplicate_images: bool = True):
        self.section_tags = ['article', 'section', 'main', 'div']
        self.heading_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        self.deduplicate_images = deduplicate_images
        
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
        
        # Deduplicate images if enabled
        if self.deduplicate_images and images:
            images = self._deduplicate_images(images)
        
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
        """Extract image URLs from an element, filtering out icons/logos"""
        images = []
        
        if not element:
            return images
        
        # Keywords to filter out unwanted images
        unwanted_keywords = [
            'icon', 'logo', 'button', 'avatar', 'thumbnail', 'badge',
            'arrow', 'switcher', 'burger', 'search', 'banner', 
            'exchange', 'fire', 'sun', 'moon', 'twitter', 'tg'
        ]
        
        # File extensions to skip (UI elements)
        ui_extensions = ['.svg', '.ico']
        
        # Keywords that strongly suggest relevant infographics  
        strong_keywords = ['price', 'chart', 'graph', 'timeline', 'history']
        
        # Patterns that indicate actual data images
        data_patterns = [
            r'bitcoin.*history',
            r'bitcoin.*price',
            r'price.*history',
            r'transactions.*per.*month',
            r'\d{4}-\d{4}',  # year ranges like 2011-2013
            r'\d{4}',  # 4 digits (years like 2024)
        ]
        
        img_tags = element.find_all('img')
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            if not src:
                continue
                
            # Convert relative URLs to absolute
            full_url = urljoin(base_url, src)
            alt_text = img.get('alt', '')
            
            # Get the filename from URL
            url_path = urlparse(full_url).path.lower()
            combined_text = (url_path + ' ' + alt_text.lower()).strip()
            
            # Skip SVG and ICO files (usually UI elements)
            if any(url_path.endswith(ext) for ext in ui_extensions):
                logger.debug(f"Skipping UI element: {full_url}")
                continue
            
            # Skip if contains unwanted keywords
            if any(keyword in combined_text for keyword in unwanted_keywords):
                logger.debug(f"Skipping unwanted image: {full_url}")
                continue
            
            # Check for data patterns
            has_data_pattern = any(re.search(pattern, combined_text) for pattern in data_patterns)
            
            # Check for strong keywords
            has_strong_keyword = any(keyword in combined_text for keyword in strong_keywords)
            
            # Check for date patterns (years between 2008-2024)
            has_relevant_date = bool(re.search(r'\b20(0[8-9]|1[0-9]|2[0-4])\b', combined_text))
            
            # Only include if it matches data patterns or has strong keywords with dates
            if has_data_pattern or (has_strong_keyword and has_relevant_date):
                images.append({
                    'url': full_url,
                    'alt_text': alt_text
                })
                logger.info(f"Found relevant infographic: {full_url}")
            else:
                logger.debug(f"Skipping non-data image: {full_url}")
        
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
    
    def _deduplicate_images(self, images: list) -> list:
        """
        Deduplicate images that are the same content but different sizes.
        Keeps the highest resolution version of each unique image.
        
        This function can be easily disabled by setting deduplicate_images=False
        in the HTMLParser constructor.
        """
        if not images:
            return images
        
        logger.info(f"Starting image deduplication for {len(images)} images")
        
        # Group images by their normalized base name (without size markers)
        image_groups = {}
        
        for image in images:
            url = image['url']
            base_name = self._normalize_image_name(url)
            resolution = self._extract_resolution(url)
            
            if base_name not in image_groups:
                image_groups[base_name] = []
            
            image_groups[base_name].append({
                'image': image,
                'resolution': resolution,
                'original_url': url
            })
        
        # For each group, keep only the highest resolution image
        deduplicated_images = []
        removed_count = 0
        
        for base_name, group in image_groups.items():
            if len(group) == 1:
                # No duplicates for this image
                deduplicated_images.append(group[0]['image'])
            else:
                # Multiple versions found, keep the highest resolution
                highest_res_item = max(group, key=lambda x: x['resolution'])
                deduplicated_images.append(highest_res_item['image'])
                
                removed_urls = [item['original_url'] for item in group if item != highest_res_item]
                removed_count += len(removed_urls)
                
                logger.info(f"Deduplicated '{base_name}': kept {highest_res_item['resolution']}px version")
                for removed_url in removed_urls:
                    logger.debug(f"  Removed duplicate: {removed_url}")
        
        logger.info(f"Image deduplication complete: {len(images)} -> {len(deduplicated_images)} images ({removed_count} duplicates removed)")
        
        return deduplicated_images
    
    def _normalize_image_name(self, url: str) -> str:
        """
        Normalize image name by removing size-related markers.
        
        Removes patterns like:
        - 550px-, 1100px- (prefix size markers)
        - _550px, _1100px (suffix size markers)  
        - 800x600-, 1920x1080- (dimension markers)
        - _800x600, _1920x1080 (suffix dimensions)
        """
        # Get the filename from the URL
        parsed_url = urlparse(url)
        filename = parsed_url.path.split('/')[-1]
        
        # Remove common size patterns (more comprehensive)
        patterns_to_remove = [
            r'\d+px-',           # 550px-, 1100px-
            r'-\d+px',           # -550px, -1100px
            r'_\d+px',           # _550px, _1100px
            r'\d+px',            # 550px, 1100px (standalone)
            r'\d+x\d+-',         # 800x600-, 1920x1080-
            r'-\d+x\d+',         # -800x600, -1920x1080
            r'_\d+x\d+',         # _800x600, _1920x1080
            r'\d+x\d+',          # 800x600, 1920x1080 (standalone)
            r'\d+w-',            # 800w- (width markers)
            r'-\d+w',            # -800w
            r'_\d+w',            # _800w
            r'\d+w',             # 800w (standalone)
            r'\d+-',             # 550- (generic number prefix)
            r'-\d+',             # -550 (generic number suffix)
            r'_\d+',             # _550 (generic number with underscore)
        ]
        
        normalized = filename
        
        # Apply patterns in order, being careful not to remove important numbers
        # First, remove the most specific patterns
        specific_patterns = [
            r'\d+px-', r'-\d+px', r'_\d+px', r'\d+px',
            r'\d+x\d+-', r'-\d+x\d+', r'_\d+x\d+', r'\d+x\d+',
            r'\d+w-', r'-\d+w', r'_\d+w', r'\d+w'
        ]
        
        for pattern in specific_patterns:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Then remove generic number patterns, but preserve years (2008-2024)
        # and other important numbers by being more selective
        generic_patterns = [
            r'(?<!20)\d{3,4}-',  # Numbers 3-4 digits followed by dash (but not years like 2008-)
            r'-(?!20)\d{3,4}',   # Numbers 3-4 digits preceded by dash (but not -2008)
            r'_(?!20)\d{3,4}',   # Numbers 3-4 digits preceded by underscore (but not _2008)
        ]
        
        for pattern in generic_patterns:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Clean up any double separators that might result
        normalized = re.sub(r'[-_]{2,}', '-', normalized)
        normalized = re.sub(r'^[-_]|[-_]$', '', normalized)
        
        # If the normalized name is empty or too short, fall back to original
        if len(normalized) < 3:
            logger.debug(f"Normalization resulted in too short name, using original: {filename}")
            return filename
        
        logger.debug(f"Normalized '{filename}' -> '{normalized}'")
        return normalized
    
    def _extract_resolution(self, url: str) -> int:
        """
        Extract the resolution/size number from an image URL.
        Only extracts numbers that are explicitly marked as resolutions (px, w, x dimensions).
        Returns 0 if no explicit resolution markers are found.
        """
        # Get the filename from the URL
        parsed_url = urlparse(url)
        filename = parsed_url.path.split('/')[-1]
        
        # Only accept explicit resolution markers - no bare numbers!
        resolution_patterns = [
            r'(\d+)px',          # 550px, 1100px (most common)
            r'(\d+)x(\d+)',      # 800x600 (capture both dimensions)
            r'(\d+)w',           # 800w (width markers)
        ]
        
        found_resolutions = []
        
        for pattern in resolution_patterns:
            matches = re.findall(pattern, filename, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # For patterns like (\d+)x(\d+), add both numbers
                    for num in match:
                        try:
                            num_val = int(num)
                            # Keep reasonable resolution values (50-10000 pixels)
                            # Exclude obvious years even if they have px/w markers
                            if 50 <= num_val <= 10000 and not (2008 <= num_val <= 2024):
                                found_resolutions.append(num_val)
                        except ValueError:
                            continue
                else:
                    try:
                        num_val = int(match)
                        # Keep reasonable resolution values (50-10000 pixels)
                        # Exclude obvious years even if they have px/w markers
                        if 50 <= num_val <= 10000 and not (2008 <= num_val <= 2024):
                            found_resolutions.append(num_val)
                    except ValueError:
                        continue
        
        # If we found explicit resolution markers, return the highest one
        if found_resolutions:
            max_res = max(found_resolutions)
            logger.debug(f"Extracted resolution {max_res} from explicit markers in: {filename}")
            return max_res
        
        # No explicit resolution markers found - return 0
        # This is much safer than guessing from bare numbers
        logger.debug(f"No explicit resolution markers found in: {filename}")
        return 0