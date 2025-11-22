# Backend Component Tests

## Overview
This directory contains individual test scripts for each backend component, allowing you to verify each part of the system independently.

## Test Scripts

### 1. FastAPI Server (`test_1_fastapi.py`)
**Tests**: API endpoints and token generation
```bash
python tests/test_1_fastapi.py
```

### 2. Database (`test_2_database.py`)
**Tests**: PostgreSQL connectivity and CRUD operations
```bash
python tests/test_2_database.py
```

### 3. Storage (`test_3_storage.py`)
**Tests**: Supabase Storage file operations
```bash
python tests/test_3_storage.py
```

### 4. ConflictManager (`test_4_conflict_manager.py`)
**Tests**: Business logic and end-to-end data flow
```bash
python tests/test_4_conflict_manager.py
```

### 5. LiveKit (`test_5_livekit.py`)
**Tests**: Cloud connectivity and token validation
```bash
python tests/test_5_livekit.py
```

## Run All Tests
Execute the complete test suite:
```bash
python tests/run_all_tests.py
```

## Prerequisites
- Backend virtual environment activated
- `.env` file configured with all credentials
- FastAPI server running (for test 1)
- Internet connection (for LiveKit tests)

## Expected Results
All tests should pass (✅) if the backend is configured correctly.
