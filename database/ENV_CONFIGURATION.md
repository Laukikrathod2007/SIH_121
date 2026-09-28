# Environment Configuration Guide

## Using .env for Secure Configuration

The NWIS database uses environment variables via a `.env` file to manage sensitive configuration data like database passwords. This is a security best practice that keeps credentials out of source code.

---

## 🔐 Why Use .env Files?

### Security Benefits
- ✅ **Never committed to git** - `.env` is in `.gitignore`
- ✅ **Different per environment** - dev, staging, production have separate configs
- ✅ **No hardcoded passwords** - keeps code clean and secure
- ✅ **Industry standard** - used by 12-factor apps and modern frameworks

### Without .env (❌ Bad Practice)
```python
# DON'T DO THIS - Password in source code!
password: str = "mySecretPassword123"
```

### With .env (✅ Good Practice)
```python
# Configuration reads from environment
password: str = os.getenv("DB_PASSWORD")
```

---

## 📋 Setup Methods

### Method 1: Manual Creation (Fast)

**Step 1: Copy the example**
```bash
cd c:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS\database
copy .env.example .env
```

**Step 2: Edit .env**
```bash
notepad .env
```

**Step 3: Update the password**
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nwis_db
DB_USER=postgres
DB_PASSWORD=your_actual_password_here  ← Change this line!
```

**Step 4: Save and close**

---

### Method 2: Interactive Setup (Recommended)

Run the helper script:
```bash
python setup_env.py
```

This script will:
1. Prompt for all configuration values
2. Use secure password input (hidden)
3. Confirm password to prevent typos
4. Create the .env file automatically
5. Display a summary

**Example session:**
```
Database Host [localhost]: 
Database Port [5432]: 
Database Name [nwis_db]: 
Database User [postgres]: 
Password: ********
Confirm Password: ********

✅ SUCCESS! .env file created successfully
```

---

## 📁 .env File Format

Your `.env` file should contain:

```bash
# NWIS Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nwis_db
DB_USER=postgres
DB_PASSWORD=YourActualPassword123
```

### Configuration Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DB_HOST` | PostgreSQL server hostname | localhost | Yes |
| `DB_PORT` | PostgreSQL server port | 5432 | Yes |
| `DB_NAME` | Database name | nwis_db | Yes |
| `DB_USER` | Database username | postgres | Yes |
| `DB_PASSWORD` | Database password | (none) | **Yes** |

---

## ✅ Verification

### Test 1: Check .env exists
```bash
dir .env
```
You should see the file listed.

### Test 2: Test database connection
```bash
python config/db_config.py
```
Expected output:
```
Testing database connection...
✓ Connection successful!
✓ Current database: {'current_database': 'nwis_db', 'current_user': 'postgres'}
```

### Test 3: Verify environment loading
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Password loaded:', 'YES' if os.getenv('DB_PASSWORD') else 'NO')"
```
Expected output:
```
Password loaded: YES
```

---

## 🔒 Security Best Practices

### DO ✅
- Keep `.env` in `.gitignore`
- Use different `.env` files for different environments
- Back up `.env` securely (password manager, encrypted storage)
- Rotate passwords regularly
- Use strong passwords (12+ characters, mixed case, numbers, symbols)

### DON'T ❌
- Never commit `.env` to git
- Never share `.env` in chat/email
- Never use the same password for all environments
- Never store passwords in source code
- Never use weak passwords like "password123"

---

## 🌍 Multiple Environments

For different deployment environments:

### Development (.env)
```bash
DB_HOST=localhost
DB_NAME=nwis_db
DB_PASSWORD=dev_password_123
```

### Staging (.env.staging)
```bash
DB_HOST=staging-db.example.com
DB_NAME=nwis_staging
DB_PASSWORD=staging_password_456
```

### Production (.env.production)
```bash
DB_HOST=prod-db.example.com
DB_NAME=nwis_production
DB_PASSWORD=super_secure_prod_password_789
```

**Usage:**
```bash
# Development (default)
python init_database.py

# Staging
copy .env.staging .env
python init_database.py

# Production
copy .env.production .env
python init_database.py
```

---

## 🐛 Troubleshooting

### Problem: "Password authentication failed"

**Causes:**
1. Wrong password in .env
2. .env file doesn't exist
3. PostgreSQL user doesn't exist

**Solutions:**

**Check 1: Verify .env exists**
```bash
dir .env
```

**Check 2: Verify password in .env**
```bash
notepad .env
```

**Check 3: Test PostgreSQL user**
```bash
psql -U postgres -d postgres
# Enter the password you put in .env
```

**Check 4: Reset PostgreSQL password**
```sql
-- Connect to PostgreSQL as admin
psql -U postgres
# Then run:
ALTER USER postgres PASSWORD 'your_new_password';
-- Update .env with this new password
```

---

### Problem: ".env file not found"

**Solution:**
```bash
# Check you're in the right directory
cd c:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS\database

# Create .env from example
copy .env.example .env

# Or use the helper script
python setup_env.py
```

---

### Problem: "Module 'dotenv' not found"

**Solution:**
```bash
pip install python-dotenv
```

---

### Problem: Environment variables not loading

**Check the code is loading .env:**
```python
from dotenv import load_dotenv
load_dotenv()  # This must be called before using os.getenv()
```

**Check .env file location:**
The `.env` file should be in the same directory as `config/db_config.py` or in the project root.

---

## 📞 Getting Help

If you still have issues:

1. **Check the main guides:**
   - `QUICK_START.md` - Fast setup
   - `SETUP_INSTRUCTIONS.md` - Detailed guide

2. **Verify your setup:**
   ```bash
   python config/db_config.py
   ```

3. **Check PostgreSQL is running:**
   ```bash
   pg_isready
   ```

4. **View PostgreSQL logs:**
   - Windows: `C:\Program Files\PostgreSQL\14\data\pg_log\`
   - Check for authentication errors

---

## 📚 Additional Resources

- [Python-dotenv Documentation](https://pypi.org/project/python-dotenv/)
- [12-Factor App Config](https://12factor.net/config)
- [PostgreSQL Authentication](https://www.postgresql.org/docs/current/auth-password.html)
