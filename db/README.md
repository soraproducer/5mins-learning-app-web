# Database Management Tools

This directory contains tools for database management, setup, and visualization for the 5mins-learning-app.

## Overview

The database layer of the 5mins-learning-app consists of:

- PostgreSQL database
- SQLAlchemy ORM models (in `app/models`)
- Async database operations

## Tools

### 1. Database Manager (`db_manager.py`)

A utility script for creating, resetting, and initializing the database.

```bash
# Reset the entire database (recreate + tables + test user)
./db/reset_db.sh

# Run specific operations
python -m db.db_manager --recreate     # Drop and recreate database
python -m db.db_manager --tables       # Create tables
python -m db.db_manager --test-user    # Create test user
```

The script provides:
- Database recreation
- Table schema creation based on SQLAlchemy models
- Test user creation with fixed UUID for testing

### 2. Database Visualizer (`visualize_db.py`)

A tool for inspecting and visualizing database content.

```bash
# Show all tables with default limit of 10 records
python -m db.visualize_db

# View specific table
python -m db.visualize_db --table users
python -m db.visualize_db --table conversations
python -m db.visualize_db --table messages

# Change output format
python -m db.visualize_db --format json
python -m db.visualize_db --format text

# View conversation with messages
python -m db.visualize_db --conversation [CONVERSATION_ID]

# View user with conversations
python -m db.visualize_db --user [USER_ID]

# Limit number of records
python -m db.visualize_db --limit 20
```

Features:
- Table statistics
- Formatted display of table contents
- Conversation tree view with messages
- User profile view with conversations

## Schema Overview

### Users
- `user_id`: UUID (primary key)
- `user_name`: String
- `created_at`: DateTime
- `updated_at`: DateTime

### Conversations
- `conversation_id`: UUID (primary key)
- `user_id`: UUID (foreign key to users)
- `user_name`: String
- `topic`: String
- `created_at`: DateTime
- `updated_at`: DateTime

### Messages
- `message_id`: UUID (primary key)
- `conversation_id`: UUID (foreign key to conversations)
- `role`: String ('user', 'assistant', or 'system')
- `content`: Text
- `timestamp`: DateTime
- `parent_message_id`: UUID (foreign key to messages, optional)
- `llm_id`: String (optional)
- `llm_metadata`: JSONB (optional)

## Testing

For testing purposes:
1. Reset database: `./db/reset_db.sh`
2. Run API server: `uvicorn app.main:app --reload`
3. Run integration tests: `python -m app.tests.real_tests.test_live_server`
