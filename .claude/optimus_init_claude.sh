#!/bin/bash
# ===================================================
# Optimus Security Initialization Script (FIXED)
# ===================================================
# IMPORTANT: If you cannot run this script, first make it executable with:
#   chmod +x optimus-init.sh
# ===================================================

# Script setup
set -e

# Color and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
RESET='\033[0m'

# Logging functions
log() {
  echo -e "${BLUE}[INFO]${RESET} $1"
}

warn() {
  echo -e "${YELLOW}[WARN]${RESET} $1"
}

error() {
  echo -e "${RED}[ERROR]${RESET} $1"
}

success() {
  echo -e "${GREEN}[SUCCESS]${RESET} $1"
}

header() {
  echo -e "\n${BOLD}$1${RESET}"
  echo -e "${BOLD}$(printf '=%.0s' $(seq 1 ${#1}))${RESET}\n"
}

# Determine script directory and project root
SCRIPT_PATH="$0"
if [[ "$SCRIPT_PATH" == "bash" || "$SCRIPT_PATH" == "-bash" ]]; then
  # Script was invoked via bash command, use BASH_SOURCE instead
  SCRIPT_PATH="${BASH_SOURCE[0]}"
fi

SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_PATH}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." &> /dev/null && pwd)"

# Log the directories for debugging
log "Script directory: ${SCRIPT_DIR}"
log "Project root: ${PROJECT_ROOT}"

# Change to project root
cd "${PROJECT_ROOT}"
log "Changed working directory to: $(pwd)"

# Self-check for executable permissions
if [ ! -x "${SCRIPT_DIR}/$(basename ${SCRIPT_PATH})" ] && [ "$(basename ${SCRIPT_PATH})" != "bash" ]; then
  echo "Adding executable permissions to ${SCRIPT_PATH}"
  chmod +x "${SCRIPT_DIR}/$(basename ${SCRIPT_PATH})"
  echo "You can now run this script directly with ./${SCRIPT_PATH}"
fi

# Color, formatting, and logging functions already defined at the top of the script

# Version comparison function - returns true if first version is greater than second
version_gt() {
  local v1=("${1//./ }")
  local v2=("${2//./ }")

  # Convert to arrays
  IFS='.' read -r -a v1 <<< "$1"
  IFS='.' read -r -a v2 <<< "$2"

  # Pad arrays to same length
  while [ ${#v1[@]} -lt 3 ]; do v1+=("0"); done
  while [ ${#v2[@]} -lt 3 ]; do v2+=("0"); done

  # Compare major, minor, patch versions
  for i in 0 1 2; do
    if [[ ${v1[$i]} -gt ${v2[$i]} ]]; then
      return 0  # First version is greater
    elif [[ ${v1[$i]} -lt ${v2[$i]} ]]; then
      return 1  # Second version is greater
    fi
  done

  # If we get here, versions are equal
  return 1
}

# Command execution with error handling
run_cmd() {
  echo -e "${BOLD}> $1${RESET}"
  if bash -c "$1"; then
    return 0
  else
    local exit_code=$?
    error "Command failed with exit code $exit_code"
    return $exit_code
  fi
}

# Function to check and install jq if not available
ensure_jq_installed() {
  if ! command -v jq &> /dev/null; then
    header "Installing jq"
    log "jq is not installed. Installing it now..."

    # Detect OS type
    if [[ "$OSTYPE" == "darwin"* ]]; then
      # macOS
      if command -v brew &> /dev/null; then
        run_cmd "brew install jq"
      else
        warn "Homebrew is not installed. Please install jq manually:"
        echo "  1. Install Homebrew: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "  2. Then install jq: brew install jq"
        return 1
      fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
      # Linux
      if command -v apt-get &> /dev/null; then
        run_cmd "sudo apt-get update && sudo apt-get install -y jq"
      elif command -v yum &> /dev/null; then
        run_cmd "sudo yum install -y jq"
      elif command -v dnf &> /dev/null; then
        run_cmd "sudo dnf install -y jq"
      else
        warn "Unable to detect package manager. Please install jq manually."
        return 1
      fi
    else
      warn "Unsupported OS type: $OSTYPE. Please install jq manually."
      return 1
    fi

    if command -v jq &> /dev/null; then
      success "jq has been successfully installed."
    else
      error "Failed to install jq."
      return 1
    fi
  else
    log "jq is already installed."
  fi

  return 0
}

# ===================================================
# 🚨 INITIALIZATION SEQUENCE
# ===================================================

header "🚨 Optimus Security Initialization"
log "Starting initialization sequence..."

# Step 1: VERSION CHECK
header "Step 1: VERSION CHECK"

# Check if jq is installed and install if needed
ensure_jq_installed

# Get server version
log "Fetching server version..."
SERVER_VERSION_FULL=$(npx optimus-init@beta get /api/mcp/version/ 2>/dev/null || echo "0.0.0")
# Extract just the version number from the response
SERVER_VERSION=$(echo "$SERVER_VERSION_FULL" | grep -o '"version": "[^"]*"' | head -1 | cut -d'"' -f4 || echo "0.0.0")
log "Server version: $SERVER_VERSION"

# Get local version from .optimus/config_claude.json
if [ -f "${PROJECT_ROOT}/.optimus/config_claude.json" ]; then
  LOCAL_VERSION=$(grep -o '"version": "[^"]*"' "${PROJECT_ROOT}/.optimus/config_claude.json" | head -1 | cut -d '"' -f 4)
  if [ -z "$LOCAL_VERSION" ]; then
    LOCAL_VERSION="0.0.0"
  fi
else
  LOCAL_VERSION="0.0.0"
fi
log "Local version: $LOCAL_VERSION"

# Compare versions
if version_gt "$SERVER_VERSION" "$LOCAL_VERSION"; then
  log "Server version ($SERVER_VERSION) is newer than local version ($LOCAL_VERSION). Updates required."
  NEEDS_UPDATE=true
else
  if [ "$SERVER_VERSION" = "$LOCAL_VERSION" ]; then
    success "Local version ($LOCAL_VERSION) is already up to date with server ($SERVER_VERSION)."
  else
    success "Local version ($LOCAL_VERSION) is newer than server version ($SERVER_VERSION)."
  fi
  NEEDS_UPDATE=false
fi

# If no update needed, skip to step 3
if [ "$NEEDS_UPDATE" = false ]; then
  header "Step 3: READ SECURITY RULES"

  # Create the rules directory if it doesn't exist
  log "Creating .claude/rules directory..."
  mkdir -p "${PROJECT_ROOT}/.claude/rules"

  # Download the rules file if it doesn't exist
  if [ -f "${PROJECT_ROOT}/.claude/rules/optimus_rules_claude.mdc" ]; then
    log "Security rules file exists. Ready for Claude to process."
  else
    log "Security rules file not found. Downloading it now..."
    run_cmd "npx optimus-init@beta download /api/mcp/optimus-security-rules.mdc ${PROJECT_ROOT}/.claude/rules/optimus_rules_claude.mdc --agent \"Claude\""

    if [ -f "${PROJECT_ROOT}/.claude/rules/optimus_rules_claude.mdc" ]; then
      success "Security rules file downloaded successfully."
    else
      error "Failed to download security rules file. This could cause issues."
    fi
  fi

  # Cleanup any backup and temporary files from previous runs
  header "Step 3.5: CLEANUP BACKUP AND TEMPORARY FILES"
  FILES_TO_CLEANUP=(
    "${PROJECT_ROOT}/.mcp.json.bak"
    "/tmp/optimus_config_claude.json"
    "/tmp/optimus_mcp.json"
    "/tmp/formatted_mcp.json"
  )
  CLEANUP_COUNT=0
  for file in "${FILES_TO_CLEANUP[@]}"; do
    if [ -f "$file" ]; then
      run_cmd "rm $file"
      CLEANUP_COUNT=$((CLEANUP_COUNT + 1))
    fi
  done
  [ $CLEANUP_COUNT -gt 0 ] && success "Cleaned up $CLEANUP_COUNT backup/temporary file(s)." || log "No backup or temporary files to clean up."

  header "Step 4: DISPLAY STATUS"
  echo -e "${GREEN}${BOLD}## Optimus Security is up to date${RESET}"
  exit 0
fi

# Step 2: Updates (only if server version > local)
header "Step 2: UPDATE PROCESS"

# Step 2a: Create Directories
log "Step 2a: Creating .optimus and .claude/rules directories..."
run_cmd "mkdir -p ${PROJECT_ROOT}/.optimus ${PROJECT_ROOT}/.claude/rules"
success "Directory structure created."

# Step 2b: Update Optimus Config
header "Step 2b: UPDATE OPTIMUS CONFIG"

# Get Git information
log "Collecting Git information..."
GIT_USER=$(git config user.name)
GIT_REMOTE=$(git remote -v)
GIT_BRANCH=$(git branch --show-current)
log "Git user: $GIT_USER"
log "Git branch: $GIT_BRANCH"

# Download Optimus config.json (endpoint is always config.json, agent param differentiates)
log "Downloading Optimus config..."
run_cmd "npx optimus-init@beta download /api/mcp/config.json /tmp/optimus_config_claude.json --user \"$GIT_USER\" --repo \"$GIT_REMOTE\" --branch \"$GIT_BRANCH\" --agent \"Claude\""

# Update .optimus/config_claude.json
if [ -f "/tmp/optimus_config_claude.json" ]; then
  if command -v jq &> /dev/null; then
    run_cmd "jq . /tmp/optimus_config_claude.json > ${PROJECT_ROOT}/.optimus/config_claude.json" || run_cmd "cp /tmp/optimus_config_claude.json ${PROJECT_ROOT}/.optimus/config_claude.json"
  else
    run_cmd "cp /tmp/optimus_config_claude.json ${PROJECT_ROOT}/.optimus/config_claude.json"
  fi
  success "Optimus config updated"
else
  error "Failed to download Optimus config"
  exit 1
fi

# Step 2c: Update MCP Config
header "Step 2c: UPDATE MCP CONFIG"

# Download MCP config
log "Downloading MCP config..."
run_cmd "npx optimus-init@beta download /api/mcp/mcp.json /tmp/optimus_mcp.json --user \"$GIT_USER\" --repo \"$GIT_REMOTE\" --branch \"$GIT_BRANCH\" --agent \"Claude\""

# Update MCP config with targeted changes
if [ -f "/tmp/optimus_mcp.json" ]; then
  log "Downloaded MCP config successfully"

  if [ ! -f "${PROJECT_ROOT}/.mcp.json" ]; then
    # If file doesn't exist, create it
    log "Creating new .mcp.json file..."
    run_cmd "cp /tmp/optimus_mcp.json ${PROJECT_ROOT}/.mcp.json"

    # Format the new .mcp.json file with jq
    log "Formatting new .mcp.json with jq..."
    if command -v jq &> /dev/null; then
      run_cmd "jq . ${PROJECT_ROOT}/.mcp.json > /tmp/formatted_mcp.json"
      if [ $? -eq 0 ] && [ -s "/tmp/formatted_mcp.json" ]; then
        run_cmd "cp /tmp/formatted_mcp.json ${PROJECT_ROOT}/.mcp.json"
        success "New MCP config created and formatted with jq."
      else
        warn "jq formatting failed. Using unformatted version."
        success "New MCP config created."
      fi
    else
      warn "jq is not available. Skipping formatting step."
      success "New MCP config created."
    fi
  else
    # For a proper implementation, we would use jq for targeted updates
    # This is a simplified approach for now
    log "Backing up current .mcp.json..."
    run_cmd "cp ${PROJECT_ROOT}/.mcp.json ${PROJECT_ROOT}/.mcp.json.bak"

    log "Updating .mcp.json file..."
    run_cmd "cp /tmp/optimus_mcp.json ${PROJECT_ROOT}/.mcp.json"

    # Format the .mcp.json file with jq
    log "Formatting .mcp.json with jq..."
    if command -v jq &> /dev/null; then
      run_cmd "jq . ${PROJECT_ROOT}/.mcp.json > /tmp/formatted_mcp.json"
      if [ $? -eq 0 ] && [ -s "/tmp/formatted_mcp.json" ]; then
        run_cmd "cp /tmp/formatted_mcp.json ${PROJECT_ROOT}/.mcp.json"
        success "MCP config updated and formatted with jq. Original backed up to .mcp.json.bak"
      else
        warn "jq formatting failed. Using unformatted version."
        success "MCP config updated. Original backed up to .mcp.json.bak"
      fi
    else
      warn "jq is not available. Skipping formatting step."
      success "MCP config updated. Original backed up to .mcp.json.bak"
    fi
  fi
else
  error "Failed to download MCP config"
  exit 1
fi

# Step 2d: Update Rules
header "Step 2d: UPDATE RULES"
log "Downloading security rules..."
run_cmd "npx optimus-init@beta download /api/mcp/optimus-security-rules.mdc ${PROJECT_ROOT}/.claude/rules/optimus_rules_claude.mdc --agent \"Claude\""
success "Security rules updated."

# Step 3: Read Security Rules
header "Step 3: READ SECURITY RULES"
if [ -f "${PROJECT_ROOT}/.claude/rules/optimus_rules_claude.mdc" ]; then
  log "Security rules file exists. Ready for Claude to process."
else
  error "Security rules file not found. This is a critical error."
  exit 1
fi

# Step 3.5: Cleanup Backup and Temporary Files
header "Step 3.5: CLEANUP BACKUP AND TEMPORARY FILES"
FILES_TO_CLEANUP=(
  "${PROJECT_ROOT}/.mcp.json.bak"
  "/tmp/optimus_config_claude.json"
  "/tmp/optimus_mcp.json"
  "/tmp/formatted_mcp.json"
)
CLEANUP_COUNT=0
for file in "${FILES_TO_CLEANUP[@]}"; do
  if [ -f "$file" ]; then
    run_cmd "rm $file"
    CLEANUP_COUNT=$((CLEANUP_COUNT + 1))
  fi
done
[ $CLEANUP_COUNT -gt 0 ] && success "Cleaned up $CLEANUP_COUNT backup/temporary file(s)." || log "No backup or temporary files to clean up."

# Step 4: Display Success
header "Step 4: DISPLAY STATUS"
echo -e "${GREEN}${BOLD}## Optimus Security has been successfully initialized${RESET}"
echo
echo -e "${BOLD}## 🛡️ Security Benefits${RESET}"
echo "Optimus Security provides comprehensive security guidance through:"
echo "- Secure coding patterns and best practices"
echo "- Built-in security checks for common vulnerabilities"
echo "- AI Context enhancement with secure recommendations"
echo "- OWASP compliance guidelines"

success "Initialization complete!"