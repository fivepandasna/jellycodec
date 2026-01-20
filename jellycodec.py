#!/usr/bin/env python3
"""
Jellyfin Codec Analyzer
Analyzes video codecs in your Jellyfin media library
Automatically loads JELLYFIN_SERVER and JELLYFIN_API_KEY from .env file
"""

import requests
import json
import argparse
from collections import Counter
from typing import Dict, List
import sys
import os

# Load .env file automatically
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Loaded configuration from .env file", file=sys.stderr)
except ImportError:
    print("Note: python-dotenv not installed. Install with: pip install python-dotenv", file=sys.stderr)
    print("Falling back to environment variables or command-line arguments", file=sys.stderr)

class JellyfinCodecAnalyzer:
    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.headers = {'X-Emby-Token': api_key}
        self.items_cache = None
    
    def test_connection(self) -> bool:
        """Test connection to Jellyfin server"""
        try:
            response = requests.get(
                f"{self.server_url}/System/Info",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 401:
                print("Error: Invalid API key (401 Unauthorized)", file=sys.stderr)
                return False
            elif response.status_code == 403:
                print("Error: Access forbidden (403 Forbidden)", file=sys.stderr)
                return False
            elif response.status_code == 404:
                print("Error: Server endpoint not found (404) - Check server URL", file=sys.stderr)
                return False
            elif response.status_code != 200:
                print(f"Error: Server returned status code {response.status_code}", file=sys.stderr)
                return False
            return True
        except requests.exceptions.ConnectionError:
            print(f"Error: Cannot connect to {self.server_url}", file=sys.stderr)
            print("Check that the server URL is correct and Jellyfin is running", file=sys.stderr)
            return False
        except requests.exceptions.Timeout:
            print(f"Error: Connection timeout to {self.server_url}", file=sys.stderr)
            return False
        except requests.exceptions.MissingSchema:
            print(f"Error: Invalid URL format: {self.server_url}", file=sys.stderr)
            print("URL must include http:// or https://", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error connecting to Jellyfin: {type(e).__name__}: {e}", file=sys.stderr)
            return False
    
    def get_all_items(self) -> List[Dict]:
        """Fetch all video items from Jellyfin"""
        if self.items_cache is not None:
            return self.items_cache
            
        items = []
        params = {
            'Recursive': 'true',
            'IncludeItemTypes': 'Movie,Episode',
            'Fields': 'MediaStreams,Path,MediaSources',
        }
        
        try:
            response = requests.get(
                f"{self.server_url}/Items",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 401:
                print("Error: API key rejected while fetching items", file=sys.stderr)
                return []
            elif response.status_code == 403:
                print("Error: Insufficient permissions to access library", file=sys.stderr)
                return []
            elif response.status_code == 500:
                print("Error: Jellyfin server error (500)", file=sys.stderr)
                print("The server encountered an internal error", file=sys.stderr)
                return []
            
            response.raise_for_status()
            data = response.json()
            items = data.get('Items', [])
            
            if not items:
                print("Warning: No video items found in library", file=sys.stderr)
            else:
                print(f"Found {len(items)} video items", file=sys.stderr)
            
            self.items_cache = items
            return items
            
        except requests.exceptions.ConnectionError:
            print("Error: Lost connection to server while fetching items", file=sys.stderr)
            return []
        except requests.exceptions.Timeout:
            print("Error: Request timeout - server took too long to respond", file=sys.stderr)
            print("Try again or check server performance", file=sys.stderr)
            return []
        except requests.exceptions.JSONDecodeError:
            print("Error: Invalid JSON response from server", file=sys.stderr)
            return []
        except requests.exceptions.HTTPError as e:
            print(f"Error: HTTP {e.response.status_code} while fetching items", file=sys.stderr)
            return []
        except Exception as e:
            print(f"Error fetching items: {type(e).__name__}: {e}", file=sys.stderr)
            return []
    
    def get_file_size(self, item: Dict) -> int:
        """Extract file size in bytes from an item"""
        # Try MediaSources first (most reliable)
        media_sources = item.get('MediaSources', [])
        if media_sources and len(media_sources) > 0:
            size = media_sources[0].get('Size', 0)
            if size:
                return size
        
        # Fallback to RunTimeTicks estimation (very rough)
        return 0
    
    def format_size(self, bytes_size: int) -> str:
        """Format bytes to human readable size"""
        if bytes_size == 0:
            return "Unknown"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} PB"
    
    def get_video_codec(self, item: Dict) -> str:
        """Extract video codec from an item"""
        media_streams = item.get('MediaStreams', [])
        for stream in media_streams:
            if stream.get('Type') == 'Video':
                codec = stream.get('Codec', 'Unknown').upper()
                
                # Map common codec names to standard format
                codec_map = {
                    'H264': 'AVC (H.264)',
                    'HEVC': 'HEVC (H.265)',
                    'H265': 'HEVC (H.265)',
                    'VP9': 'VP9',
                    'VP8': 'VP8',
                    'AV1': 'AV1',
                    'MPEG4': 'MPEG-4',
                    'MPEG2VIDEO': 'MPEG-2',
                    'VC1': 'VC-1',
                    'WMV3': 'WMV3',
                }
                
                return codec_map.get(codec, codec)
        return 'Unknown'
    
    def analyze_codecs(self, items: List[Dict]) -> Dict[str, Dict]:
        """Analyze video codecs from items"""
        codec_data = {}
        items_without_codec = 0
        items_without_streams = 0
        
        for item in items:
            media_streams = item.get('MediaStreams', [])
            
            if not media_streams:
                items_without_streams += 1
                continue
            
            codec = self.get_video_codec(item)
            file_size = self.get_file_size(item)
            
            if codec == 'Unknown':
                items_without_codec += 1
            else:
                if codec not in codec_data:
                    codec_data[codec] = {'count': 0, 'total_size': 0}
                codec_data[codec]['count'] += 1
                codec_data[codec]['total_size'] += file_size
        
        if items_without_streams > 0:
            print(f"Warning: {items_without_streams} items have no media stream data", file=sys.stderr)
        
        if items_without_codec > 0:
            print(f"Warning: {items_without_codec} items have no video codec info", file=sys.stderr)
        
        return codec_data
    
    def print_results(self, codec_data: Dict[str, Dict], detailed: bool = False):
        """Print codec statistics"""
        if not codec_data:
            print("No video codecs found")
            return
        
        total_count = sum(data['count'] for data in codec_data.values())
        total_size = sum(data['total_size'] for data in codec_data.values())
        
        print(f"\n{'='*70}")
        print(f"Video Codec Statistics")
        print(f"{'='*70}")
        print(f"Total videos analyzed: {total_count}")
        print(f"Total size: {self.format_size(total_size)}\n")
        
        # Sort by count (descending)
        sorted_codecs = sorted(codec_data.items(), key=lambda x: x[1]['count'], reverse=True)
        
        if detailed:
            print(f"{'Count':<8} {'Codec':<20} {'Size':<15} {'Percentage':<10}")
            print(f"{'-'*70}")
            for codec, data in sorted_codecs:
                count = data['count']
                size = data['total_size']
                percentage = (count / total_count * 100) if total_count > 0 else 0
                print(f"{count:<8} {codec:<20} {self.format_size(size):<15} {percentage:>5.1f}%")
        else:
            print(f"{'Count':<8} {'Codec':<20} {'Size':<15}")
            print(f"{'-'*70}")
            for codec, data in sorted_codecs:
                count = data['count']
                size = data['total_size']
                print(f"{count:<8} {codec:<20} {self.format_size(size):<15}")
        
        print(f"{'='*70}\n")
    
    def list_files_by_codec(self, items: List[Dict], codec_filter: str = None):
        """List all files, optionally filtered by codec"""
        codec_groups = {}
        
        for item in items:
            codec = self.get_video_codec(item)
            if codec not in codec_groups:
                codec_groups[codec] = []
            
            name = item.get('Name', 'Unknown')
            path = item.get('Path', 'No path')
            size = self.get_file_size(item)
            codec_groups[codec].append({'name': name, 'path': path, 'size': size})
        
        if codec_filter:
            if codec_filter in codec_groups:
                files = codec_groups[codec_filter]
                total_size = sum(f['size'] for f in files)
                
                print(f"\n{'='*70}")
                print(f"Files with codec: {codec_filter}")
                print(f"Total: {len(files)} files, {self.format_size(total_size)}")
                print(f"{'='*70}")
                for file_info in sorted(files, key=lambda x: x['name']):
                    print(f"\n{file_info['name']}")
                    print(f"  Size: {self.format_size(file_info['size'])}")
                    print(f"  Path: {file_info['path']}")
                print(f"\n{'='*70}\n")
            else:
                print(f"\nNo files found with codec: {codec_filter}\n")
        else:
            for codec in sorted(codec_groups.keys()):
                files = codec_groups[codec]
                total_size = sum(f['size'] for f in files)
                
                print(f"\n{'='*70}")
                print(f"Codec: {codec} ({len(files)} files, {self.format_size(total_size)})")
                print(f"{'='*70}")
                for file_info in sorted(files, key=lambda x: x['name']):
                    print(f"\n{file_info['name']}")
                    print(f"  Size: {self.format_size(file_info['size'])}")
                    print(f"  Path: {file_info['path']}")
    
    def save_results(self, codec_data: Dict[str, Dict], filename: str, detailed: bool = False):
        """Save codec statistics to file"""
        try:
            with open(filename, 'w') as f:
                total_count = sum(data['count'] for data in codec_data.values())
                total_size = sum(data['total_size'] for data in codec_data.values())
                
                f.write(f"{'='*70}\n")
                f.write(f"Video Codec Statistics\n")
                f.write(f"{'='*70}\n")
                f.write(f"Total videos analyzed: {total_count}\n")
                f.write(f"Total size: {self.format_size(total_size)}\n\n")
                
                sorted_codecs = sorted(codec_data.items(), key=lambda x: x[1]['count'], reverse=True)
                
                if detailed:
                    f.write(f"{'Count':<8} {'Codec':<20} {'Size':<15} {'Percentage':<10}\n")
                    f.write(f"{'-'*70}\n")
                    for codec, data in sorted_codecs:
                        count = data['count']
                        size = data['total_size']
                        percentage = (count / total_count * 100) if total_count > 0 else 0
                        f.write(f"{count:<8} {codec:<20} {self.format_size(size):<15} {percentage:>5.1f}%\n")
                else:
                    f.write(f"{'Count':<8} {'Codec':<20} {'Size':<15}\n")
                    f.write(f"{'-'*70}\n")
                    for codec, data in sorted_codecs:
                        count = data['count']
                        size = data['total_size']
                        f.write(f"{count:<8} {codec:<20} {self.format_size(size):<15}\n")
                
                f.write(f"{'='*70}\n")
            
            print(f"Results saved to {filename}")
        except PermissionError:
            print(f"Error: Permission denied writing to {filename}", file=sys.stderr)
            print("Check file permissions or try a different location", file=sys.stderr)
        except IsADirectoryError:
            print(f"Error: {filename} is a directory, not a file", file=sys.stderr)
        except OSError as e:
            print(f"Error saving file: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error saving to file: {type(e).__name__}: {e}", file=sys.stderr)
    
    def save_file_list(self, items: List[Dict], filename: str, codec_filter: str = None, format_type: str = 'csv'):
        """Save file list to file in CSV or JSON format"""
        try:
            codec_groups = {}
            
            for item in items:
                codec = self.get_video_codec(item)
                if codec not in codec_groups:
                    codec_groups[codec] = []
                
                name = item.get('Name', 'Unknown')
                path = item.get('Path', 'No path')
                size = self.get_file_size(item)
                codec_groups[codec].append({'name': name, 'path': path, 'codec': codec, 'size': size, 'size_formatted': self.format_size(size)})
            
            if format_type == 'csv':
                import csv
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Name', 'Codec', 'Size (Bytes)', 'Size', 'Path'])
                    
                    if codec_filter:
                        if codec_filter in codec_groups:
                            for file_info in sorted(codec_groups[codec_filter], key=lambda x: x['name']):
                                writer.writerow([file_info['name'], file_info['codec'], file_info['size'], file_info['size_formatted'], file_info['path']])
                    else:
                        for codec in sorted(codec_groups.keys()):
                            for file_info in sorted(codec_groups[codec], key=lambda x: x['name']):
                                writer.writerow([file_info['name'], file_info['codec'], file_info['size'], file_info['size_formatted'], file_info['path']])
            
            else:  # json format
                output_data = []
                if codec_filter:
                    if codec_filter in codec_groups:
                        output_data = sorted(codec_groups[codec_filter], key=lambda x: x['name'])
                else:
                    for codec in sorted(codec_groups.keys()):
                        output_data.extend(sorted(codec_groups[codec], key=lambda x: x['name']))
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"File list saved to {filename} ({format_type.upper()} format)")
        except PermissionError:
            print(f"Error: Permission denied writing to {filename}", file=sys.stderr)
            print("Check file permissions or try a different location", file=sys.stderr)
        except IsADirectoryError:
            print(f"Error: {filename} is a directory, not a file", file=sys.stderr)
        except OSError as e:
            print(f"Error saving file: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error saving to file: {type(e).__name__}: {e}", file=sys.stderr)

def interactive_mode(analyzer: JellyfinCodecAnalyzer):
    """Run in interactive mode"""
    print("\n" + "="*50)
    print("Jellyfin Codec Analyzer - Interactive Mode")
    print("="*50)
    
    # Fetch items once
    print("\nFetching media items from Jellyfin...")
    items = analyzer.get_all_items()
    
    if not items:
        print("No items found. Exiting.")
        return
    
    # Analyze codecs
    print("Analyzing codecs...")
    codec_stats = analyzer.analyze_codecs(items)
    
    while True:
        print("\n" + "="*50)
        print("What would you like to do?")
        print("="*50)
        print("1. Show codec statistics")
        print("2. Show detailed statistics (with percentages)")
        print("3. List all files by codec")
        print("4. List files for specific codec")
        print("5. Save file list to file")
        print("6. Exit")
        print("="*50)
        
        try:
            choice = input("\nEnter your choice (1-6): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nExiting...")
            break
        
        if choice == '1':
            analyzer.print_results(codec_stats, detailed=False)
        
        elif choice == '2':
            analyzer.print_results(codec_stats, detailed=True)
        
        elif choice == '3':
            print("\nListing all files by codec...")
            analyzer.list_files_by_codec(items)
        
        elif choice == '4':
            print("\nAvailable codecs:")
            for i, codec in enumerate(sorted(codec_stats.keys()), 1):
                count = codec_stats[codec]['count']
                size = codec_stats[codec]['total_size']
                print(f"  {i}. {codec} ({count} files, {analyzer.format_size(size)})")
            
            codec_choice = input("\nEnter codec name or number: ").strip()
            
            # Check if input is a number
            try:
                codec_num = int(codec_choice)
                codec_list = sorted(codec_stats.keys())
                if 1 <= codec_num <= len(codec_list):
                    codec_filter = codec_list[codec_num - 1]
                else:
                    print("Invalid number")
                    continue
            except ValueError:
                codec_filter = codec_choice
            
            analyzer.list_files_by_codec(items, codec_filter)
        
        elif choice == '5':
            filename = input("Enter filename (default: files.csv): ").strip()
            if not filename:
                filename = "files.csv"
            
            print("\nExport format:")
            print("1. CSV (recommended - easily open in Excel/spreadsheets)")
            print("2. JSON (for programmatic use)")
            
            format_choice = input("\nEnter format choice (1-2, default: 1): ").strip()
            if not format_choice:
                format_choice = '1'
            
            format_type = 'csv' if format_choice == '1' else 'json'
            
            # Adjust filename extension if needed
            if format_type == 'csv' and not filename.endswith('.csv'):
                filename = filename.rsplit('.', 1)[0] + '.csv'
            elif format_type == 'json' and not filename.endswith('.json'):
                filename = filename.rsplit('.', 1)[0] + '.json'
            
            print("\nSave options:")
            print("1. All files (all codecs)")
            print("2. Specific codec only")
            
            save_choice = input("\nEnter choice (1-2): ").strip()
            
            if save_choice == '1':
                analyzer.save_file_list(items, filename, format_type=format_type)
            elif save_choice == '2':
                print("\nAvailable codecs:")
                for i, codec in enumerate(sorted(codec_stats.keys()), 1):
                    count = codec_stats[codec]['count']
                    size = codec_stats[codec]['total_size']
                    print(f"  {i}. {codec} ({count} files, {analyzer.format_size(size)})")
                
                codec_choice = input("\nEnter codec name or number: ").strip()
                
                # Check if input is a number
                try:
                    codec_num = int(codec_choice)
                    codec_list = sorted(codec_stats.keys())
                    if 1 <= codec_num <= len(codec_list):
                        codec_filter = codec_list[codec_num - 1]
                    else:
                        print("Invalid number")
                        continue
                except ValueError:
                    codec_filter = codec_choice
                
                analyzer.save_file_list(items, filename, codec_filter, format_type=format_type)
            else:
                print("Invalid choice")
        
        elif choice == '6':
            print("\nExiting...")
            break
        
        else:
            print("\nInvalid choice. Please enter 1-6.")

def main():
    print("Jellyfin Codec Analyzer starting...", file=sys.stderr)
    
    parser = argparse.ArgumentParser(
        description='Analyze video codecs in Jellyfin media library',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                                    # Uses .env file
  %(prog)s -s http://localhost:8096 -k KEY   # Override .env settings
  %(prog)s -i                                 # Interactive mode
  %(prog)s -d                                 # Detailed output
  %(prog)s -o codecs.txt                      # Save to file

Setup .env file:
  Create a .env file in the same directory with:
  JELLYFIN_SERVER=http://localhost:8096
  JELLYFIN_API_KEY=your_api_key_here
        '''
    )
    
    parser.add_argument('-s', '--server', 
                        help='Jellyfin server URL (e.g., http://localhost:8096). Can also use JELLYFIN_SERVER env var')
    parser.add_argument('-k', '--api-key', 
                        help='Jellyfin API key. Can also use JELLYFIN_API_KEY env var')
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='Run in interactive mode')
    parser.add_argument('-o', '--output', 
                        help='Output file to save results')
    parser.add_argument('-d', '--detailed', action='store_true',
                        help='Show detailed statistics with percentages')
    parser.add_argument('-l', '--list-files', action='store_true',
                        help='List all files by codec')
    parser.add_argument('-c', '--codec', 
                        help='Filter files by specific codec (use with -l)')
    
    args = parser.parse_args()
    
    # Get server URL from args or environment
    server = args.server or os.getenv('JELLYFIN_SERVER')
    if not server:
        print("Error: Server URL required. Provide via -s or set JELLYFIN_SERVER env var", file=sys.stderr)
        print("", file=sys.stderr)
        print("Create a .env file with:", file=sys.stderr)
        print("  JELLYFIN_SERVER=http://localhost:8096", file=sys.stderr)
        print("  JELLYFIN_API_KEY=your_api_key_here", file=sys.stderr)
        sys.exit(1)
    
    # Get API key from args or environment
    api_key = args.api_key or os.getenv('JELLYFIN_API_KEY')
    if not api_key:
        print("Error: API key required. Provide via -k or set JELLYFIN_API_KEY env var", file=sys.stderr)
        print("", file=sys.stderr)
        print("Create a .env file with:", file=sys.stderr)
        print("  JELLYFIN_SERVER=http://localhost:8096", file=sys.stderr)
        print("  JELLYFIN_API_KEY=your_api_key_here", file=sys.stderr)
        sys.exit(1)
    
    # Validate URL format
    if not server.startswith(('http://', 'https://')):
        print(f"Error: Invalid server URL: {server}", file=sys.stderr)
        print("URL must start with http:// or https://", file=sys.stderr)
        print(f"Example: http://localhost:8096", file=sys.stderr)
        sys.exit(1)
    
    # Validate API key format (basic check)
    if len(api_key) < 10:
        print(f"Error: API key seems too short: {len(api_key)} characters", file=sys.stderr)
        print("Check that you copied the full API key", file=sys.stderr)
        sys.exit(1)
    
    # Initialize analyzer
    analyzer = JellyfinCodecAnalyzer(server, api_key)
    
    # Test connection
    print("Testing connection to Jellyfin...", file=sys.stderr)
    if not analyzer.test_connection():
        print("Failed to connect to Jellyfin server", file=sys.stderr)
        sys.exit(1)
    
    print("Connection successful!", file=sys.stderr)
    
    # Interactive mode
    if args.interactive:
        interactive_mode(analyzer)
        return
    
    # Fetch and analyze items
    print("Fetching media items...", file=sys.stderr)
    items = analyzer.get_all_items()
    
    if not items:
        print("No items found", file=sys.stderr)
        sys.exit(1)
    
    print("Analyzing codecs...", file=sys.stderr)
    codec_stats = analyzer.analyze_codecs(items)
    
    # List files mode
    if args.list_files:
        analyzer.list_files_by_codec(items, args.codec)
        return
    
    # Print results
    analyzer.print_results(codec_stats, args.detailed)
    
    # Save to file if requested
    if args.output:
        analyzer.save_results(codec_stats, args.output, args.detailed)

if __name__ == '__main__':
    main()
