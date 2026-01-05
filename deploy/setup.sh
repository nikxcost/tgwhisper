#!/bin/bash
# Initial setup script for Beget deployment
# Run this once after cloning the repository to the server

set -e

echo "=== TGWhisper Bot Deployment Setup ==="
echo ""

# Get current directory (should be project root on Beget)
PROJECT_DIR=$(pwd)
echo "Project directory: $PROJECT_DIR"

# Check Python version
echo ""
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version)
echo "Found: $PYTHON_VERSION"

# Verify Python 3.8+
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PYTHON_MINOR" -lt 8 ]; then
    echo "WARNING: Python 3.8 or higher is recommended"
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo ""
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt --quiet
echo "✓ Dependencies installed"

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p logs
mkdir -p backups
echo "✓ Directories created"

# Set up .env file if doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file from template..."
    cat > .env << 'EOF'
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=

# API Keys
OPENROUTER_API_KEY=
GROQ_API_KEY=

# Database
DATABASE_URL=sqlite:///bot_database.db

# Logging
LOG_LEVEL=INFO
EOF
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file with your API keys!"
    echo "   Use: nano .env"
else
    echo ""
    echo "✓ .env file already exists"
fi

# Initialize database
echo ""
echo "Initializing database..."
python3 -c "from database.database import init_db; init_db()" 2>&1
echo "✓ Database initialized"

# Make scripts executable
echo ""
echo "Making deployment scripts executable..."
chmod +x deploy/*.sh
echo "✓ Scripts are now executable"

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env file with your API keys:"
echo "   nano .env"
echo ""
echo "2. Add the following tokens:"
echo "   - TELEGRAM_BOT_TOKEN (get from @BotFather)"
echo "   - OPENROUTER_API_KEY (get from openrouter.ai)"
echo "   - GROQ_API_KEY (get from console.groq.com)"
echo ""
echo "3. Test the bot manually:"
echo "   source venv/bin/activate"
echo "   python3 main.py"
echo ""
echo "4. If bot works, stop it (Ctrl+C) and set up cron:"
echo "   crontab -e"
echo "   Add this line (replace with your actual path):"
echo "   */3 * * * * $PROJECT_DIR/deploy/supervisor.sh"
echo ""
echo "5. Check bot status:"
echo "   ./deploy/check_status.sh"
echo ""
