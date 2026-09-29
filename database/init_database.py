"""
Simple Database Initialization Script
Run this to quickly set up and populate the NWIS database
"""

import sys
import os

# Set the working directory
os.chdir(r'c:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS\database')
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
sys.path.insert(0, os.path.join(os.getcwd(), 'config'))

print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║              NWIS Database Initialization                        ║
║              Quick Setup & Data Loading                          ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
""")

print("📋 Configuration Check:")
print(f"   Working Directory: {os.getcwd()}")
print(f"   Python Version: {sys.version.split()[0]}")

# Check if dependencies are installed
try:
    import psycopg2
    print("   ✓ psycopg2 installed")
except ImportError:
    print("   ✗ psycopg2 not installed")
    print("\n   Installing dependencies...")
    os.system("pip install psycopg2-binary pandas numpy PyPDF2")

try:
    import pandas
    print("   ✓ pandas installed")
except ImportError:
    pass

try:
    import PyPDF2
    print("   ✓ PyPDF2 installed")
except ImportError:
    pass

print("\n" + "─" * 70)
print("⚠️  IMPORTANT: Configure Database Password")
print("─" * 70)
print("""
Before proceeding, you need to set your PostgreSQL password.

Step 1 - Create .env file:
   cd c:\\Users\\harsh_cuhj7z7\\OneDrive\\Documents\\HACKATHON\\NWIS\\database
   copy .env.example .env

Step 2 - Edit .env file:
   Open .env in notepad and change:
   DB_PASSWORD=your_actual_password_here

The .env file keeps your password secure and out of source code.
It's already in .gitignore so it won't be committed to git.
""")

response = input("\n✓ Have you created and configured the .env file? (y/n): ").strip().lower()

if response != 'y':
    print("\n⚠ Please create and configure the .env file first:")
    print("   1. copy .env.example .env")
    print("   2. Edit .env and set DB_PASSWORD")
    print("   3. Run this script again")
    print("\nExiting...")
    sys.exit(0)

print("\n" + "=" * 70)
print("Starting Database Setup...")
print("=" * 70)

# Run master loader
try:
    from master_load import main as run_master_load
    
    print("\n🚀 Running master data loader...\n")
    success = run_master_load()
    
    if success:
        print("\n" + "=" * 70)
        print("✓ ✓ ✓  DATABASE SETUP COMPLETE!  ✓ ✓ ✓")
        print("=" * 70)
        
        print("\n📊 Your database is ready with:")
        print("   • Time-series telemetry data")
        print("   • Daily drilling reports")
        print("   • Well master data")
        print("   • Performance KPIs")
        
        print("\n🔍 Verify your data:")
        print("   python scripts/verify_data.py")
        
        print("\n🚀 Next steps:")
        print("   1. Review data verification results")
        print("   2. Set up the backend API server")
        print("   3. Configure the frontend dashboard")
        
    else:
        print("\n❌ Setup encountered errors. Please check the logs above.")
        print("\n💡 Common issues:")
        print("   • PostgreSQL not running")
        print("   • Incorrect password")
        print("   • CSV files not found")
        print("\nCheck SETUP_INSTRUCTIONS.md for troubleshooting.")
        
except KeyboardInterrupt:
    print("\n\n⚠ Setup interrupted by user.")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error during setup: {e}")
    print("\n💡 Please check:")
    print("   1. PostgreSQL is installed and running")
    print("   2. .env file exists with correct DB_PASSWORD")
    print("   3. All data files are present in data/raw/")
    print("\nSee SETUP_INSTRUCTIONS.md for detailed help.")
    sys.exit(1)
