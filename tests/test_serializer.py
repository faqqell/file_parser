import pytest
from src.services.table_serializer import TableSerializer

def test_to_row_kv_text_empty():
    assert TableSerializer.to_row_kv_text([]) == ""
    assert TableSerializer.to_row_kv_text(None) == ""

def test_to_row_kv_text_single_row():
    # Only header
    rows = [["ID", "Name"]]
    result = TableSerializer.to_row_kv_text(rows)
    # Since there are no data rows, it should effectively be just schema summary
    assert "Table Schema: Columns: col_0, col_1 | Rows: 1" in result
    assert 'col_0="ID"' in result

def test_to_row_kv_text_basic():
    rows = [
        ["ID", "Name", "Age"],
        ["1", "Alice", "30"],
        ["2", "Bob", "25"]
    ]
    result = TableSerializer.to_row_kv_text(rows)
    
    assert "Table Schema: Columns: ID, Name, Age | Rows: 2" in result
    assert 'row 1: {ID="1", Name="Alice", Age="30"}' in result
    assert 'row 2: {ID="2", Name="Bob", Age="25"}' in result

def test_to_row_kv_text_missing_values():
    rows = [
        ["Col1", "Col2"],
        ["Val1"] # Missing second value
    ]
    result = TableSerializer.to_row_kv_text(rows)
    # The serializer typically handles index out of bounds by using colN
    # Let's check the implementation logic from the file we viewed earlier
    # It loops over proper row parts
    assert 'row 1: {Col1="Val1"}' in result

def test_to_row_kv_text_special_chars():
    rows = [
        ["Key", "Value"],
        ['Quote"', "Val'ue"]
    ]
    result = TableSerializer.to_row_kv_text(rows)
    # Should escape double quotes to single quotes as per implementation
    assert 'Key="Quote\'"' in result
