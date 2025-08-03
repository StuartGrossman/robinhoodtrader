#!/usr/bin/env python3
"""
Test script for improved data extraction from Robinhood options
"""
import re
import json
from datetime import datetime

def test_data_extraction_patterns():
    """Test the data extraction patterns with sample Robinhood HTML content."""
    
    # Sample HTML content that might be found in Robinhood options page
    sample_content = """
    <div class="option-details">
        <div class="price-info">
            <span>Share price: $621.23</span>
            <span>Bid: 0.08</span>
            <span>Ask: 0.09</span>
        </div>
        <div class="volume-info">
            <span>Volume: 14,029</span>
            <span>Open Interest: 3,726</span>
        </div>
        <div class="greeks">
            <span>Theta: -0.1305</span>
            <span>Gamma: 0.0116</span>
            <span>Delta: 0.0347</span>
            <span>Vega: 0.0339</span>
        </div>
        <div class="high-low">
            <span>High: 0.12</span>
            <span>Low: 0.05</span>
        </div>
        <div class="strike-info">
            <span>Strike: 635</span>
            <span>Expires: 8/4/2025</span>
        </div>
    </div>
    """
    
    # Test patterns from the improved extraction method
    patterns = {
        'current_price': [
            r'(?:Last|Price|Mark|Current)[:\s]+\$?(\d+\.\d{2,4})',
            r'Premium[:\s]+\$?(\d+\.\d{2,4})', 
            r'\$(\d+\.\d{2,4})\s*(?:Last|Current)',
            r'(\d+\.\d{2,4})\s*USD',  # Robinhood format
            r'Mark[:\s]*\$?(\d+\.\d{2,4})',  # Mark price
            r'Share price[:\s]*\$?(\d+\.\d{2,4})',  # Robinhood share price
        ],
        'bid': [
            r'Bid[:\s]+\$?(\d+\.\d{2,4})',
            r'Bid\s*\$?(\d+\.\d{2,4})',
            r'Bid[:\s]*\$?(\d+\.\d{2,4})',
            r'\$(\d+\.\d{2,4})\s*×\s*\d+',  # $0.07 × 1,062 format
            r'Bid[:\s]*(\d+\.\d{2,4})',  # Robinhood format
        ],
        'ask': [
            r'Ask[:\s]+\$?(\d+\.\d{2,4})',
            r'Ask\s*\$?(\d+\.\d{2,4})',
            r'Ask[:\s]*\$?(\d+\.\d{2,4})',
            r'\$(\d+\.\d{2,4})\s*×\s*\d+',  # $0.08 × 1,501 format
            r'Ask[:\s]*(\d+\.\d{2,4})',  # Robinhood format
        ],
        'volume': [
            r'Volume[:\s]+(\d+(?:,\d+)*)',
            r'Vol[:\s]+(\d+(?:,\d+)*)',
            r'Volume[:\s]*(\d+(?:,\d+)*)',
            r'Volume[:\s]*(\d{1,3}(?:,\d{3})*)',  # 14,029 format
            r'Volume[:\s]*(\d+)',  # Simple format
        ],
        'open_interest': [
            r'Open Interest[:\s]+(\d+(?:,\d+)*)',
            r'OI[:\s]+(\d+(?:,\d+)*)',
            r'Open Interest[:\s]*(\d+(?:,\d+)*)',
            r'Open interest[:\s]*(\d{1,3}(?:,\d{3})*)',  # 3,726 format
            r'Open Interest[:\s]*(\d+)',  # Simple format
        ],
        'theta': [
            r'Theta[:\s]+(-?\d+\.\d{2,4})',
            r'θ[:\s]+(-?\d+\.\d{2,4})',
            r'Theta[:\s]*(-?\d+\.\d+)',  # More flexible
            r'θ[:\s]*(-?\d+\.\d+)',
            r'Theta[:\s]*(-?\d+\.\d{4})',  # 4 decimal places
            r'Theta[:\s]*(\d+\.\d{4})',  # Positive format
            r'Theta[:\s]*(-?\d+\.\d{4})',  # -0.1305 format
            r'Theta[:\s]*(-?\d+\.\d{2,4})',  # Robinhood format
        ],
        'gamma': [
            r'Gamma[:\s]+(\d+\.\d{2,4})',
            r'Γ[:\s]+(\d+\.\d{2,4})',
            r'Gamma[:\s]*(\d+\.\d+)',  # More flexible
            r'Γ[:\s]*(\d+\.\d+)',
            r'Gamma[:\s]*(\d+\.\d{4})',  # 4 decimal places
            r'Gamma[:\s]*(\d+\.\d{2,4})',  # Robinhood format
        ],
        'delta': [
            r'Delta[:\s]+(-?\d+\.\d{2,4})',
            r'Δ[:\s]+(-?\d+\.\d{2,4})',
            r'Delta[:\s]*(-?\d+\.\d+)',  # More flexible
            r'Δ[:\s]*(-?\d+\.\d+)',
            r'Delta[:\s]*(-?\d+\.\d{4})',  # 4 decimal places
            r'Delta[:\s]*(-?\d+\.\d{2,4})',  # Robinhood format
        ],
        'vega': [
            r'Vega[:\s]+(\d+\.\d{2,4})',
            r'ν[:\s]+(\d+\.\d{2,4})',
            r'Vega[:\s]*(\d+\.\d+)',  # More flexible
            r'ν[:\s]*(\d+\.\d+)',
            r'Vega[:\s]*(\d+\.\d{4})',  # 4 decimal places
            r'Vega[:\s]*(\d+\.\d{2,4})',  # Robinhood format
        ],
        'high': [
            r'(?:Day\s+)?High[:\s]+\$?(\d+\.\d{2,4})',
            r'High\s+\$?(\d+\.\d{2,4})',
            r'High[:\s]*\$?(\d+\.\d{2,4})',  # Robinhood format
        ],
        'low': [
            r'(?:Day\s+)?Low[:\s]+\$?(\d+\.\d{2,4})',
            r'Low\s+\$?(\d+\.\d{2,4})',
            r'Low[:\s]*\$?(\d+\.\d{2,4})',  # Robinhood format
        ],
        'strike': [
            r'Strike[:\s]+\$?(\d+)',
            r'Strike\s+Price[:\s]+\$?(\d+)',
            r'Strike[:\s]*\$?(\d+)',  # Robinhood format
        ],
        'expiration': [
            r'(?:Exp|Expires?)[:\s]+(\d{1,2}/\d{1,2}(?:/\d{2,4})?)',
            r'Expiration[:\s]+(\d{1,2}/\d{1,2}(?:/\d{2,4})?)',
            r'Expires[:\s]*(\d{1,2}/\d{1,2}(?:/\d{2,4})?)',  # Robinhood format
        ]
    }
    
    print("🧪 Testing data extraction patterns...")
    print("=" * 50)
    
    extracted_data = {}
    total_extracted = 0
    
    for field, pattern_list in patterns.items():
        for pattern in pattern_list:
            try:
                matches = re.findall(pattern, sample_content, re.IGNORECASE)
                if matches:
                    value = matches[0].replace(',', '').strip()
                    extracted_data[field] = value
                    total_extracted += 1
                    print(f"✅ {field}: {value} (pattern: {pattern[:30]}...)")
                    break  # Found match, move to next field
            except Exception as pattern_error:
                continue
    
    print(f"\n📊 Total fields extracted: {total_extracted}")
    print(f"📋 Extracted data: {json.dumps(extracted_data, indent=2)}")
    
    # Test expected values
    expected_values = {
        'current_price': '621.23',
        'bid': '0.08',
        'ask': '0.09',
        'volume': '14029',
        'open_interest': '3726',
        'theta': '-0.1305',
        'gamma': '0.0116',
        'delta': '0.0347',
        'vega': '0.0339',
        'high': '0.12',
        'low': '0.05',
        'strike': '635',
        'expiration': '8/4/2025'
    }
    
    print(f"\n🎯 Testing against expected values:")
    for field, expected in expected_values.items():
        actual = extracted_data.get(field, 'NOT_FOUND')
        status = "✅" if actual == expected else "❌"
        print(f"{status} {field}: expected {expected}, got {actual}")
    
    success_count = sum(1 for field, expected in expected_values.items() 
                       if extracted_data.get(field) == expected)
    
    print(f"\n📈 Success rate: {success_count}/{len(expected_values)} ({success_count/len(expected_values)*100:.1f}%)")
    
    return extracted_data

def main():
    """Main test function."""
    print("🚀 Improved Data Extraction Test")
    print("=" * 50)
    
    # Test the patterns
    result = test_data_extraction_patterns()
    
    if len(result) >= 8:  # At least 8 fields extracted
        print("\n✅ Test PASSED: Sufficient data extraction")
    else:
        print("\n❌ Test FAILED: Insufficient data extraction")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    main() 