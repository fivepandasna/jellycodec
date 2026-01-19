#!/usr/bin/env python3
"""
Jellyfin Codec Analyzer
Analyzes video codecs in your Jellyfin media library
"""

import requests
import json
import argparse
from collections import Counter
from typing import Dict, List
import sys

class JellyfinCodecAnalyzer:
    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.headers = {'X-Emby-Token': api_key}
    
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
        items = []
        params = {
            'Recursive': 'true',
            'IncludeItemTypes': 'Movie,Episode',
            'Fields': 'MediaStreams,Path',
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
    
    def analyze_codecs(self, items: List[Dict]) -> Dict[str, int]:
        """Analyze video codecs from items"""
        codec_counter = Counter()
        items_without_codec = 0
        items_without_streams = 0
        
        for item in items:
            media_streams = item.get('MediaStreams', [])
            
            if not media_streams:
                items_without_streams += 1
                continue
            
            video_stream_found = False
            for stream in media_streams:
                if stream.get('Type') == 'Video':
                    video_stream_found = True
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
                    
                    codec_name = codec_map.get(codec, codec)
                    codec_counter[codec_name] += 1
                    break  # Only count first video stream per item
            
            if not video_stream_found:
                items_without_codec += 1
        
        if items_without_streams > 0:
            print(f"Warning: {items_without_streams} items have no media stream data", file=sys.stderr)
        
        if items_without_codec > 0:
            print(f"Warning: {items_without_codec} items have no video codec info", file=sys.stderr)
        
        return dict(codec_counter)
    
    def print_results(self, codec_stats: Dict[str, int], detailed: bool = False):
        """Print codec statistics"""
        if not codec_stats:
            print("No video codecs found")
            return
        
        total = sum(codec_stats.values())
        print(f"\n{'='*50}")
        print(f"Video Codec Statistics")
        print(f"{'='*50}")
        print(f"Total videos analyzed: {total}\n")
        
        # Sort by count (descending)
        sorted_codecs = sorted(codec_stats.items(), key=lambda x: x[1], reverse=True)
        
        for codec, count in sorted_codecs:
            percentage = (count / total * 100) if total > 0 else 0
            if detailed:
                print(f"{count:>6} {codec:<20} ({percentage:>5.1f}%)")
            else:
                print(f"{count:>6} {codec}")
        
        print(f"{'='*50}\n")
    
    def save_results(self, codec_stats: Dict[str, int], filename: str, detailed: bool = False):
        """Save results to file"""
        try:
            with open(filename, 'w') as f:
                total = sum(codec_stats.values())
                f.write(f"{'='*50}\n")
                f.write(f"Video Codec Statistics\n")
                f.write(f"{'='*50}\n")
                f.write(f"Total videos analyzed: {total}\n\n")
                
                sorted_codecs = sorted(codec_stats.items(), key=lambda x: x[1], reverse=True)
                
                for codec, count in sorted_codecs:
                    percentage = (count / total * 100) if total > 0 else 0
                    if detailed:
                        f.write(f"{count:>6} {codec:<20} ({percentage:>5.1f}%)\n")
                    else:
                        f.write(f"{count:>6} {codec}\n")
                
                f.write(f"{'='*50}\n")
            
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

def main():
    parser = argparse.ArgumentParser(
        description='Analyze video codecs in Jellyfin media library',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s -s http://localhost:8096 -k YOUR_API_KEY
  %(prog)s -s http://localhost:8096 -k YOUR_API_KEY -d
  %(prog)s -s http://localhost:8096 -k YOUR_API_KEY -o codecs.txt
  %(prog)s -s http://localhost:8096 -k YOUR_API_KEY -o codecs.txt -d
        '''
    )
    
    parser.add_argument('-s', '--server', required=True,
                        help='Jellyfin server URL (e.g., http://localhost:8096)')
    parser.add_argument('-k', '--api-key', required=True,
                        help='Jellyfin API key')
    parser.add_argument('-o', '--output', 
                        help='Output file to save results')
    parser.add_argument('-d', '--detailed', action='store_true',
                        help='Show detailed statistics with percentages')
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = JellyfinCodecAnalyzer(args.server, args.api_key)
    
    # Test connection
    print("Testing connection to Jellyfin...", file=sys.stderr)
    if not analyzer.test_connection():
        print("Failed to connect to Jellyfin server", file=sys.stderr)
        sys.exit(1)
    
    print("Connection successful!", file=sys.stderr)
    
    # Fetch and analyze items
    print("Fetching media items...", file=sys.stderr)
    items = analyzer.get_all_items()
    
    if not items:
        print("No items found", file=sys.stderr)
        sys.exit(1)
    
    print("Analyzing codecs...", file=sys.stderr)
    codec_stats = analyzer.analyze_codecs(items)
    
    # Print results
    analyzer.print_results(codec_stats, args.detailed)
    
    # Save to file if requested
    if args.output:
        analyzer.save_results(codec_stats, args.output, args.detailed)

if __name__ == '__main__':
    main()
