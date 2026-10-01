#!/bin/bash
# =============================================================================
# コンタクトセンター チャットサービス - 環境セットアップスクリプト
# macOS 向け
# =============================================================================

set -e

echo "=========================================="
echo "  チャットサービス 環境セットアップ"
echo "=========================================="
echo ""

# ---------- 色付き出力ヘルパー ----------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

success() { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
error() { echo -e "${RED}✗ $1${NC}"; exit 1; }

# ---------- 1. Homebrew ----------
echo "--- 1. Homebrew の確認 ---"
if command -v brew &> /dev/null; then
    success "Homebrew はインストール済みです ($(brew --version | head -1))"
else
    warn "Homebrew が見つかりません。インストールします..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Apple Silicon の場合 PATH を通す
    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
    fi
    success "Homebrew をインストールしました"
fi
echo ""

# ---------- 2. Node.js (nvm経由) ----------
echo "--- 2. Node.js の確認 ---"
export NVM_DIR="$HOME/.nvm"

# nvm の確認・インストール
if [[ -s "$NVM_DIR/nvm.sh" ]]; then
    source "$NVM_DIR/nvm.sh"
    success "nvm はインストール済みです ($(nvm --version))"
else
    warn "nvm が見つかりません。インストールします..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
    source "$NVM_DIR/nvm.sh"
    success "nvm をインストールしました"
fi

# Node.js 24 の確認・インストール
if nvm ls 24 &> /dev/null; then
    success "Node.js 24 はインストール済みです"
else
    warn "Node.js 24 をインストールします..."
    nvm install 24
    success "Node.js 24 をインストールしました"
fi
nvm use 24
nvm alias default 24
success "Node.js $(node --version) を使用します"
echo ""

# ---------- 3. Python 3.12 ----------
echo "--- 3. Python の確認 ---"
PYTHON_CMD=""

# Python 3.12 を探す
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
    success "Python 3.12 はインストール済みです ($($PYTHON_CMD --version))"
elif command -v python3 &> /dev/null; then
    PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
    if [[ "$PY_VERSION" == "3.12" || "$PY_VERSION" == "3.13" ]]; then
        PYTHON_CMD="python3"
        success "Python ($($PYTHON_CMD --version)) はインストール済みです"
    else
        warn "Python $PY_VERSION が見つかりましたが、3.12 が推奨です。Homebrew でインストールします..."
        brew install python@3.12
        PYTHON_CMD="/opt/homebrew/bin/python3.12"
        success "Python 3.12 をインストールしました"
    fi
else
    warn "Python が見つかりません。Homebrew でインストールします..."
    brew install python@3.12
    PYTHON_CMD="/opt/homebrew/bin/python3.12"
    success "Python 3.12 をインストールしました"
fi
echo ""

# ---------- 4. SQLite ----------
echo "--- 4. SQLite の確認 ---"
# macOS には SQLite が標準で入っている
if command -v sqlite3 &> /dev/null; then
    success "SQLite はインストール済みです ($(sqlite3 --version | awk '{print $1}'))"
else
    warn "SQLite をインストールします..."
    brew install sqlite
    success "SQLite をインストールしました"
fi
echo ""

# ---------- 5. バックエンドセットアップ ----------
echo "--- 5. バックエンド (Python) セットアップ ---"
cd "$(dirname "$0")/backend"

if [[ -d "venv" ]]; then
    warn "既存の仮想環境を削除して再作成します..."
    rm -rf venv
fi

$PYTHON_CMD -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
success "Python 仮想環境を作成し、依存パッケージをインストールしました"
deactivate
cd ..
echo ""

# ---------- 6. フロントエンドセットアップ ----------
echo "--- 6. フロントエンド (React) セットアップ ---"
cd "$(dirname "$0")/frontend"
source "$NVM_DIR/nvm.sh"
nvm use 24 > /dev/null
npm install
success "npm パッケージをインストールしました"
cd ..
echo ""

# ---------- 完了 ----------
echo "=========================================="
echo -e "${GREEN}  セットアップ完了！${NC}"
echo "=========================================="
echo ""
echo "サービスの起動方法:"
echo ""
echo "  【バックエンド】"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  python -m app.main"
echo ""
echo "  【フロントエンド】（別ターミナル）"
echo "  cd frontend"
echo "  nvm use 24"
echo "  npm run dev"
echo ""
echo "  ブラウザで http://localhost:3000 にアクセス"
echo ""
echo "  初期ログイン情報:"
echo "    ユーザー名: admin"
echo "    パスワード: password123"
echo ""
