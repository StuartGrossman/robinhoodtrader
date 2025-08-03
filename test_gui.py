#!/usr/bin/env python3
"""
Simple GUI test to check if tkinter is working
"""
import tkinter as tk
import sys

def test_basic_gui():
    """Test basic GUI functionality."""
    print("🧪 Testing basic GUI...")
    print(f"🐍 Python version: {sys.version}")
    
    try:
        # Test tkinter import
        print("📦 Testing tkinter import...")
        import tkinter as tk
        print("✅ tkinter imported successfully")
        
        # Test GUI creation
        print("🎨 Creating test window...")
        root = tk.Tk()
        root.title("GUI Test")
        root.geometry("400x300")
        root.configure(bg='#0d1117')
        
        # Add test content
        label = tk.Label(root, text="🎉 GUI is working!", 
                        font=('Arial', 16, 'bold'),
                        fg='#58a6ff', bg='#0d1117')
        label.pack(pady=50)
        
        button = tk.Button(root, text="Close Test", 
                          command=root.quit,
                          font=('Arial', 12),
                          bg='#238636', fg='white')
        button.pack(pady=20)
        
        status_label = tk.Label(root, text="If you see this, tkinter is working correctly!", 
                               font=('Arial', 10),
                               fg='#8b949e', bg='#0d1117')
        status_label.pack(pady=20)
        
        print("✅ Test window created successfully")
        print("🖥️  GUI window should be visible now")
        print("📋 If you don't see a window, there may be a display issue")
        
        # Show the window
        root.mainloop()
        
        print("✅ GUI test completed successfully")
        
    except Exception as e:
        print(f"❌ GUI test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_basic_gui()