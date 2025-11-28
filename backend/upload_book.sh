#!/bin/bash
# Quick script to ingest your romance book PDF into Luna's knowledge base

# Check if PDF path was provided
if [ -z "$1" ]; then
    echo "Usage: ./upload_book.sh <path-to-book.pdf> \"Book Title\""
    echo ""
    echo "Example:"
    echo "  ./upload_book.sh docs/attached.pdf \"Attached: The Science of Adult Attachment\""
    exit 1
fi

# Check if book title was provided
if [ -z "$2" ]; then
    echo "Error: Please provide a book title as the second argument"
    echo ""
    echo "Usage: ./upload_book.sh <path-to-book.pdf> \"Book Title\""
    exit 1
fi

PDF_PATH="$1"
BOOK_TITLE="$2"

# Check if file exists
if [ ! -f "$PDF_PATH" ]; then
    echo "Error: File not found: $PDF_PATH"
    exit 1
fi

echo "=================================================="
echo "📚 Uploading Romance Book to Luna's Knowledge Base"
echo "=================================================="
echo "PDF: $PDF_PATH"
echo "Title: $BOOK_TITLE"
echo ""
echo "This will:"
echo "  1. Extract text from PDF using OCR"
echo "  2. Detect chapters automatically"
echo "  3. Create smart chunks with chapter metadata"
echo "  4. Upload to Pinecone 'books' namespace"
echo ""
echo "⏳ This may take 5-10 minutes for large books..."
echo "=================================================="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the ingestion script
python scripts/ingest_romance_book.py "$PDF_PATH" "$BOOK_TITLE"

echo ""
echo "=================================================="
echo "✅ Upload complete!"
echo ""
echo "Luna can now reference this book when mediating."
echo "Try asking questions like:"
echo "  - 'What does this book say about attachment?'"
echo "  - 'What advice is in Chapter 3?'"
echo "=================================================="
