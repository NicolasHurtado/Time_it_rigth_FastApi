# Time It Right

Timer-based game where users try to stop a timer at exactly 10 seconds. Built with FastAPI and Clean Architecture.

## Architecture

Clean Architecture with FastAPI:
- **Domain**: Entities and value objects
- **Application**: Use cases and business logic
- **Infrastructure**: Database and external services  
- **Presentation**: API endpoints and schemas

## Database

SQLite with async support via SQLAlchemy 2.0 and aiosqlite.

## Game Rules

- Target: Stop timer at exactly 10 seconds (10,000ms)
- Scoring: Based on deviation from target
- Leaderboard: Ranked by lowest average deviation

## Features

- **User Authentication**: Register/login with JWT tokens
- **Game Sessions**: Start/stop timer game with accuracy scoring
- **Leaderboard**: Rankings by average deviation from 10-second target
- **User Analytics**: Personal statistics and game history

## Quick Start

### Prerequisites
- Python 3.11+
- Poetry

### Installation

```bash
# Clone repository
git clone <repository-url>
cd time_it_rigth
```

### With Poetry

```bash
# Install dependencies
poetry install

# Set environment variables
cp env.example .env
# Edit .env with your SECRET_KEY

# Run development server
poetry run start
```

### With pip 

```bash
#create virtual environment
python -m venv venv

# activate virtual environment
# on linux or mac
source venv/bin/activate 
# or on windows
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp env.example .env
# Edit .env with your SECRET_KEY

```

### API Endpoints

- **Auth**: `/auth/register`, `/auth/login`, `/auth/profile`
- **Game**: `/games/start`, `/games/{id}/stop`, `/games/history`
- **Leaderboard**: `/leaderboard`
- **Analytics**: `analytics/user/{user_id}`, `/analytics/me`

### Development Tools

```bash
# Code quality
poetry run black .
poetry run isort .
poetry run flake8 .
poetry run mypy .

# Testing
poetry run pytest
#or with pip
pytest -v
```

## 📞 Contact

For any inquiries about the project, contact us at [nicolashurtado0712@gmail.com](mailto:nicolashurtado0712@gmail.com).

---

Developed with ❤️ by Nicolas Hurtado