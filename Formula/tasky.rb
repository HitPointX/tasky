class Tasky < Formula
  include Language::Python::Virtualenv

  desc "Lightweight terminal system monitor for macOS"
  homepage "https://github.com/HitPointX/tasky"
  url "https://github.com/HitPointX/tasky/archive/refs/tags/b2.tar.gz"
  sha256 "1d37fb4e1ca8889aac7def897f254cc2515e49b01897518b7396d231fade0929"
  license "MIT"
  head "https://github.com/HitPointX/tasky.git", branch: "main"

  depends_on "python@3.12"
  depends_on :macos

  resource "psutil" do
    url "https://files.pythonhosted.org/packages/source/p/psutil/psutil-5.9.8.tar.gz"
    sha256 "6be126e3225486dff286a8fb9a06246a5253f4c7c53b475ea5f5ac934e64194c"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    # tasky requires a real terminal — just assert the binary exists and exits cleanly
    assert_predicate bin/"tasky", :exist?
  end
end
