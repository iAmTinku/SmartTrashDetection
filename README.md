# Smart Trash Can Project

## Requirements

- Python 3.11.9
- PostgreSQL 15+

## Setup

python -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate
pip install -r requirements.txt

## Run Server

uvicorn server:app --reload
