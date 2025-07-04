# /// script
# dependencies = [
#   "requests<3",
#   "rich",
#   "typer",
#   "pathspec",
# ]
# ///

"""
Demonstrates how to display a tree of files / directories with the Tree renderable.
"""

import fnmatch
import os
import pathlib
from typing import Optional, List

import pathspec
import typer
from rich import print
from rich.filesize import decimal
from rich.markup import escape
from rich.text import Text
from rich.tree import Tree

app = typer.Typer()


def load_gitignore_patterns(directory: pathlib.Path) -> tuple[Optional[pathspec.PathSpec], Optional[pathlib.Path]]:
    """Load .gitignore patterns from the directory and its parents.
    
    Returns:
        A tuple of (PathSpec, git_root_directory) where git_root_directory is the 
        root of the git repository where gitignore patterns should be evaluated from.
    """
    patterns = []
    current_dir = directory
    git_root = None
    
    # Walk up the directory tree looking for .gitignore files
    while True:
        gitignore_path = current_dir / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, "r") as f:
                patterns.extend(f.read().splitlines())
        
        # Check if we've reached a git repository root
        if (current_dir / ".git").exists():
            git_root = current_dir
            break
            
        # Check if we've reached the filesystem root
        if current_dir.parent == current_dir:
            # If we found gitignore files but no .git directory, use the starting directory
            if patterns and git_root is None:
                git_root = directory
            break
            
        current_dir = current_dir.parent
    
    if patterns:
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns), git_root
    return None, None


def walk_directory(
    directory: pathlib.Path, 
    tree: Tree, 
    exclude_patterns: Optional[List[str]] = None,
    gitignore_spec: Optional[pathspec.PathSpec] = None,
    git_root: Optional[pathlib.Path] = None,
    show_links: bool = True,
    show_hidden: bool = False,
    max_depth: Optional[int] = None,
    current_depth: int = 0,
) -> None:
    """Recursively build a Tree with directory contents."""
    # Check if we've reached the maximum depth
    if max_depth is not None and current_depth >= max_depth:
        return
    # Sort dirs first then by filename
    paths = sorted(
        pathlib.Path(directory).iterdir(),
        key=lambda path: (path.is_file(), path.name.lower()),
    )
    for path in paths:
        # Skip hidden files unless show_hidden is True
        if not show_hidden and path.name.startswith("."):
            continue
            
        # Check gitignore patterns
        if gitignore_spec and git_root:
            # Get relative path from the git root for gitignore matching
            try:
                rel_path = path.relative_to(git_root)
                if gitignore_spec.match_file(str(rel_path)):
                    continue
            except ValueError:
                # If relative_to fails, skip this check
                pass
        
        # Check exclusion patterns
        if exclude_patterns:
            if any(fnmatch.fnmatch(path.name, pattern) for pattern in exclude_patterns):
                continue
            
        if path.is_dir():
            # Always show directories, but check if they contain matching files
            style = "dim" if path.name.startswith("__") else ""
            if show_links:
                dir_text = f"[bold magenta]:open_file_folder: [link file://{path}]{escape(path.name)}"
            else:
                dir_text = f"[bold magenta]:open_file_folder: {escape(path.name)}"
            branch = tree.add(
                dir_text,
                style=style,
                guide_style=style,
            )
            walk_directory(
                path, branch, exclude_patterns, gitignore_spec, git_root,
                show_links, show_hidden, max_depth, current_depth + 1
            )
        else:
            text_filename = Text(path.name, "green")
            text_filename.highlight_regex(r"\..*$", "bold red")
            if show_links:
                text_filename.stylize(f"link file://{path}")
            file_size = path.stat().st_size
            text_filename.append(f" ({decimal(file_size)})", "blue")
            icon = "🐍 " if path.suffix == ".py" else "📄 "
            tree.add(Text(icon) + text_filename)


@app.command()
def main(
    directory: str = typer.Argument(
        ".",
        help="Directory to display as a tree",
    ),
    exclude: Optional[List[str]] = typer.Option(
        None,
        "--exclude",
        "-e",
        help="Glob patterns to exclude (e.g., '*.pyc', '__pycache__')",
    ),
    depth: Optional[int] = typer.Option(
        None,
        "--depth",
        "-d",
        help="Maximum depth to traverse",
    ),
    show_hidden: bool = typer.Option(
        False,
        "--show-hidden",
        "-a",
        help="Show hidden files (starting with .)",
    ),
    links: bool = typer.Option(
        False,
        "--links",
        "-l",
        help="Enable clickable file links",
    ),
    gitignore: bool = typer.Option(
        False,
        "--gitignore",
        "-g", 
        help="Respect .gitignore files",
    ),
) -> None:
    """Display a tree of files and directories with Rich formatting."""
    dir_path = pathlib.Path(directory).resolve()
    
    if not dir_path.exists():
        typer.echo(f"Error: Directory '{directory}' does not exist.", err=True)
        raise typer.Exit(1)
    
    if not dir_path.is_dir():
        typer.echo(f"Error: '{directory}' is not a directory.", err=True)
        raise typer.Exit(1)
    
    # Load gitignore patterns if requested
    gitignore_spec = None
    git_root = None
    if gitignore:
        gitignore_spec, git_root = load_gitignore_patterns(dir_path)
    
    if links:
        root_text = f":open_file_folder: [link file://{dir_path}]{dir_path}"
    else:
        root_text = f":open_file_folder: {dir_path}"
    
    tree = Tree(
        root_text,
        guide_style="bold bright_blue",
    )
    walk_directory(
        dir_path, tree, exclude, gitignore_spec, git_root,
        links, show_hidden, depth, 0
    )
    print(tree)


if __name__ == "__main__":
    app()


# Tests
def test_walk_directory_with_exclude(tmp_path):
    """Test that exclude patterns filter files correctly."""
    # Create test directory structure
    (tmp_path / "test.py").write_text("python file")
    (tmp_path / "test.txt").write_text("text file")
    (tmp_path / "data.json").write_text("{}")
    
    from rich.tree import Tree
    from rich.console import Console
    import io
    
    tree = Tree("root")
    
    # Test excluding txt and json files
    walk_directory(tmp_path, tree, exclude_patterns=["*.txt", "*.json"], show_links=False, show_hidden=False)
    
    # Render tree to string
    console = Console(file=io.StringIO(), width=120)
    console.print(tree)
    tree_str = console.file.getvalue()
    
    assert "test.py" in tree_str
    assert "test.txt" not in tree_str
    assert "data.json" not in tree_str


def test_walk_directory_hidden_files(tmp_path):
    """Test that hidden files are shown/hidden correctly."""
    # Create test files
    (tmp_path / "visible.txt").write_text("visible")
    (tmp_path / ".hidden.txt").write_text("hidden")
    
    from rich.tree import Tree
    from rich.console import Console
    import io
    
    # Test without hidden files
    tree1 = Tree("root")
    walk_directory(tmp_path, tree1, show_links=False, show_hidden=False)
    console1 = Console(file=io.StringIO(), width=120)
    console1.print(tree1)
    tree1_str = console1.file.getvalue()
    assert "visible.txt" in tree1_str
    assert ".hidden.txt" not in tree1_str
    
    # Test with hidden files
    tree2 = Tree("root")
    walk_directory(tmp_path, tree2, show_links=False, show_hidden=True)
    console2 = Console(file=io.StringIO(), width=120)
    console2.print(tree2)
    tree2_str = console2.file.getvalue()
    assert "visible.txt" in tree2_str
    assert ".hidden.txt" in tree2_str


def test_main_invalid_directory():
    """Test that invalid directory raises error."""
    from typer.testing import CliRunner
    runner = CliRunner()
    
    result = runner.invoke(app, ["/nonexistent/path"])
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_main_file_instead_of_directory(tmp_path):
    """Test that passing a file instead of directory raises error."""
    from typer.testing import CliRunner
    runner = CliRunner()
    
    # Create a file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")
    
    result = runner.invoke(app, [str(test_file)])
    assert result.exit_code == 1
    assert "is not a directory" in result.output


def test_walk_directory_depth_limit(tmp_path):
    """Test that depth limit works correctly."""
    # Create nested directory structure
    (tmp_path / "level1").mkdir()
    (tmp_path / "level1" / "file1.txt").write_text("level 1")
    (tmp_path / "level1" / "level2").mkdir()
    (tmp_path / "level1" / "level2" / "file2.txt").write_text("level 2")
    (tmp_path / "level1" / "level2" / "level3").mkdir()
    (tmp_path / "level1" / "level2" / "level3" / "file3.txt").write_text("level 3")
    
    from rich.tree import Tree
    from rich.console import Console
    import io
    
    # Also create a file at the root level
    (tmp_path / "root_file.txt").write_text("root level")
    
    # Test with depth limit of 2 (shows content up to 2 levels deep)
    tree = Tree("root")
    walk_directory(tmp_path, tree, show_links=False, max_depth=2)
    console = Console(file=io.StringIO(), width=120)
    console.print(tree)
    tree_str = console.file.getvalue()
    
    # Depth 0: root level
    assert "root_file.txt" in tree_str
    assert "level1" in tree_str
    
    # Depth 1: inside level1
    assert "file1.txt" in tree_str
    assert "level2" in tree_str
    
    # Depth 2: we stop here, so level2 is shown but not its contents
    assert "file2.txt" not in tree_str
    assert "level3" not in tree_str
    assert "file3.txt" not in tree_str


def test_main_help():
    """Test that help command works."""
    from typer.testing import CliRunner
    runner = CliRunner()
    
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    # Just verify we get some help output with the description
    assert "Display a tree of files and directories" in result.output
