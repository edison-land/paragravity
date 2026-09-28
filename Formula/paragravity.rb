class Paragravity < Formula
  desc "Parallel multi-account and sandbox manager for Google Antigravity"
  homepage "https://github.com/edison-land/paragravity"
  url "https://github.com/edison-land/paragravity/archive/refs/tags/v1.2.0.tar.gz"
  sha256 "fde68373db43d003f44c8f1e878a8efa7db52e4fde98233ff45f5184d6f5f4eb"
  license "MIT"

  depends_on :macos

  def install
    bin.install "bin/paragravity"
    bin.install_symlink "paragravity" => "pgrav"

    # `pgrav web` imports web_server.py from the paragravity script's own
    # directory — it must ship alongside the CLI binary.
    bin.install "bin/web_server.py" if File.exist?("bin/web_server.py")

    # Install zsh completions if present
    if File.exist?("completions/_paragravity")
      zsh_completion.install "completions/_paragravity"
      zsh_completion.install_symlink "_paragravity" => "_pgrav"
    end
  end

  test do
    system bin/"paragravity", "--version"
    system bin/"pgrav", "--version"
  end
end
