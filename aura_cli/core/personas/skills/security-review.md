---
name: security-review
description: Use this skill when adding authentication, handling user input, creating API endpoints, working with secrets, environment variables, database queries, file uploads, or implementing payment features. Provides OWASP Top 10 checklist and secure Python patterns for injection prevention, secret management, XSS, CSRF, rate limiting, and dependency auditing.
version: 1.0.0
author: Aura Core Team
---

# Security Review Skill

Comprehensive security checklist and secure coding patterns for Python applications.

## When to Activate

- Implementing authentication or authorization
- Handling user input or file uploads
- Creating new API endpoints
- Working with secrets or credentials
- Implementing payment features
- Storing or transmitting sensitive data

## 1. Secret Management

### ❌ NEVER hardcode secrets
```python
api_key = "sk-proj-xxxxx"      # CRITICAL: hardcoded secret
db_password = "password123"    # CRITICAL: in source code
```

### ✅ ALWAYS use environment variables
```python
import os
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not configured")
```

**Checklist:**
- [ ] No API keys, tokens or passwords hardcoded
- [ ] All secrets in environment variables
- [ ] `.env` in `.gitignore`
- [ ] No secrets in git history (`git log -p | grep -i "password\|api_key"`)

## 2. Input Validation — ALWAYS validate

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Annotated

class CreateUserRequest(BaseModel):
    email: EmailStr
    name: Annotated[str, Field(min_length=1, max_length=100)]
    age: Annotated[int, Field(ge=0, le=150)]

def create_user(raw_input: dict):
    try:
        validated = CreateUserRequest(**raw_input)
        return db.users.create(validated.model_dump())
    except ValueError as e:
        return {"success": False, "errors": str(e)}, 400
```

**File Upload Validation:**
```python
def validate_file(file) -> None:
    if file.size > 5 * 1024 * 1024:  # 5MB
        raise ValueError("File too large (max 5MB)")
    allowed_types = {"image/jpeg", "image/png", "image/gif"}
    if file.content_type not in allowed_types:
        raise ValueError(f"Invalid file type: {file.content_type}")
```

## 3. SQL Injection Prevention

```python
# ❌ CRITICAL: SQL injection
query = f"SELECT * FROM users WHERE email = '{user_email}'"
cursor.execute(query)

# ✅ Parameterized queries
cursor.execute("SELECT * FROM users WHERE email = ?", (user_email,))
# OR with ORM:
user = session.query(User).filter(User.email == user_email).first()
```

## 4. Command Injection Prevention

```python
import subprocess
import shlex

# ❌ CRITICAL: command injection
subprocess.run(f"ping {user_input}", shell=True)

# ✅ Use argument list, never shell=True with user input
subprocess.run(["ping", shlex.quote(user_input)], shell=False)
```

## 5. Authentication & Authorization

```python
# Always verify authorization before sensitive operations
async def delete_item(item_id: str, requester_id: str):
    requester = await db.users.get(requester_id)
    if requester.role != "admin":
        raise PermissionError("Unauthorized")
    await db.items.delete(item_id)

# JWT stored securely (httponly cookie, not localStorage)
response.set_cookie(
    "session",
    token,
    httponly=True,
    secure=True,
    samesite="Strict",
    max_age=3600
)
```

## 6. Race Conditions in Financial Operations

```python
# ❌ CRITICAL: race condition
balance = get_balance(user_id)
if balance >= amount:
    withdraw(user_id, amount)  # Another request may withdraw in parallel!

# ✅ Atomic transaction with row lock
async with db.transaction():
    balance = await db.execute(
        "SELECT amount FROM balances WHERE user_id = ? FOR UPDATE",
        (user_id,)
    ).fetchone()
    if balance["amount"] < amount:
        raise ValueError("Insufficient balance")
    await db.execute(
        "UPDATE balances SET amount = amount - ? WHERE user_id = ?",
        (amount, user_id)
    )
```

## 7. Rate Limiting

```python
# Apply rate limiting to all API endpoints
# Stricter limits for expensive/sensitive operations
@app.route("/api/search")
@rate_limit(max_requests=10, window_seconds=60)  # 10/min for search
def search():
    ...

@app.route("/api/login")
@rate_limit(max_requests=5, window_seconds=300)  # 5/5min for auth
def login():
    ...
```

## 8. Safe Error Messages

```python
# ❌ Exposing internal details
except Exception as e:
    return {"error": str(e), "traceback": traceback.format_exc()}, 500

# ✅ Generic message for users, details in logs
except Exception as e:
    logger.error("Internal error: %s", e, exc_info=True)
    return {"error": "An error occurred. Please try again."}, 500
```

## 9. Sensitive Data in Logs

```python
# ❌ Logging sensitive data
logger.info(f"Login: email={email}, password={password}")

# ✅ Redact sensitive fields
logger.info(f"Login attempt: email={email}, password_provided={bool(password)}")
```

## 10. Dependency Security

```bash
# Check for vulnerable dependencies
pip-audit

# Check for outdated packages
pip list --outdated

# Always pin versions in requirements
# ❌ requests>=2.0.0
# ✅ requests==2.31.0
```

## OWASP Top 10 Quick Checklist

Before ANY commit touching security-sensitive code:

- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] All user inputs validated with schemas
- [ ] SQL queries parameterized (no string concatenation)
- [ ] Command execution uses argument lists (no shell=True with user input)
- [ ] Authorization checked before every sensitive operation
- [ ] Rate limiting on all endpoints
- [ ] Error messages don't expose internals
- [ ] Logs don't contain passwords, tokens or PII
- [ ] Dependencies up to date (pip-audit clean)
- [ ] File uploads validated (size, type, extension)

## Security Testing

```python
def test_requires_authentication(client):
    response = client.get("/api/protected")
    assert response.status_code == 401

def test_requires_admin_role(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    response = client.delete("/api/admin/resource", headers=headers)
    assert response.status_code == 403

def test_rejects_invalid_input(client):
    response = client.post("/api/users", json={"email": "not-an-email"})
    assert response.status_code == 400

def test_sql_injection_prevented(client):
    response = client.get("/api/search?q=' OR '1'='1")
    assert response.status_code in (200, 400)
    data = response.get_json()
    assert "users" not in str(data).lower()  # no DB leak
```
