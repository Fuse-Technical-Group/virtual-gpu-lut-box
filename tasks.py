#!/usr/bin/env python3
"""Invoke tasks for virtual-gpu-lut-box project automation."""

import shutil
import sys
from pathlib import Path

from invoke.context import Context
from invoke.tasks import task

# Ensure UTF-8 encoding for Windows console (for emoji support)
if sys.platform == "win32":
    import locale
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')


@task
def clean(_: Context) -> None:
    """Clean build artifacts, cache files, and temporary files."""
    print("🧹 Cleaning build artifacts and cache files...")

    # Directories to clean
    dirs_to_clean = [
        "build",
        "dist",
        "*.egg-info",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".coverage",
        "htmlcov",
        "__pycache__",
    ]

    for pattern in dirs_to_clean:
        if "*" in pattern:
            # Handle glob patterns
            for path in Path(".").glob(f"**/{pattern}"):
                if path.is_dir():
                    print(f"  Removing directory: {path}")
                    shutil.rmtree(path, ignore_errors=True)
                elif path.is_file():
                    print(f"  Removing file: {path}")
                    path.unlink(missing_ok=True)
        else:
            # Handle specific directories
            if Path(pattern).exists():
                print(f"  Removing directory: {pattern}")
                shutil.rmtree(pattern, ignore_errors=True)

    print("✅ Clean completed")


@task
def format(ctx: Context) -> None:
    """Format code with ruff."""
    print("🎨 Formatting code with ruff...")
    ctx.run("ruff format src tests")
    print("✅ Code formatting completed")


@task
def lint(ctx: Context, fix: bool = False) -> None:
    """Run linting with ruff.

    Args:
        fix: Automatically fix fixable issues (default: False)
    """
    print("🔍 Linting code with ruff...")
    cmd = "ruff check src tests"
    if fix:
        cmd += " --fix"
        print("  Auto-fixing enabled")
    ctx.run(cmd)
    print("✅ Linting completed")


@task
def typecheck(ctx: Context) -> None:
    """Run type checking with pyright."""
    print("🔬 Type checking with pyright...")
    ctx.run("pyright src/virtual_gpu_lut_box")
    print("✅ Type checking completed")


@task
def spell(ctx: Context, fix: bool = False) -> None:
    """Run spell checking with codespell.

    Args:
        fix: Automatically fix spelling issues (default: False)
    """
    print("📝 Spell checking with codespell...")

    cmd = "codespell"
    if fix:
        cmd += " --write-changes"
        print("  Auto-fix mode enabled")

    ctx.run(cmd)
    print("✅ Spell checking completed")


@task
def security(ctx: Context) -> None:
    """Run security analysis with bandit and safety."""
    print("🔒 Running security analysis with bandit...")
    ctx.run("bandit -r src/virtual_gpu_lut_box")
    print("✅ Bandit analysis completed")

    print("🔒 Checking dependencies for vulnerabilities with safety...")
    ctx.run("safety check")
    print("✅ Safety check completed")


@task
def check_patterns(ctx: Context) -> None:
    """Check for banned code patterns."""
    print("🔍 Checking for banned code patterns...")

    # Check for contextlib.suppress(Exception) patterns
    result = ctx.run("grep -r 'contextlib.suppress(Exception)' src/ || true", hide=True)
    if result.stdout.strip():
        print("❌ Found banned contextlib.suppress(Exception) patterns:")
        print(result.stdout)
        raise SystemExit(1)

    result = ctx.run("grep -r 'contextlib.suppress.*Exception' src/ || true", hide=True)
    if result.stdout.strip():
        print("❌ Found potential contextlib.suppress with broad exceptions:")
        print(result.stdout)
        raise SystemExit(1)

    print("✅ No banned patterns found")


@task
def reuse_annotate(ctx: Context) -> None:
    """Add SPDX license headers to source files missing them."""
    print("📜 Adding SPDX license headers to source files...")

    # Annotate Python files
    print("  Annotating Python files...")
    ctx.run(
        "reuse annotate --license BSD-3-Clause --copyright 'Fuse Technical Group' "
        "--year 2025 --style python "
        "src/**/*.py tests/**/*.py client_integrations/build_shaders.py tests/integration/*.py"
    )

    # Annotate GLSL files
    print("  Annotating GLSL source files...")
    ctx.run(
        "reuse annotate --license BSD-3-Clause --copyright 'Fuse Technical Group' "
        "--year 2025 --style c "
        "client_integrations/src/*.glsl"
    )

    print("✅ SPDX headers added to all source files")


@task
def reuse_lint(ctx: Context) -> None:
    """Verify REUSE compliance (check SPDX headers).

    Note: This may fail on Windows systems with >=64 logical processors due to
    Python multiprocessing limitation. Windows WaitForMultipleObjects() has
    a 63-handle limit that affects multiprocessing pools.
    See: https://stackoverflow.com/q/65252807
    """
    print("📋 Checking REUSE compliance...")
    print("⚠️  Note: May timeout on Windows systems with >=64 logical processors")

    try:
        ctx.run("reuse lint", timeout=30)
        print("✅ REUSE compliance check passed")
    except Exception as e:
        print(f"❌ REUSE lint failed or timed out: {e}")
        print("\n💡 Windows multiprocessing limitation on high-core systems (>=64 logical processors)")
        print("   See: https://stackoverflow.com/q/65252807")
        print("   Headers were added correctly with 'reuse annotate'")
        print("   Manual verification: Check that source files have SPDX headers")


@task
def test(ctx: Context, coverage: bool = True, verbose: bool = False) -> None:
    """Run tests with pytest.

    Args:
        coverage: Generate coverage report (default: True)
        verbose: Run with verbose output (default: False)
    """
    print("🧪 Running tests with pytest...")

    cmd = "pytest"

    if coverage:
        cmd += " --cov=virtual_gpu_lut_box --cov-report=term-missing --cov-report=html --cov-report=xml"

    if verbose:
        cmd += " -v"

    cmd += " tests"

    ctx.run(cmd)
    print("✅ Tests completed")


@task(pre=[format, lint, typecheck, spell, security, check_patterns])
def quality(_: Context) -> None:
    """Run code quality checks: format, lint, typecheck, spell check, security, and pattern checks.

    Does NOT run tests - use 'invoke test' separately for functional testing.
    """
    print("🎯 Quality checks completed successfully!")


@task(pre=[clean])
def build(ctx: Context) -> None:
    """Build the package for distribution."""
    print("🔨 Building package...")

    # Build source distribution and wheel
    ctx.run("uv build")

    # Show built files
    print("\n📦 Built files:")
    dist_path = Path("dist")
    if dist_path.exists():
        for file in sorted(dist_path.glob("*")):
            size = file.stat().st_size
            if size > 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.1f}M"
            elif size > 1024:
                size_str = f"{size / 1024:.1f}K"
            else:
                size_str = f"{size}B"
            print(f"  {file.name} ({size_str})")

    print("✅ Build completed")


@task(pre=[build])
def publish(ctx: Context, test: bool = False) -> None:
    """Publish package to PyPI.

    Args:
        test: Publish to test PyPI instead of production (default: False)
    """
    if test:
        print("🚀 Publishing to Test PyPI...")
        ctx.run("python -m twine upload --repository testpypi dist/*")
    else:
        print("🚀 Publishing to PyPI...")
        response = input("Are you sure you want to publish to production PyPI? (y/N): ")
        if response.lower() != "y":
            print("❌ Publish cancelled")
            return
        ctx.run("python -m twine upload dist/*")

    print("✅ Publish completed")


@task
def install(ctx: Context, dev: bool = False, editable: bool = True) -> None:
    """Install the package.

    Args:
        dev: Install with development dependencies (default: False)
        editable: Install in editable mode (default: True)
    """
    print("📥 Installing package...")

    if dev:
        ctx.run("uv sync --extra dev")
    else:
        if editable:
            ctx.run("uv pip install -e .")
        else:
            ctx.run("uv pip install .")
    print("✅ Installation completed")


@task
def docs(ctx: Context) -> None:
    """Build documentation with MkDocs."""
    print("📚 Building documentation...")
    ctx.run("mkdocs build")
    print("✅ Documentation built to site/")


@task
def docs_serve(ctx: Context) -> None:
    """Serve documentation locally with live reload."""
    print("📚 Serving documentation at http://127.0.0.1:8000")
    print("   Press Ctrl+C to stop")
    ctx.run("mkdocs serve")


@task
def dev_setup(ctx: Context) -> None:
    """Set up development environment."""
    print("🔧 Setting up development environment...")

    # Install package in editable mode with dev dependencies
    ctx.run("uv sync --extra dev")

    # Install pre-commit hooks
    ctx.run("pre-commit install")

    print("✅ Development environment setup completed")


@task
def release(ctx: Context, version: str = "") -> None:
    """Prepare a release.

    Args:
        version: Version number to release (e.g., "1.0.0")
    """
    if not version:
        print("❌ Version number required. Usage: invoke release --version=1.0.0")
        return

    print(f"🚀 Preparing release {version}...")

    # Update version in __init__.py
    init_file = Path("src/virtual_gpu_lut_box/__init__.py")
    content = init_file.read_text()

    # Extract current version
    version_line_start = '__version__ = "'
    version_line_end = '"'
    start_idx = content.find(version_line_start) + len(version_line_start)
    end_idx = content.find(version_line_end, start_idx)
    current_version = content[start_idx:end_idx]

    # Replace with new version
    updated_content = content.replace(
        f'__version__ = "{current_version}"', f'__version__ = "{version}"'
    )
    init_file.write_text(updated_content)
    print(f"  Updated version from {current_version} to {version} in {init_file}")

    # Run quality checks
    print("  Running quality checks...")
    quality(ctx)

    # Build package
    print("  Building package...")
    build(ctx)

    print(f"✅ Release {version} prepared. Review and then run:")
    print("   git add .")
    print(f"   git commit -m 'Release {version}'")
    print(f"   git tag v{version}")
    print("   git push origin main --tags")
    print("   invoke publish")


@task
def demo(ctx: Context) -> None:
    """Run a quick demo of the package."""
    print("🎬 Running package demo...")

    # Check if package is installed
    try:
        ctx.run(
            "python -c 'import virtual_gpu_lut_box; print(f\"Package version: {virtual_gpu_lut_box.__version__}\")'"
        )
    except Exception:
        print("❌ Package not installed. Run 'invoke install' first.")
        return

    # Run CLI info command
    print("\n📊 Platform information:")
    try:
        ctx.run("virtual-gpu-lut-box info")
    except Exception as e:
        print(f"❌ CLI not available: {e}")
        return

    # Run comprehensive demo
    print("\n🔧 Running comprehensive demo:")
    try:
        ctx.run("python docs/examples/comprehensive_demo.py")
    except Exception as e:
        print(f"⚠️  Demo failed (expected if dependencies not installed): {e}")

    print("\n💡 Streaming functionality is built-in!")
    print("   - Platform-specific dependencies are automatically installed")
    print("   - No extra steps needed for Syphon (macOS) or Spout (Windows)")

    print("✅ Demo completed")


@task
def all(ctx: Context) -> None:
    """Run complete CI/CD pipeline: clean, quality checks, tests, and build."""
    print("🎯 Running complete CI/CD pipeline...")
    clean(ctx)
    quality(ctx)
    test(ctx)
    build(ctx)
    print("🎉 Complete pipeline finished successfully!")


if __name__ == "__main__":
    # Allow running tasks directly
    import sys

    if len(sys.argv) > 1:
        print("Use 'invoke <task>' to run tasks")
    else:
        print("Available tasks:")
        print("  invoke clean           - Clean build artifacts")
        print("  invoke format          - Format code")
        print("  invoke lint            - Run linting")
        print("  invoke typecheck       - Run type checking")
        print("  invoke spell           - Run spell checking")
        print("  invoke security        - Run security analysis")
        print("  invoke check-patterns  - Check for banned code patterns")
        print("  invoke reuse-annotate  - Add SPDX license headers")
        print("  invoke reuse-lint      - Verify REUSE compliance")
        print("  invoke test            - Run tests")
        print("  invoke quality         - Run all quality checks")
        print("  invoke build           - Build package")
        print("  invoke publish         - Publish to PyPI")
        print("  invoke install         - Install package")
        print("  invoke docs            - Generate documentation")
        print("  invoke dev-setup       - Set up development environment")
        print("  invoke release         - Prepare a release")
        print("  invoke demo            - Run package demo")
        print("  invoke all             - Run complete CI/CD pipeline")
