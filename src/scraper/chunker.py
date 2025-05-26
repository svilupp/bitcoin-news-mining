from typing import List
from .models import RawChunk
from loguru import logger
import re


class ContentChunker:
    """Split website content into manageable chunks for processing"""
    
    def __init__(self, max_tokens_per_chunk: int = 2000):
        self.max_tokens_per_chunk = max_tokens_per_chunk
        
    def create_chunks(self, parsed_content: dict, url: str) -> List[RawChunk]:
        """Create chunks from parsed content"""
        chunks = []
        chunk_index = 0
        
        # Process text sections
        for section in parsed_content.get('sections', []):
            text_chunks = self._split_text_section(section, url, chunk_index)
            chunks.extend(text_chunks)
            chunk_index += len(text_chunks)
        
        # Process images if any
        for image in parsed_content.get('images', []):
            image_chunk = RawChunk(
                url=url,
                chunk_index=chunk_index,
                content_type='image',
                content=f"Image: {image['alt_text']} URL: {image['url']}",
                image_path=None,  # Will be set when image is downloaded
                section_heading=None,
                tokens_estimate=500  # Rough estimate for image processing
            )
            chunks.append(image_chunk)
            chunk_index += 1
        
        logger.info(f"Created {len(chunks)} chunks from {url}")
        return chunks
    
    def _split_text_section(self, section: dict, url: str, start_index: int) -> List[RawChunk]:
        """Split a text section into appropriately sized chunks"""
        content = section['content']
        heading = section['heading']
        estimated_tokens = section.get('tokens_estimate', len(content.split()) * 1.3)
        
        # If section fits in one chunk, return as-is
        if estimated_tokens <= self.max_tokens_per_chunk:
            return [RawChunk(
                url=url,
                chunk_index=start_index,
                content_type='text',
                content=content,
                section_heading=heading,
                tokens_estimate=int(estimated_tokens)
            )]
        
        # Split into smaller chunks
        chunks = []
        sentences = self._split_into_sentences(content)
        current_chunk = ""
        current_tokens = 0
        chunk_count = 0
        
        # Add heading context to first chunk
        if heading:
            current_chunk = f"Section: {heading}\n\n"
            current_tokens = len(heading.split()) * 1.3
        
        for sentence in sentences:
            sentence_tokens = len(sentence.split()) * 1.3
            
            # If adding this sentence would exceed limit, save current chunk
            if current_tokens + sentence_tokens > self.max_tokens_per_chunk and current_chunk.strip():
                chunks.append(RawChunk(
                    url=url,
                    chunk_index=start_index + chunk_count,
                    content_type='text',
                    content=current_chunk.strip(),
                    section_heading=heading,
                    tokens_estimate=int(current_tokens)
                ))
                chunk_count += 1
                
                # Start new chunk with context if needed
                current_chunk = f"(Continued from: {heading})\n\n" if heading else ""
                current_tokens = len(current_chunk.split()) * 1.3 if current_chunk else 0
            
            current_chunk += sentence + " "
            current_tokens += sentence_tokens
        
        # Add final chunk if there's content
        if current_chunk.strip():
            chunks.append(RawChunk(
                url=url,
                chunk_index=start_index + chunk_count,
                content_type='text',
                content=current_chunk.strip(),
                section_heading=heading,
                tokens_estimate=int(current_tokens)
            ))
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for better chunking"""
        # Split on sentence endings, but keep common abbreviations together
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        
        # Filter out very short sentences and clean up
        sentences = [s.strip() for s in sentences if len(s.strip()) > 2]
        
        return sentences
    
    def optimize_chunks(self, chunks: List[RawChunk]) -> List[RawChunk]:
        """Optimize chunks by merging small ones and splitting large ones"""
        optimized = []
        
        i = 0
        while i < len(chunks):
            current_chunk = chunks[i]
            
            # If chunk is very small, try to merge with next chunk
            if (current_chunk.tokens_estimate < self.max_tokens_per_chunk * 0.3 
                and i + 1 < len(chunks)
                and chunks[i + 1].content_type == 'text'
                and current_chunk.content_type == 'text'
                and current_chunk.section_heading == chunks[i + 1].section_heading):
                
                next_chunk = chunks[i + 1]
                combined_tokens = current_chunk.tokens_estimate + next_chunk.tokens_estimate
                
                if combined_tokens <= self.max_tokens_per_chunk:
                    # Merge chunks
                    merged_content = f"{current_chunk.content}\n\n{next_chunk.content}"
                    merged_chunk = RawChunk(
                        url=current_chunk.url,
                        chunk_index=current_chunk.chunk_index,
                        content_type='text',
                        content=merged_content,
                        section_heading=current_chunk.section_heading,
                        tokens_estimate=combined_tokens
                    )
                    optimized.append(merged_chunk)
                    i += 2  # Skip next chunk since we merged it
                    continue
            
            optimized.append(current_chunk)
            i += 1
        
        # Update chunk indices
        for i, chunk in enumerate(optimized):
            chunk.chunk_index = i
        
        logger.info(f"Optimized {len(chunks)} chunks to {len(optimized)} chunks")
        return optimized