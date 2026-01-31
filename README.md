# 📄 Local RAG Parser

**Production-ready document parsing API for RAG (Retrieval-Augmented Generation) systems.**

Parse PDFs, DOCX, Excel, and images into clean, structured JSON with intelligent chunking — perfect for vector databases and LLM applications.

---

## 🚀 Features

### Supported Formats
- **PDF** - Text extraction, table detection, OCR fallback
- **DOCX** - Paragraphs, tables, headings, metadata
- **Excel** (.xlsx, .xls) - Multi-sheet support, merged cells handling
- **Images** (.png, .jpg, .jpeg) - OCR text extraction

### Intelligent Processing
- ✅ **Smart Table Detection** - Automatic header recognition, forward-fill for empty cells
- ✅ **OCR Post-Correction** - Fixes letter spacing ("n i m p r o vement" → "improvement") and typos
- ✅ **Content Deduplication** - Eliminates duplicate content between tables and text
- ✅ **Hierarchical Chunking** - Preserves document structure with context metadata
- ✅ **Language Detection** - Automatic language identification
- ✅ **Metadata Extraction** - Author, title, creation date, page count

### Output Format
```json
{
  "doc_id": "a1b2c3...",
  "source": {
    "file_name": "document.pdf",
    "file_size": 245760,
    "created_at": "2026-01-31T10:00:00"
  },
  "content_units": [
    {
      "type": "text",
      "text": "Clean extracted text...",
      "page_number": 1,
      "order_index": 0
    },
    {
      "type": "table",
      "text": "Table Schema: Columns: Name, Value | Rows: 3...",
      "table": {"rows": [["Name", "Value"], ["Item1", "100"]]},
      "bbox": [50, 100, 550, 300]
    }
  ],
  "chunks": [
    {
      "chunk_id": "uuid-1234",
      "doc_id": "a1b2c3...",
      "text": "[Section: Introduction] Clean extracted text...",
      "metadata": {
        "page_number": 1,
        "section_title": "Introduction",
        "is_table": false
      }
    }
  ],
  "metadata": {
    "language": "en",
    "pages_count": 5,
    "warnings": []
  }
}
```

---

## 📦 Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd local_rag_parser
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the API**
   ```bash
   python -m api
   ```

   API will be available at `http://localhost:8000`

---

## 🔧 Usage

### API Endpoint

**POST** `/parse`

Upload a document and receive structured JSON with chunks.

**Parameters:**
- `file` (required) - Document file (PDF, DOCX, Excel, Image)
- `ocr_enabled` (optional, default: `true`) - Enable OCR for scanned documents
- `max_pages` (optional) - Limit number of pages to process

**Example with cURL:**
```bash
curl -X POST http://localhost:8000/parse \
  -F "file=@document.pdf" \
  -F "ocr_enabled=true"
```

**Response:**
```json
{
  "initial_link": "http://localhost:8000/download/initial/1234567890.pdf",
  "parsed_link": "http://localhost:8000/download/parsed/1234567890.json",
  "content_type": "TEXT",
  "parsing_time_sec": 2.34
}
```

### Download Results

**GET** `/download/{path}`

Download original files or parsed JSON results.

**Example:**
```bash
# Download parsed JSON
curl http://localhost:8000/download/parsed/1234567890.json

# Download original file
curl http://localhost:8000/download/initial/1234567890.pdf
```

### CLI Usage

Parse a file directly from command line:

```bash
python src/main.py path/to/document.pdf
```

Output will be saved as `output_<doc_id>.json` in the current directory.

---

## 🏗️ Architecture

```
local_rag_parser/
├── api.py                      # FastAPI application
├── src/
│   ├── main.py                 # CLI entry point
│   ├── schemas.py              # Pydantic schemas
│   ├── core/
│   │   └── detector.py         # File type detection
│   ├── models/
│   │   └── models.py           # Data models (ParsedDocument, ContentUnit, Chunk)
│   ├── parsers/
│   │   ├── pdf_parser.py       # PDF parsing with OCR
│   │   ├── docx_parser.py      # DOCX parsing
│   │   ├── excel_parser.py     # Excel parsing
│   │   └── image_parser.py     # Image OCR
│   └── services/
│       ├── chunker.py          # Text chunking logic
│       ├── normalizer.py       # Text normalization
│       ├── table_serializer.py # Table to text conversion
│       ├── ocr_service.py      # OCR wrapper (EasyOCR)
│       ├── s3_service.py       # Local storage (S3 mock)
│       └── file_service.py     # Main processing orchestrator
└── local_storage/              # Parsed results storage
    ├── initial/                # Original uploaded files
    └── parsed/                 # JSON results with chunks
```

---

## ⚙️ Configuration

### Chunking Parameters

Edit in `api.py` or `src/main.py`:

```python
chunker = Chunker(
    chunk_size=1000,      # Max characters per chunk
    chunk_overlap=100     # Overlap between chunks
)
```

### OCR Settings

OCR is enabled by default. To disable:

```bash
curl -X POST http://localhost:8000/parse \
  -F "file=@document.pdf" \
  -F "ocr_enabled=false"
```

### Storage Location

Change storage path in `api.py`:

```python
s3_service = LocalS3Service(base_path="custom_storage")
```

---

## 🧪 Testing

### Test with Sample Files

```bash
# PDF
curl -X POST http://localhost:8000/parse -F "file=@data/sample.pdf"

# DOCX
curl -X POST http://localhost:8000/parse -F "file=@data/sample.docx"

# Excel
curl -X POST http://localhost:8000/parse -F "file=@data/sample.xlsx"
```

### Verify Output

Check `local_storage/parsed/*.json` for results.

---

## 🔍 Advanced Features

### Smart Table Handling

- **Header Detection**: Automatically detects if first row is prose vs. proper headers
- **Forward-Fill**: Fills empty cells with values from previous rows (useful for category columns)
- **Merged Cells**: Correctly handles Excel merged cells

### OCR Post-Processing

- **Letter Spacing Fix**: `"n i m p r o vement"` → `"improvement"`
- **Typo Correction**: `"rvn"` → `"run"`, `"eqwal"` → `"equal"`
- **Custom Dictionary**: Easily extend `OCR_FIXES` in `pdf_parser.py`

### Deduplication

- **Bbox-based**: Excludes text overlapping with table areas
- **Margin Control**: 5px margin to avoid edge cases (configurable)

---

## 📊 Performance

| Document Type | Avg. Time | Notes |
|---------------|-----------|-------|
| PDF (10 pages) | 2-3s | Without OCR |
| PDF (10 pages) | 8-12s | With OCR |
| DOCX (20 pages) | 1-2s | Fast |
| Excel (5 sheets) | 1-2s | Fast |
| Image (1 page) | 3-5s | OCR required |

*Tested on MacBook Pro M1, 16GB RAM*

---

## 🛠️ Troubleshooting

### OCR Not Working

Ensure EasyOCR is properly installed:
```bash
pip install easyocr
```

### Import Errors

Make sure you're running from the project root:
```bash
python -m api  # ✅ Correct
python api.py  # ❌ May cause import errors
```

### Memory Issues with Large PDFs

Limit pages:
```bash
curl -X POST http://localhost:8000/parse \
  -F "file=@large.pdf" \
  -F "max_pages=10"
```

---

## 📝 Dependencies

Core libraries:
- `fastapi` - Web framework
- `pdfplumber` - PDF extraction
- `python-docx` - DOCX parsing
- `openpyxl` - Excel parsing
- `easyocr` - OCR engine
- `pydantic` - Data validation
- `langdetect` - Language detection
- `pyspellchecker` - OCR error correction

See `requirements.txt` for full list.

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- [ ] Add support for PowerPoint (.pptx)
- [ ] Implement async OCR for better performance
- [ ] Add unit tests
- [ ] Support for more languages in OCR
- [ ] Vector embedding integration

---

## 📄 License

MIT License - feel free to use in your projects!

---

## 🙏 Acknowledgments

Built with:
- [pdfplumber](https://github.com/jsvine/pdfplumber) for PDF parsing
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) for OCR
- [FastAPI](https://fastapi.tiangolo.com/) for the API framework

---

## 📧 Contact

For questions or issues, please open a GitHub issue.

**Happy Parsing! 🚀**
# file_parser
