#!/usr/bin/env python3
"""
Test GUI Updates for SPY Expanded Tracker
"""
import tkinter as tk
from tkinter import ttk
import threading
import time
from datetime import datetime

class TestGUIUpdates:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GUI Update Test")
        self.root.geometry("800x600")
        
        # Create notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create test tab
        self.create_test_tab()
        
        # Start update thread
        self.update_active = True
        self.update_thread = threading.Thread(target=self.update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        
    def create_test_tab(self):
        """Create a test tab with widgets."""
        tab_frame = tk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Test Contract")
        
        # Info text widget
        self.info_text = tk.Text(tab_frame, height=10, bg='#0d1117', fg='#f0f6fc',
                                font=('SF Mono', 10), wrap=tk.WORD)
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Update counter
        self.update_count = 0
        
    def update_info_display(self):
        """Update the info display."""
        try:
            self.update_count += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            
            info = f"""
🧪 GUI UPDATE TEST
{'='*50}
Update Count: {self.update_count}
Current Time: {current_time}
Status: ACTIVE & UPDATING

📊 TEST DATA
Price: ${100 + self.update_count * 0.01:.2f}
Volume: {50 + self.update_count}
Bid: ${99.50 + self.update_count * 0.005:.2f}
Ask: ${100.50 + self.update_count * 0.005:.2f}

🏷️ TEST GREEKS
Delta: {0.5 + self.update_count * 0.001:.4f}
Gamma: {0.02 + self.update_count * 0.0001:.4f}
Theta: {-0.1 - self.update_count * 0.001:.4f}
Vega: {0.05 + self.update_count * 0.0005:.4f}

⏰ Update Frequency: Every 1 second
Last Update: {current_time}
            """
            
            self.info_text.delete('1.0', tk.END)
            self.info_text.insert('1.0', info)
            print(f"✅ Updated info display - Count: {self.update_count}")
            
        except Exception as e:
            print(f"❌ Error updating info display: {e}")
    
    def update_loop(self):
        """Update loop running in background thread."""
        while self.update_active:
            try:
                # Schedule GUI update
                self.root.after(0, self.update_info_display)
                time.sleep(1)  # Update every second
            except Exception as e:
                print(f"❌ Error in update loop: {e}")
                time.sleep(2)
    
    def run(self):
        """Run the test GUI."""
        print("🚀 Starting GUI Update Test...")
        print("📊 Updates should occur every second")
        print("⏹️  Close window to stop")
        
        self.root.mainloop()
        self.update_active = False

def main():
    """Run the GUI update test."""
    test = TestGUIUpdates()
    test.run()

if __name__ == "__main__":
    main() 