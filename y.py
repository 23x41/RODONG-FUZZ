import requests
import base64
import time
import sys
import json
import random
import os
from datetime import datetime

class LoopbackFuzzer:
    def __init__(self, base_url, delay=0.01, log_file="fuzzer_log.json", max_patterns=None):
        self.base_url = base_url
        self.delay = delay
        self.log_file = log_file
        self.max_patterns = max_patterns
        self.results = []
        
        # Create curl folder if it doesn't exist
        self.curl_folder = "curl"
        if not os.path.exists(self.curl_folder):
            os.makedirs(self.curl_folder)
            print(f"Created folder: {self.curl_folder}")
        
    def generate_random_patterns(self):
        """Generate random patterns for NUM@NUM@NUM@NUM where NUM can be EMPTY or 0-31"""
        patterns = []
        values = [""] + [str(i) for i in range(32)]  # EMPTY + 0-31
        
        print("Generating random patterns...")
        
        if self.max_patterns:
            total_patterns = self.max_patterns
        else:
            total_patterns = 33 ** 4  # 1,185,921 total possible patterns
        
        # Generate random patterns
        for count in range(total_patterns):
            pos1 = random.choice(values)
            pos2 = random.choice(values)
            pos3 = random.choice(values)
            pos4 = random.choice(values)
            
            # Build pattern: NUM@NUM@NUM@NUM
            pattern = f"{pos1}@{pos2}@{pos3}@{pos4}"
            patterns.append(pattern)
        
        # Shuffle the patterns to ensure randomness
        random.shuffle(patterns)
        return patterns
    
    def save_curl_response(self, pattern, encoded_pattern, response, response_count):
        """Save individual curl response to file"""
        try:
            # Create a safe filename
            safe_pattern = pattern.replace('@', '_').replace('/', '_')
            filename = f"response_{response_count:06d}_{safe_pattern}.txt"
            filepath = os.path.join(self.curl_folder, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"URL: {self.base_url}{encoded_pattern}\n")
                f.write(f"Pattern: {pattern}\n")
                f.write(f"Base64: {encoded_pattern}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Status Code: {response.status_code}\n")
                f.write(f"Content Length: {len(response.content)} bytes\n")
                f.write("-" * 80 + "\n")
                f.write("HEADERS:\n")
                for header, value in response.headers.items():
                    f.write(f"{header}: {value}\n")
                f.write("-" * 80 + "\n")
                f.write("CONTENT:\n")
                f.write(response.text)
            
            return filepath
        except Exception as e:
            print(f"Error saving curl response: {e}")
            return None
    
    def fuzz_server(self):
        """Fuzz the server with random patterns"""
        patterns = self.generate_random_patterns()
        total_patterns = len(patterns)
        
        print(f"Starting RANDOM fuzzing with {total_patterns} patterns")
        print(f"Target: {self.base_url}")
        print(f"Curl responses saved to: {self.curl_folder}/")
        print("-" * 80)
        
        start_time = datetime.now()
        
        for i, pattern in enumerate(patterns, 1):
            try:
                # Encode the pattern in base64
                encoded_pattern = base64.b64encode(pattern.encode()).decode()
                
                # Build the full URL
                url = f"{self.base_url}{encoded_pattern}"
                
                # Display real-time information
                print(f"\n[{i}/{total_patterns}]")
                print(f"Pattern:    '{pattern}'")
                print(f"Base64:     '{encoded_pattern}'")
                print(f"URL:        {url}")
                
                # Send request
                response = requests.get(url, timeout=5, allow_redirects=False)
                
                # Display response info
                print(f"Status:     {response.status_code}")
                print(f"Length:     {len(response.content)} bytes")
                
                # Save individual curl response
                curl_file = self.save_curl_response(pattern, encoded_pattern, response, i)
                if curl_file:
                    print(f"Curl saved: {os.path.basename(curl_file)}")
                
                print("-" * 40)
                
                # Collect results
                result = {
                    'pattern': pattern,
                    'encoded_pattern': encoded_pattern,
                    'url': url,
                    'status_code': response.status_code,
                    'content_length': len(response.content),
                    'curl_file': curl_file,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.results.append(result)
                
                # Log interesting responses
                if response.status_code >= 400 or response.status_code == 200 and len(response.content) == 0:
                    print(f"    [!] INTERESTING: Status {response.status_code}, Length {len(response.content)}")
                
                time.sleep(self.delay)
                
            except requests.exceptions.RequestException as e:
                error_result = {
                    'pattern': pattern,
                    'encoded_pattern': encoded_pattern,
                    'url': url,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                self.results.append(error_result)
                print(f"\n[{i}/{total_patterns}] ERROR: {pattern}")
                print(f"Base64: '{encoded_pattern}'")
                print(f"URL: {url}")
                print(f"Error: {e}")
                print("-" * 40)
                
            except KeyboardInterrupt:
                print(f"\nFuzzing interrupted. Processed {i}/{total_patterns} patterns.")
                break
            except Exception as e:
                print(f"\n[{i}/{total_patterns}] UNEXPECTED ERROR: {e}")
                print(f"Pattern: '{pattern}'")
                print("-" * 40)
        
        # Save results
        self.save_results()
        
        # Print summary
        self.print_summary(start_time)
    
    def save_results(self):
        """Save results to JSON file"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\nResults saved to {self.log_file}")
        except Exception as e:
            print(f"Error saving results: {e}")
    
    def print_summary(self, start_time):
        """Print fuzzing summary"""
        end_time = datetime.now()
        duration = end_time - start_time
        
        successful = [r for r in self.results if 'status_code' in r]
        errors = [r for r in self.results if 'error' in r]
        
        status_codes = {}
        for result in successful:
            code = result['status_code']
            status_codes[code] = status_codes.get(code, 0) + 1
        
        # Count curl files saved
        curl_files = [r for r in self.results if 'curl_file' in r and r['curl_file'] is not None]
        
        print("\n" + "=" * 60)
        print("RANDOM FUZZING SUMMARY")
        print("=" * 60)
        print(f"Total patterns: {len(self.results)}")
        print(f"Successful requests: {len(successful)}")
        print(f"Errors: {len(errors)}")
        print(f"Curl files saved: {len(curl_files)}")
        print(f"Duration: {duration}")
        print(f"Status codes distribution:")
        for code, count in sorted(status_codes.items()):
            print(f"  {code}: {count}")
        print(f"Curl folder: {self.curl_folder}/")
        print(f"JSON results: {self.log_file}")
        print("=" * 60)

def main():
    # Configuration
    BASE_URL = "http://rodong.rep.kp/ko/index.php?"
    DELAY = 0.01  # Adjust based on your needs
    MAX_PATTERNS = None  # Set to a number for testing, None for all
    
    fuzzer = LoopbackFuzzer(BASE_URL, DELAY, max_patterns=MAX_PATTERNS)
    
    print("Loopback Server Fuzzer - Real-time Display with Curl Saving")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    print(f"Pattern: NUM@NUM@NUM@NUM where NUM = EMPTY or 0-31")
    print(f"Total possible patterns: 33^4 = 1,185,921")
    if MAX_PATTERNS:
        print(f"Limited to: {MAX_PATTERNS} patterns")
    print(f"Delay between requests: {DELAY} seconds")
    print(f"Curl responses will be saved to: curl/")
    print("=" * 60)
    
    try:
        input("Press Enter to start fuzzing...")
        print("\nStarting fuzzing (Ctrl+C to stop)...")
        fuzzer.fuzz_server()
    except KeyboardInterrupt:
        print("\nFuzzing cancelled by user.")
    except Exception as e:
        print(f"Fatal error: {e}")

if __name__ == "__main__":
    main()
