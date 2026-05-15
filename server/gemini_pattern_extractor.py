#!/usr/bin/env python3
"""
GEMINI Pattern Extractor - Complete Version
Extracts 30 patterns from GEMINI HTML into structured DataFrame
With error handling, validation, and main execution
"""
import re, ast, pandas as pd
import sys

def extract_patterns(html_content):
    """Extract A, B, C pattern groups from GEMINI HTML with error handling"""
    try:
        # Better regex for nested arrays
        A_match = re.search(r'const A_NAMES = (\[[\s\S]*?\]);', html_content)
        B_match = re.search(r'const B_NAMES = (\[[\s\S]*?\]);', html_content)
        C_match = re.search(r'const C_NAMES = (\[[\s\S]*?\]);', html_content)
        
        if not A_match or not B_match or not C_match:
            print("❌ ERROR: Could not extract A_NAMES, B_NAMES, or C_NAMES from HTML")
            return None
        
        A = ast.literal_eval(A_match.group(1))
        B = ast.literal_eval(B_match.group(1))
        C = ast.literal_eval(C_match.group(1))
        
        # Validate data
        if len(A) != 10 or len(B) != 10 or len(C) != 10:
            print(f"❌ ERROR: Expected 10 items per group. Got A={len(A)}, B={len(B)}, C={len(C)}")
            return None
        
        dfs = []
        for data, grp in [(A, 'A·VOLUME'), (B, 'B·PRICE'), (C, 'C·INDICATOR')]:
            df = pd.DataFrame(data, columns=['Name', 'Description'])
            # Extract pattern name (before first dash or danda)
            df['Pattern'] = df['Description'].str.extract(r'^([^–।]+)')[0].str.strip()
            df.insert(0, 'Rank', range(1, 11))
            df.insert(1, 'Group', grp)
            dfs.append(df)
        
        master = pd.concat(dfs, ignore_index=True)
        return master[['Rank', 'Group', 'Name', 'Pattern', 'Description']]
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return None

if __name__ == '__main__':
    print("=" * 60)
    print("GEMINI Pattern Extractor")
    print("=" * 60)
    
    # Read GEMINI HTML
    try:
        with open('gemini.html', 'r', encoding='utf-8') as f:
            html = f.read()
        print("✅ HTML file loaded")
    except FileNotFoundError:
        print("❌ ERROR: gemini.html not found")
        sys.exit(1)
    
    # Extract patterns
    df = extract_patterns(html)
    if df is None:
        sys.exit(1)
    
    print(f"✅ Extracted {len(df)} patterns\n")
    print(df.to_string(index=False))
    
    # Save to CSV
    try:
        df.to_csv('gemini_patterns.csv', index=False)
        print(f"\n✅ Saved: gemini_patterns.csv")
    except Exception as e:
        print(f"❌ ERROR saving CSV: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Summary:")
    print(f"  Total patterns: {len(df)}")
    for grp in ['A·VOLUME', 'B·PRICE', 'C·INDICATOR']:
        count = len(df[df['Group'] == grp])
        print(f"  {grp}: {count}")
    print("=" * 60)
