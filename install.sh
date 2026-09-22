#!/usr/bin/env bash
# ParaGravity One-Line Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/edison-land/paragravity/main/install.sh | bash

set -euo pipefail

REPO="${PARAGRAVITY_REPO:-edison-land/paragravity}"
BRANCH="${PARAGRAVITY_BRANCH:-main}"
INSTALL_DIR="${HOME}/.local/bin"
RAW_BASE="https://raw.githubusercontent.com/${REPO}/${BRANCH}"

echo -e "\033[1;36m==> Installing ParaGravity (pgrav)...\033[0m"

# Ensure macOS
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo -e "\033[31mError: ParaGravity currently supports macOS only.\033[0m"
    exit 1
fi

# Ensure Python 3
if ! command -v python3 &>/dev/null; then
    echo -e "\033[31mError: python3 is required but not found.\033[0m"
    exit 1
fi

mkdir -p "${INSTALL_DIR}"

echo " • Downloading paragravity binary to ${INSTALL_DIR}..."
curl -fsSL "${RAW_BASE}/bin/paragravity" -o "${INSTALL_DIR}/paragravity"
chmod +x "${INSTALL_DIR}/paragravity"

# Symlink pgrav alias
ln -sf "paragravity" "${INSTALL_DIR}/pgrav"

# Configure Shell PATH if needed (check the rc file itself, so re-running the
# installer never appends duplicate PATH lines)
SHELL_NAME="$(basename "${SHELL:-zsh}")"
RC_FILE=""

case "${SHELL_NAME}" in
    zsh)  RC_FILE="${HOME}/.zshrc" ;;
    bash) RC_FILE="${HOME}/.bash_profile" ;;
    fish) RC_FILE="${HOME}/.config/fish/config.fish" ;;
    *)    RC_FILE="${HOME}/.profile" ;;
esac

if [[ "${SHELL_NAME}" == "fish" ]]; then
    if ! grep -qsF 'set -gx PATH $HOME/.local/bin $PATH' "${RC_FILE}"; then
        echo " • Adding ${INSTALL_DIR} to PATH in ${RC_FILE}..."
        echo "set -gx PATH \$HOME/.local/bin \$PATH" >> "${RC_FILE}"
    fi
elif ! grep -qsF 'export PATH="$HOME/.local/bin:$PATH"' "${RC_FILE}"; then
    echo " • Adding ${INSTALL_DIR} to PATH in ${RC_FILE}..."
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "${RC_FILE}"
fi

echo ""
echo -e "\033[1;32m🎉 ParaGravity successfully installed!\033[0m"
echo ""
echo "Quick Start:"
echo "  1. Reload your shell:     source ${RC_FILE}"
echo "  2. Create a new profile:  paragravity create zwe"
echo "  3. List active profiles:  paragravity list"
echo "  4. Launch an instance:    paragravity launch zwe"
echo ""
echo -e "Tip: You can also use the short alias \033[1;36mpgrav\033[0m instead of \033[1;36mparagravity\033[0m!"
