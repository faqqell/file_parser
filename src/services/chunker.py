import uuid
from typing import List, Optional
from src.models.models import ContentUnit, Chunk
from src.services.table_serializer import TableSerializer

class Chunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_units(self, units: List[ContentUnit], doc_id: str) -> List[Chunk]:
        chunks = []
        current_chunk_text = ""
        current_units = []
        current_section = None
        
        for unit in units:
            # Update current section context
            if unit.type == "text" and unit.section_title:
                current_section = unit.section_title
                
            # Treat tables specially - they are atomic units unless too large
            if unit.type == "table":
                # First, flush any accumulated text
                if current_chunk_text:
                    chunks.append(self._create_chunk(
                        text=current_chunk_text,
                        doc_id=doc_id,
                        page_number=current_units[0].page_number if current_units else None,
                        section_title=current_section,
                        is_table=False,
                        order_index=current_units[0].order_index if current_units else 0
                    ))
                    current_chunk_text = ""
                    current_units = []

                # Handle the table
                table_chunks = self._process_table_unit(unit, doc_id, current_section)
                chunks.extend(table_chunks)
                continue
            
            # For text units, try to group them
            unit_text = unit.text
            if not unit_text:
                continue

            # If adding this unit exceeds chunk size, flush current buffer
            if len(current_chunk_text) + len(unit_text) > self.chunk_size and current_chunk_text:
                chunks.append(self._create_chunk(
                    text=current_chunk_text,
                    doc_id=doc_id,
                    page_number=current_units[0].page_number if current_units else None,
                    section_title=current_section,
                    is_table=False,
                    order_index=current_units[0].order_index if current_units else 0
                ))
                current_chunk_text = ""
                current_units = []

            # If the unit itself is huge, split it
            if len(unit_text) > self.chunk_size:
                text_blocks = self._split_text(unit_text)
                for block in text_blocks:
                    chunks.append(self._create_chunk(
                        text=block,
                        doc_id=doc_id,
                        page_number=unit.page_number,
                        section_title=unit.section_title or current_section,
                        is_table=False,
                        order_index=unit.order_index
                    ))
            else:
                # Accumulate
                if current_chunk_text:
                    current_chunk_text += "\n\n"
                current_chunk_text += unit_text
                current_units.append(unit)

        # Flush final buffer
        if current_chunk_text:
            chunks.append(self._create_chunk(
                text=current_chunk_text,
                doc_id=doc_id,
                page_number=current_units[0].page_number if current_units else None,
                section_title=current_section,
                is_table=False,
                order_index=current_units[0].order_index if current_units else 0
            ))

        return chunks

    def _process_table_unit(self, unit: ContentUnit, doc_id: str, section_title: Optional[str]) -> List[Chunk]:
        """
        Process a table unit. If it fits in chunk_size, return 1 chunk.
        If it's too big, split by rows and REPEAT HEADERS in each chunk.
        """
        if len(unit.text) <= self.chunk_size:
            return [self._create_chunk(
                text=unit.text,
                doc_id=doc_id,
                page_number=unit.page_number,
                section_title=section_title,
                is_table=True,
                order_index=unit.order_index
            )]
        
        # Table is too big. We need primitive rows to split intelligently.
        # If 'table' field matches the expected structure: {'rows': [['col1', 'col2'], ['val1', 'val2']]}
        if not unit.table or 'rows' not in unit.table or not unit.table['rows']:
            # Fallback: just split text blindly if we don't have structured rows
            return self._split_large_text_unit(unit, doc_id, section_title, is_table=True)

        rows = unit.table['rows']
        if len(rows) < 2:
             return [self._create_chunk(
                text=unit.text,
                doc_id=doc_id,
                page_number=unit.page_number,
                section_title=section_title,
                is_table=True,
                order_index=unit.order_index
            )]

        # Extract header and data
        header_row = rows[0]
        data_rows = rows[1:]
        
        # We will form small tables: [header_row] + subset_of_data_rows
        chunks = []
        current_batch = []
        current_size = 0
        
        # Helper to finish a batch
        def make_chunk_from_batch(batch_rows):
            # Create a mini-table with original header
            mini_table = [header_row] + batch_rows
            text = TableSerializer.to_row_kv_text(mini_table)
            # Add note about splitting
            text = f"[Table Split: showing {len(batch_rows)} rows]\n" + text
            return self._create_chunk(
                text=text,
                doc_id=doc_id,
                page_number=unit.page_number,
                section_title=section_title,
                is_table=True,
                order_index=unit.order_index
            )

        for row in data_rows:
            # Rough size estimation: sum of char lengths of cells + overhead
            row_len = sum(len(str(c)) for c in row) + len(row)*10 + 20 
            
            if current_size + row_len > self.chunk_size and current_batch:
                chunks.append(make_chunk_from_batch(current_batch))
                current_batch = []
                current_size = 0
            
            current_batch.append(row)
            current_size += row_len
            
        if current_batch:
            chunks.append(make_chunk_from_batch(current_batch))
            
        return chunks

    def _split_large_text_unit(self, unit: ContentUnit, doc_id: str, section_title: Optional[str], is_table: bool) -> List[Chunk]:
        text_blocks = self._split_text(unit.text)
        return [
            self._create_chunk(
                text=block,
                doc_id=doc_id,
                page_number=unit.page_number,
                section_title=section_title,
                is_table=is_table,
                order_index=unit.order_index
            )
            for block in text_blocks
        ]

    def _split_text(self, text: str) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]
        
        blocks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            # Try to find a sentence break near the end
            if end < len(text):
                # Search back for period or newline
                break_point = -1
                search_window = text[start + self.chunk_size - 100 : start + self.chunk_size]
                
                last_period = search_window.rfind('. ')
                last_newline = search_window.rfind('\n')
                
                if last_newline != -1:
                    break_point = start + self.chunk_size - 100 + last_newline + 1
                elif last_period != -1:
                     break_point = start + self.chunk_size - 100 + last_period + 2
                     
                if break_point != -1 and break_point > start:
                    end = break_point
            
            blocks.append(text[start:end])
            start = end - self.chunk_overlap 
            if start < 0: start = 0 # Safety
            
            # Avoid infinite loop if no progress
            if end == start:
                start += self.chunk_size

        return blocks

    def _create_chunk(self, text: str, doc_id: str, page_number: Optional[int], section_title: Optional[str], is_table: bool, order_index: int) -> Chunk:
        context_prefix = ""
        if section_title:
            context_prefix += f"[Section: {section_title}]\n"
        if page_number:
            context_prefix += f"[Page: {page_number}] "
            
        full_content = context_prefix + text
        
        return Chunk(
            chunk_id=str(uuid.uuid4()),
            doc_id=doc_id,
            text=full_content,
            metadata={
                "page_number": page_number,
                "section_title": section_title,
                "is_table": is_table,
                "order_index": order_index
            }
        )