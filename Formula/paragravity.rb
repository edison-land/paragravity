class Paragravity < Formula
  desc "Parallel multi-account and sandbox manager for Google Antigravity"
  homepage "https://github.com/edison-land/paragravity"
  url "https://github.com/edison-land/paragravity/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "530b1112a0f5a232906aae898de5a00a0dafb8ee510e84f510c70c48fbaae466"
  license "MIT"

  depends_on :macos

  def install
    bin.install "bin/paragravity"
    bin.install_symlink "paragravity" => "pgrav"

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
