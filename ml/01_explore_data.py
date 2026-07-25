"""
Step 1: Explore the raw dataset.

Run this FIRST after downloading the CSV from Kaggle, before anything else.
It prints the actual column names, data types, missing values, and target
distribution -- since Kaggle dataset column names can vary slightly between
versions/uploads, we confirm the real structure before writing cleaning logic
that assumes the wrong names.

Usage:
    python 01_explore_data.py
"""

import pandas as pd

RAW_DATA_PATH = "data/smart_mobility_traffic.csv"  # <- update if your filename differs


def main():
    df = pd.read_csv(RAW_DATA_PATH)

    print("=" * 70)
    print("SHAPE:", df.shape)
    print("=" * 70)

    print("\nCOLUMNS:")
    for col in df.columns:
        print(f"  - {col}  (dtype: {df[col].dtype})")

    print("\nFIRST 5 ROWS:")
    print(df.head())

    print("\nMISSING VALUES PER COLUMN:")
    print(df.isnull().sum())

    # Try to find the target column automatically (common naming variants)
    target_candidates = [c for c in df.columns if "congestion" in c.lower()]
    print(f"\nLikely target column(s): {target_candidates}")

    if target_candidates:
        target_col = target_candidates[0]
        print(f"\nValue counts for '{target_col}':")
        print(df[target_col].value_counts())

    print("\n" + "=" * 70)
    print("NEXT STEP: open 02_preprocess.py and update the CONFIG section")
    print("at the top to match the exact column names printed above.")
    print("=" * 70)


if __name__ == "__main__":
    main()
