# Jellyfin Codec Analyzer

A small command-line tool to analyze video codecs in a Jellyfin media library. It queries the Jellyfin server, inspects media stream information for movies and episodes, and summarizes codecs, counts, and sizes. The tool also supports an interactive mode to explore and export results.

The primary intended use of this tool is to find your biggest files using inefficient codecs and replace or re-encode them to save space or bandwith.

**Key features**
- Analyze video codecs across your Jellyfin library
- Show counts, total sizes, and percentages per codec
- List files grouped by codec and optionally filter by codec
- Save summary or per-file lists to CSV or JSON
- Interactive TUI-style mode for quick exploration



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

**Configuration**

The script reads the Jellyfin server URL and API key from environment variables or command-line flags. Create a `.env` file in the same directory (optional) with the following values:

```
JELLYFIN_SERVER=http://localhost:8096
JELLYFIN_API_KEY=your_api_key_here
```

If `python-dotenv` is available the script will automatically load `.env` on startup and print a notice to stderr.

**Usage**

Run the analyzer directly:

```bash
python jellycodec.py -s http://your-server:8096 -k YOUR_API_KEY
```

Common options:
- `-s`, `--server`: Jellyfin server URL (or set `JELLYFIN_SERVER` env var)
- `-k`, `--api-key`: Jellyfin API key (or set `JELLYFIN_API_KEY` env var)
- `-i`, `--interactive`: Run in interactive mode (menu-driven)
- `-l`, `--list-files`: List all files grouped by codec
- `-c`, `--codec`: Filter listed files by codec (use with `-l`)
- `-o`, `--output`: Save codec summary to a file
- `-d`, `--detailed`: Show percentages and detailed output

Examples:

- Analyze library and print summary:

```bash
python jellycodec.py -s http://localhost:8096 -k ABCDEFGHIJK
```

- Run interactive mode (recommended for exploring and exporting):

```bash
python jellycodec.py -i -s http://localhost:8096 -k ABCDEFGHIJK
```

- List files for a specific codec:

```bash
python jellycodec.py -l -c "HEVC (H.265)" -s http://localhost:8096 -k ABCDEFGHIJK
```

- Save codec summary to `codecs.txt`:

```bash
python jellycodec.py -o codecs.txt -d -s http://localhost:8096 -k ABCDEFGHIJK
```

**Interactive mode**

When launched with `-i`, the script fetches all movie/episode items once and provides a simple menu where you can:
- View codec statistics (counts, total size)
- View detailed statistics with percentages
- List files grouped by codec
- List files for a selected codec
- Export file lists (CSV or JSON)

The interactive flow is useful when you want to quickly inspect which files use a particular codec and export results for further analysis.

**Output and exports**

- Summary output shows total videos analyzed and aggregated size (human-readable).
- File lists can be saved in CSV (recommended) or JSON formats.
- The script attempts to use `MediaSources` entry to determine file sizes; when size information is missing the size will be reported as `Unknown`.

**Development & Contributing**

Contributions and improvements welcome. Open an issue or submit a pull request with fixes or enhancements (e.g., support for additional item types, more robust size detection, or unit tests).

**License**

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

