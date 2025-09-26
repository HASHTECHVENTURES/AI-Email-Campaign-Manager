#!/bin/bash
# AI Email Campaign Manager - Installation Script

echo "🚀 Installing AI Email Campaign Manager..."
echo "=========================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9+ first."
    exit 1
fi

echo "✅ Python 3 found"

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "To start the application:"
echo "  python3 app.py"
echo ""
echo "Then open your browser to:"
echo "  http://localhost:5008"
echo ""
echo "Happy email campaigning! 🚀"
