#!/usr/bin/env python3
"""
Performance Testing Suite - Weather Forecast API
Unified script for testing all endpoints with configurable scenarios

Features:
- Tests 3 endpoints: neighbors, single weather, regional weather
- Tests 3 city counts: 10, 50, 100
- Baseline mode: Save results for future comparison
- Compare mode: Compare against baseline with regression detection
- HTTP testing against real API Gateway URL

Usage:
    python scripts/test_performance.py                    # Run all tests, save baseline
    python scripts/test_performance.py --compare          # Compare against last baseline
    python scripts/test_performance.py --scenario 100     # Test only 100 cities scenario
    python scripts/test_performance.py --endpoint regional # Test only regional endpoint
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests


# Test scenarios: (endpoint_name, city_count)
SCENARIOS = [
    ('neighbors', 10),
    ('neighbors', 50),
    ('neighbors', 100),
    ('single', 10),
    ('single', 50),
    ('single', 100),
    ('regional', 10),
    ('regional', 50),
    ('regional', 100),
]


def load_api_url() -> str:
    """Load API Gateway URL from API_URL.txt"""
    api_url_file = Path(__file__).parent.parent / 'API_URL.txt'
    
    if not api_url_file.exists():
        print("❌ API_URL.txt not found!")
        print("💡 Run deployment first: bash scripts/deploy-main.sh")
        sys.exit(1)
    
    with open(api_url_file, 'r') as f:
        return f.read().strip()


def load_test_cities(limit: int = 100) -> List[str]:
    """Load test city IDs from test_100_municipalities.json"""
    test_file = Path(__file__).parent.parent / 'lambda' / 'data' / 'test_100_municipalities.json'
    
    with open(test_file, 'r', encoding='utf-8') as f:
        municipalities = json.load(f)
    
    return [m['id'] for m in municipalities[:limit]]


def test_neighbors_endpoint(api_url: str, city_id: str) -> Dict[str, Any]:
    """Test GET /api/cities/neighbors/{city_id}?radius=50"""
    start = time.time()
    
    try:
        response = requests.get(
            f"{api_url}/api/cities/neighbors/{city_id}",
            params={'radius': '50'},
            headers={'Accept': 'application/json'},
            timeout=30
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            neighbors_count = len(data.get('neighbors', []))
            success = True
            error = None
        else:
            neighbors_count = 0
            success = False
            error = f"Status {response.status_code}: {response.text[:200]}"
        
        return {
            'success': success,
            'status_code': response.status_code,
            'latency_ms': round(elapsed * 1000, 2),
            'neighbors_count': neighbors_count,
            'error': error
        }
    
    except Exception as e:
        elapsed = time.time() - start
        return {
            'success': False,
            'status_code': 0,
            'latency_ms': round(elapsed * 1000, 2),
            'neighbors_count': 0,
            'error': str(e)
        }


def test_single_weather_endpoint(api_url: str, city_id: str) -> Dict[str, Any]:
    """Test GET /api/weather/city/{city_id}"""
    start = time.time()
    
    try:
        response = requests.get(
            f"{api_url}/api/weather/city/{city_id}",
            headers={'Accept': 'application/json'},
            timeout=30
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            has_weather = 'temperature' in data
            success = True
            error = None
        else:
            has_weather = False
            success = False
            error = f"Status {response.status_code}: {response.text[:200]}"
        
        return {
            'success': success,
            'status_code': response.status_code,
            'latency_ms': round(elapsed * 1000, 2),
            'has_weather': has_weather,
            'error': error
        }
    
    except Exception as e:
        elapsed = time.time() - start
        return {
            'success': False,
            'status_code': 0,
            'latency_ms': round(elapsed * 1000, 2),
            'has_weather': False,
            'error': str(e)
        }


def test_regional_weather_endpoint(api_url: str, city_ids: List[str]) -> Dict[str, Any]:
    """Test POST /api/weather/regional"""
    start = time.time()
    
    try:
        response = requests.post(
            f"{api_url}/api/weather/regional",
            json={'cityIds': city_ids},
            headers={'Content-Type': 'application/json'},
            timeout=180
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            cities_returned = len(data) if isinstance(data, list) else 0
            success = True
            error = None
        else:
            cities_returned = 0
            success = False
            error = f"Status {response.status_code}: {response.text[:200]}"
        
        return {
            'success': success,
            'status_code': response.status_code,
            'latency_ms': round(elapsed * 1000, 2),
            'cities_requested': len(city_ids),
            'cities_returned': cities_returned,
            'avg_per_city_ms': round(elapsed * 1000 / len(city_ids), 2) if city_ids else 0,
            'error': error
        }
    
    except Exception as e:
        elapsed = time.time() - start
        return {
            'success': False,
            'status_code': 0,
            'latency_ms': round(elapsed * 1000, 2),
            'cities_requested': len(city_ids),
            'cities_returned': 0,
            'avg_per_city_ms': 0,
            'error': str(e)
        }


def run_scenario(api_url: str, endpoint: str, city_count: int, city_ids: List[str]) -> Dict[str, Any]:
    """Run a single test scenario"""
    scenario_name = f"{endpoint}_{city_count}"
    print(f"\n🧪 Testing: {scenario_name}")
    
    if endpoint == 'neighbors':
        # Test first city only
        result = test_neighbors_endpoint(api_url, city_ids[0])
        result['scenario'] = scenario_name
        result['endpoint'] = endpoint
        result['city_count'] = 1
    
    elif endpoint == 'single':
        # Test N individual cities sequentially
        results = []
        for city_id in city_ids[:city_count]:
            results.append(test_single_weather_endpoint(api_url, city_id))
        
        # Aggregate results
        success_count = sum(1 for r in results if r['success'])
        total_latency = sum(r['latency_ms'] for r in results)
        
        result = {
            'scenario': scenario_name,
            'endpoint': endpoint,
            'city_count': city_count,
            'success': success_count == city_count,
            'success_rate': round((success_count / city_count) * 100, 1) if city_count > 0 else 0,
            'total_latency_ms': round(total_latency, 2),
            'avg_latency_ms': round(total_latency / city_count, 2) if city_count > 0 else 0,
            'error': None if success_count == city_count else f"{city_count - success_count} failures"
        }
    
    elif endpoint == 'regional':
        # Test N cities in parallel (single request)
        result = test_regional_weather_endpoint(api_url, city_ids[:city_count])
        result['scenario'] = scenario_name
        result['endpoint'] = endpoint
        result['city_count'] = city_count
    
    # Print result
    status = "✅" if result.get('success', False) else "❌"
    latency_key = 'latency_ms' if 'latency_ms' in result else 'total_latency_ms'
    print(f"   {status} {result[latency_key]:.0f}ms", end='')
    
    if 'avg_per_city_ms' in result:
        print(f" ({result['avg_per_city_ms']:.1f}ms/city)", end='')
    elif 'avg_latency_ms' in result:
        print(f" ({result['avg_latency_ms']:.1f}ms/city)", end='')
    
    if not result.get('success', False):
        print(f" - ERROR: {result.get('error', 'Unknown')[:50]}", end='')
    
    print()
    
    return result


def run_all_scenarios(api_url: str, filter_scenario: Optional[int] = None, filter_endpoint: Optional[str] = None) -> List[Dict[str, Any]]:
    """Run all test scenarios"""
    print(f"\n{'='*70}")
    print(f"🚀 PERFORMANCE TEST SUITE")
    print(f"{'='*70}")
    print(f"API: {api_url}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*70}")
    
    # Load test cities
    city_ids = load_test_cities(limit=100)
    print(f"✅ Loaded {len(city_ids)} test cities")
    
    # Filter scenarios
    scenarios = SCENARIOS
    if filter_scenario:
        scenarios = [(e, c) for e, c in scenarios if c == filter_scenario]
    if filter_endpoint:
        scenarios = [(e, c) for e, c in scenarios if e == filter_endpoint]
    
    print(f"📋 Running {len(scenarios)} scenarios\n")
    
    # Run scenarios
    results = []
    for endpoint, city_count in scenarios:
        result = run_scenario(api_url, endpoint, city_count, city_ids)
        results.append(result)
        time.sleep(0.5)  # Small delay between scenarios
    
    return results


def save_baseline(results: List[Dict[str, Any]]) -> Path:
    """Save results as baseline for future comparisons"""
    output_dir = Path(__file__).parent.parent / 'output'
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"performance_baseline_{timestamp}.json"
    filepath = output_dir / filename
    
    baseline_data = {
        'timestamp': datetime.now().isoformat(),
        'test_type': 'baseline',
        'scenarios': results
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(baseline_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Baseline saved: {filepath}")
    return filepath


def load_latest_baseline() -> Optional[Dict[str, Any]]:
    """Load the most recent baseline file"""
    output_dir = Path(__file__).parent.parent / 'output'
    
    if not output_dir.exists():
        return None
    
    baseline_files = list(output_dir.glob('performance_baseline_*.json'))
    
    if not baseline_files:
        return None
    
    latest_file = max(baseline_files, key=lambda p: p.stat().st_mtime)
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_with_baseline(current_results: List[Dict[str, Any]]) -> None:
    """Compare current results with baseline"""
    baseline = load_latest_baseline()
    
    if not baseline:
        print("\n⚠️  No baseline found. Run without --compare first.")
        return
    
    print(f"\n{'='*70}")
    print(f"📊 COMPARISON WITH BASELINE")
    print(f"{'='*70}")
    print(f"Baseline: {baseline['timestamp']}")
    print(f"{'='*70}\n")
    
    # Create lookup for baseline results
    baseline_lookup = {r['scenario']: r for r in baseline['scenarios']}
    
    # Compare each scenario
    regressions = []
    improvements = []
    
    for current in current_results:
        scenario = current['scenario']
        
        if scenario not in baseline_lookup:
            print(f"⚠️  {scenario:20s} - No baseline data")
            continue
        
        baseline_result = baseline_lookup[scenario]
        
        # Get latency values
        current_latency = current.get('latency_ms') or current.get('total_latency_ms', 0)
        baseline_latency = baseline_result.get('latency_ms') or baseline_result.get('total_latency_ms', 0)
        
        # Calculate change
        if baseline_latency > 0:
            change_pct = ((current_latency - baseline_latency) / baseline_latency) * 100
        else:
            change_pct = 0
        
        # Determine status
        if change_pct > 20:  # Regression threshold
            status = "🔴 REGRESSION"
            regressions.append((scenario, change_pct))
        elif change_pct < -10:  # Improvement threshold
            status = "🟢 IMPROVEMENT"
            improvements.append((scenario, change_pct))
        else:
            status = "⚪ STABLE"
        
        print(f"{status:20s} {scenario:20s} {baseline_latency:7.0f}ms → {current_latency:7.0f}ms ({change_pct:+.1f}%)")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📈 SUMMARY")
    print(f"{'='*70}")
    print(f"Regressions: {len(regressions)}")
    print(f"Improvements: {len(improvements)}")
    print(f"Stable: {len(current_results) - len(regressions) - len(improvements)}")
    
    if regressions:
        print(f"\n❌ REGRESSIONS DETECTED:")
        for scenario, change_pct in regressions:
            print(f"   - {scenario}: {change_pct:+.1f}%")
        print(f"{'='*70}\n")
        sys.exit(1)  # Exit with error if regressions found
    else:
        print(f"\n✅ NO REGRESSIONS DETECTED")
        print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description='Performance testing suite for Weather Forecast API')
    parser.add_argument('--compare', action='store_true', help='Compare with baseline')
    parser.add_argument('--scenario', type=int, choices=[10, 50, 100], help='Test only specific city count')
    parser.add_argument('--endpoint', type=str, choices=['neighbors', 'single', 'regional'], help='Test only specific endpoint')
    
    args = parser.parse_args()
    
    # Load API URL
    api_url = load_api_url()
    
    # Run tests
    results = run_all_scenarios(api_url, filter_scenario=args.scenario, filter_endpoint=args.endpoint)
    
    # Compare or save baseline
    if args.compare:
        compare_with_baseline(results)
    else:
        save_baseline(results)
    
    # Print summary
    success_count = sum(1 for r in results if r.get('success', False))
    print(f"\n{'='*70}")
    print(f"✅ TESTS COMPLETED: {success_count}/{len(results)} passed")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
