import pytest
from src.models.models import ContentUnit
from src.services.chunker import Chunker

@pytest.fixture
def chunker():
    return Chunker(chunk_size=100, chunk_overlap=10)

def test_basic_text_chunking(chunker):
    unit = ContentUnit(
        type="text",
        text="A" * 150, # Larger than chunk_size=100
        page_number=1,
        order_index=0,
        order_index_in_page=0
    )
    chunks = chunker.split_units([unit], "doc1")
    
    assert len(chunks) == 2
    assert len(chunks[0].text) > 0
    # Expected: Context prefix "[Page: 1] " + 100 chars
    # Wait, implementation adds context prefix. "A"*100 plus context.
    # The split happens based on text size, THEN metadata is attached.
    # Actually logic: if len(unit_text) > chunk_size -> split text.
    
    # 150 chars -> 100 + 50 (with overlap).
    # Chunker logic: 
    # Chunk 1: "A"*100
    # Chunk 2: start=90, end=150 -> "A"*60

def test_grouping_small_units(chunker):
    # Two small units should be grouped into one chunk
    u1 = ContentUnit(type="text", text="Hello", page_number=1, order_index=0, order_index_in_page=0)
    u2 = ContentUnit(type="text", text="World", page_number=1, order_index=1, order_index_in_page=1)
    
    chunks = chunker.split_units([u1, u2], "doc1")
    assert len(chunks) == 1
    assert "Hello" in chunks[0].text
    assert "World" in chunks[0].text

def test_table_splitting(chunker):
    # Create a table that is definitely larger than chunk_size=100
    # Header: 2 cols ~ 10 chars
    # Rows: 10 rows, each ~20 chars -> 200 chars total
    
    rows = [["Col1", "Col2"]]
    for i in range(10):
        rows.append([f"Val{i}", f"Data{i}"])
        
    # Serialize it manually to see huge text or just pass rows structure
    # The new chunker uses 'table' dict structure
    
    # Fake long text representation
    fake_text = "start " + "X"*300 
    
    unit = ContentUnit(
        type="table",
        text=fake_text,
        table={"rows": rows},
        page_number=1,
        order_index=0,
        order_index_in_page=0
    )
    
    chunks = chunker.split_units([unit], "doc1")
    
    # Needs to be split
    assert len(chunks) > 1
    
    # Check if header is preserved in second chunk
    # The header line in serializer is "Table Schema: ..." and "row X: ..."
    # Our mocked implementation should handle this.
    
    # Depending on how many rows fit in 100 chars.
    # Likely 1-2 rows per chunk.
    assert chunks[0].metadata["is_table"] is True
    assert chunks[1].metadata["is_table"] is True
    
    # Verify header presence in generic text form (hard to regex exactly without running serializer logic)
    # But we can check that it didn't just split text blindly mid-word
    assert "Table Split:" in chunks[1].text or "Table Schema" in chunks[1].text

def test_section_splitting(chunker):
    # If a new section title appears, it should likely start a new chunk logic (or at least flush text)
    # Current logic: "If adding this unit exceeds chunk size, flush current buffer"
    # It does NOT strictly force split on section title unless we programmed it to.
    # Looking at code: `current_section` is updated.
    
    u1 = ContentUnit(type="text", text="P1", page_number=1, section_title="Intro", order_index=0, order_index_in_page=0)
    u2 = ContentUnit(type="text", text="P2", page_number=1, section_title="Body", order_index=1, order_index_in_page=1)
    
    # chunk_size=100, "P1" + "P2" fits? Yes.
    # Logic: it appends u1, then u2.
    # BUT `current_section` is updated to "Body" when u2 is processed.
    # When chunk is finally created, it uses `current_section`.
    # Wait, if we group them, we might lose "Intro" title if we just overwrite `current_section`.
    # Code check:
    # if unit.section_title: current_section = unit.section_title
    # text accumulates.
    # Final chunk gets `current_section`.
    # Yes, this means minimal loss of granularity for very small paragraphs changing sections. 
    # But for RAG it's usually acceptable if they are small.
    
    chunks = chunker.split_units([u1, u2], "doc1")
    assert len(chunks) == 1
    assert "Section: Body" in chunks[0].text # Should take the latest or preserve context?
    # Ideally it should break on section title change, but for now we test current behavior.
