# Global command-line utilities

# Default recipe - show available commands
default:
    @just -f {{justfile()}} --list

# Quick HTTP server on port 8000
serve port="8000":
    python3 -m http.server {{port}}

# Show my public IP
myip:
    @curl -s https://api.ipify.org && echo

# Write a new blog post
[group('blog')]
[working-directory: '/Users/vincentwarmerdam/Development/blog']
write:
    uvx --from "python-dotenv[cli]" dotenv run -- uvx --with git+https://github.com/koaning/draft draft --write-folder /Users/vincentwarmerdam/Development/blog/content/posts/2025

# Deploy the blog
[group('blog')]
[working-directory: '/Users/vincentwarmerdam/Development/blog']
deploy:
    make deploy

# Extract various archive formats
extract file:
    #!/usr/bin/env bash
    if [ -f "{{file}}" ]; then
        case "{{file}}" in
            *.tar.bz2) tar xjf "{{file}}" ;;
            *.tar.gz)  tar xzf "{{file}}" ;;
            *.tar.xz)  tar xJf "{{file}}" ;;
            *.tar)     tar xf "{{file}}" ;;
            *.zip)     unzip "{{file}}" ;;
            *.gz)      gunzip "{{file}}" ;;
            *.bz2)     bunzip2 "{{file}}" ;;
            *.rar)     unrar x "{{file}}" ;;
            *.7z)      7z x "{{file}}" ;;
            *)         echo "Don't know how to extract {{file}}" ;;
        esac
    else
        echo "{{file}} is not a valid file"
    fi

# Kill process by port
freeport port:
    lsof -ti:{{port}} | xargs kill -9

# Show disk usage in human-readable format
diskusage path=".":
    du -sh {{path}}/* | sort -hr | head -20

# List the directory tree
tree depth="1":
    uv run {{justfile_directory()}}/rich-ls.py . --depth {{depth}} --gitignore


commit:
    git commit -m "$(git --no-pager diff | uvx llm "Write a commit message for the following git diff. The message needs to be 7 words max. Keep it short and concise.")"
