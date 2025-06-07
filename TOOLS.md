# 5mins-learning-app Tools

This document outlines the various tools and utilities available for development, testing, and maintenance of the 5mins-learning-app.

## Database Tools

### Database Management (`db/db_manager.py`)
- Reset and initialize the database
- Create tables based on SQLAlchemy models
- Create test user for development

```bash
# Reset entire database
./db/reset_db.sh

# Targeted operations
python -m db.db_manager --recreate     # Drop/recreate database
python -m db.db_manager --tables       # Create tables
python -m db.db_manager --test-user    # Create test user
```

### Database Visualization (`db/visualize_db.py`)
- View database contents
- Inspect conversations, messages, and users
- Generate statistics
- View detailed message information including LLM metadata

```bash
# Basic usage
python -m db.visualize_db

# Specific views
python -m db.visualize_db --table users
python -m db.visualize_db --conversation [ID]
python -m db.visualize_db --user [ID]
python -m db.visualize_db --message [ID]
```

## Test Tools

### Unit Tests (`app/tests/mock_tests/`)
- Tests individual components with mocked dependencies
- Tests service and API endpoint logic
- Run with pytest: `pytest app/tests/mock_tests/`

### Integration Tests (`app/tests/real_tests/`)
- Test against live server: `app/tests/real_tests/test_live_server.py`
- Tests complete API flows

```bash
# Start the server
uvicorn app.main:app --reload

# In another terminal, run the integration tests
python -m app.tests.real_tests.test_live_server
```

## Development Environment

### Server 
- Start the development server: `uvicorn app.main:app --reload`
- Server runs on: `http://localhost:8000`
- API docs available at: `http://localhost:8000/docs`

### API Endpoints

#### Conversations
- `POST /api/conversations` - Create a new conversation
- `POST /api/conversations/{conversation_id}/first-reply` - Generate first reply
- `GET /api/conversations/{conversation_id}/messages` - Get messages

#### Messages
- `GET /api/messages/{message_id}` - Get a specific message
- `POST /api/messages` - Create a new message

#### Users
- `GET /api/users/{user_id}` - Get a user
- `POST /api/users` - Create a new user

#### Streaming
- `POST /api/stream` - Stream query responses

### LLM Integration

The app integrates with multiple LLM providers:
- OpenAI (ChatGPT)
- Anthropic (Claude)
- Google (Gemini)
- Local LLM (Ollama with Gemma)

## Testing Flow

For a complete test of the API:

1. Reset database:
   ```bash
   ./db/reset_db.sh
   ```

2. Start server:
   ```bash
   uvicorn app.main:app --reload
   ```

3. Run integration tests:
   ```bash
   python -m app.tests.real_tests.test_live_server
   ```

4. Analyze results by inspecting the database:
   ```bash
   python -m db.visualize_db
   ```

## Common Workflows

### Adding a New API Endpoint

1. Add route handler to appropriate router file in `app/routers/`
2. Implement service method in related service file in `app/services/`
3. Add schema definitions if needed in `app/schemas/`
4. Add unit tests in `app/tests/mock_tests/`
5. Add integration test case in `app/tests/real_tests/test_live_server.py`

### Debugging Database Issues

1. View database content:
   ```bash
   python -m db.visualize_db
   ```

2. Inspect specific conversation:
   ```bash
   python -m db.visualize_db --conversation [ID]
   ```

3. Reset database if needed:
   ```bash
   ./db/reset_db.sh
