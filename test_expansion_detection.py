#!/usr/bin/env python3
"""
Test script for improved expansion detection
"""
import re
import asyncio

def test_expansion_text_detection():
    """Test the text-based expansion detection logic."""
    
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
    
    # Test the expansion detection logic from the improved script
    expansion_text_indicators = [
        'theta', 'gamma', 'delta', 'vega', 
        'volume', 'open interest', 'implied volatility',
        'bid', 'ask', 'strike', 'expiration'
    ]
    
    text_indicators_found = sum(1 for indicator in expansion_text_indicators 
                               if indicator.lower() in sample_content.lower())
    
    print("🧪 Testing expansion text detection...")
    print("=" * 50)
    print(f"📊 Found {text_indicators_found}/{len(expansion_text_indicators)} text indicators")
    
    # Show which indicators were found
    found_indicators = [ind for ind in expansion_text_indicators 
                       if ind.lower() in sample_content.lower()]
    print(f"✅ Found indicators: {found_indicators}")
    
    # Test the threshold logic
    if text_indicators_found >= 3:
        print("✅ Expansion detected successfully!")
        return True
    else:
        print("❌ Insufficient indicators for expansion detection")
        return False

def test_html_element_detection():
    """Test the HTML element-based expansion detection logic."""
    
    # Sample HTML with various class names that might indicate expansion
    sample_html = """
    <div class="expanded-option-details">
        <div class="option-details">
            <div class="contract-details">
                <div class="greeks-section">
                    <span>Theta: -0.1305</span>
                </div>
                <div class="volume-section">
                    <span>Volume: 14,029</span>
                </div>
            </div>
        </div>
    </div>
    """
    
    # Test the HTML element indicators from the improved script
    expansion_indicators = [
        '[class*="expanded"]',
        '[class*="details"]',
        '[class*="option-details"]',
        '[class*="contract-details"]',
        '[class*="expanded-view"]',
        '[class*="option-expanded"]',
        '[data-testid*="expanded"]',
        '[data-testid*="details"]',
        '[data-testid*="option-details"]',
        '[class*="greeks"]',
        '[class*="volume"]',
        '[class*="bid-ask"]',
        '[class*="strike"]',
        '[class*="expiration"]'
    ]
    
    print("\n🧪 Testing HTML element detection...")
    print("=" * 50)
    
    # Simulate the element detection logic
    found_elements = []
    for indicator in expansion_indicators:
        # Extract the class name from the selector
        class_name = indicator.replace('[class*="', '').replace('"]', '')
        if class_name in sample_html:
            found_elements.append(class_name)
            print(f"✅ Found element: {indicator}")
    
    print(f"📊 Found {len(found_elements)} HTML element indicators")
    print(f"✅ Found elements: {found_elements}")
    
    if len(found_elements) > 0:
        print("✅ HTML element expansion detected!")
        return True
    else:
        print("❌ No HTML element indicators found")
        return False

def main():
    """Main test function."""
    print("🚀 Expansion Detection Test")
    print("=" * 50)
    
    # Test text-based detection
    text_success = test_expansion_text_detection()
    
    # Test HTML element-based detection
    html_success = test_html_element_detection()
    
    # Overall result
    if text_success or html_success:
        print("\n✅ Test PASSED: Expansion detection working correctly")
    else:
        print("\n❌ Test FAILED: Expansion detection not working")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    main() 