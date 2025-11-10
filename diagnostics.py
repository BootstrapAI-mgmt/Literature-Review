# Save as: check_papers.py
import os
from pathlib import Path


def check_papers_location():
    """Quick diagnostic to find your papers"""

    print("=" * 60)
    print("PAPERS FOLDER DIAGNOSTIC")
    print("=" * 60)

    # Common locations to check
    locations = [
        r'C:\Users\jpcol\OneDrive\Documents\Doctorate\Research\Literature-Review',
        r'C:\Users\jpcol\Documents\Doctorate\Research\Literature-Review',
        r'.\Literature-Review',
        r'..\Literature-Review',
        os.path.join(os.path.expanduser('~'), 'Documents', 'Literature-Review'),
        os.path.join(os.path.expanduser('~'), 'OneDrive', 'Documents', 'Literature-Review'),
    ]

    found = False
    for path in locations:
        exists = os.path.exists(path)
        is_dir = os.path.isdir(path) if exists else False

        print(f"\nChecking: {path}")
        print(f"  Exists: {exists}")
        print(f"  Is Directory: {is_dir}")

        if exists and is_dir:
            # Count files
            total_files = 0
            pdf_files = 0

            for root, dirs, files in os.walk(path):
                total_files += len(files)
                pdf_files += sum(1 for f in files if f.lower().endswith('.pdf'))

            print(f"  Total files: {total_files}")
            print(f"  PDF files: {pdf_files}")

            if pdf_files > 0:
                print(f"  ✅ FOUND YOUR PAPERS HERE!")
                found = True

                # Show folder structure
                print("\n  Folder structure:")
                for root, dirs, files in os.walk(path):
                    level = root.replace(path, '').count(os.sep)
                    indent = ' ' * 2 * level
                    print(f"{indent}{os.path.basename(root)}/")

                    # Show up to 3 PDF files as examples
                    pdf_count = 0
                    subindent = ' ' * 2 * (level + 1)
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            print(f"{subindent}- {file}")
                            pdf_count += 1
                            if pdf_count >= 3:
                                remaining = sum(1 for f in files if f.lower().endswith('.pdf')) - 3
                                if remaining > 0:
                                    print(f"{subindent}... and {remaining} more PDFs")
                                break
                break

    if not found:
        print("\n❌ Could not find your papers folder!")
        print("\nPlease update the PAPERS_FOLDER variable in the script")
        print("to point to your actual Literature-Review folder location.")

    return found


if __name__ == "__main__":
    check_papers_location()
    input("\nPress Enter to exit...")