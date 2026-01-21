# Jellyfin Codec Analyzer
A small command-line tool to analyze video codecs in a Jellyfin media library. It queries the Jellyfin server, inspects media stream information for movies and episodes, and summarizes codecs, counts, and sizes. The tool also supports an interactive mode to explore and export results.

The primary intended use of this tool is to find your biggest files using inefficient codecs and replace or re-encode them to save space or bandwidth.

**Key features**
- Analyze video codecs across your Jellyfin library
- Show counts, total sizes, and percentages per codec
- List files grouped by codec and optionally filter by codec
- Save summary or per-file lists to CSV or JSON
- Interactive TUI-style mode for quick exploration

Requirements
------------
- Python 3.6+
- Linux or Unix-like system (macOS, BSD, etc.)
- Jellyfin server with API access

Installation
------------
The recommended installation method is via PyPI:
```bash
pip install jellycodec
```

If you're working from the repository (developer or local install), install with:
```bash
pip install .
```

After installation the `jellycodec` command will be available on your PATH; run it with `jellycodec -h` for usage.

Configuration
-------------
The script reads the Jellyfin server URL and API key from environment variables or command-line flags.

**Set environment variables:**

```bash
export JELLYFIN_SERVER=http://localhost:8096
export JELLYFIN_API_KEY=your_api_key_here
```

To make them persistent, add the export commands to your shell configuration file (`~/.bashrc`, `~/.zshrc`, or `~/.profile`):

Then reload your shell configuration:
```bash
source ~/.bashrc  # or ~/.zshrc or ~/.profile, depending on your shell
```

**Getting your Jellyfin API Key:**
1. Log into your Jellyfin web interface
2. Go to Dashboard → API Keys
3. Click "+" to create a new API key
4. Copy the generated key

Usage
-----
Run the analyzer directly:
```bash
jellycodec
```

Or with command-line arguments to override environment variables:
```bash
jellycodec -s http://your-server:8096 -k YOUR_API_KEY
```

Common options:
- `-s`, `--server`: Jellyfin server URL (or set `JELLYFIN_SERVER` env var)
- `-k`, `--api-key`: Jellyfin API key (or set `JELLYFIN_API_KEY` env var)
- `-i`, `--interactive`: Run in interactive mode (menu-driven)
- `-l`, `--list-files`: List all files grouped by codec
- `-c`, `--codec`: Filter listed files by codec (use with `-l`)
- `-o`, `--output`: Save codec summary to a file
- `-d`, `--detailed`: Show percentages and detailed output

Examples
--------

Analyze library and print summary (using environment variables):
```bash
jellycodec
```

Analyze with explicit credentials:
```bash
jellycodec -s http://localhost:8096 -k ABCDEFGHIJK
```

Run interactive mode (recommended for exploring and exporting):
```bash
jellycodec -i
```

List files for a specific codec:
```bash
jellycodec -l -c "HEVC (H.265)"
```

Save codec summary to `codecs.txt`:
```bash
jellycodec -o codecs.txt -d
```

One-time run with inline environment variables:
```bash
JELLYFIN_SERVER=http://localhost:8096 JELLYFIN_API_KEY=your_key jellycodec -i
```

Interactive Mode
----------------
When launched with `-i`, the script fetches all movie/episode items once and provides a simple menu where you can:
- View codec statistics (counts, total size)
- View detailed statistics with percentages
- List files grouped by codec
- List files for a selected codec
- Export file lists (CSV or JSON)

The interactive flow is useful when you want to quickly inspect which files use a particular codec and export results for further analysis.

Output and Exports
------------------
- Summary output shows total videos analyzed and aggregated size (human-readable).
- File lists can be saved in CSV (recommended) or JSON formats.
- The script attempts to use `MediaSources` entry to determine file sizes; when size information is missing the size will be reported as `Unknown`.

Development & Contributing
--------------------------
Contributions and improvements welcome. Open an issue or submit a pull request with fixes or enhancements (e.g., support for additional item types, more robust size detection, or unit tests).

License
-------
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.