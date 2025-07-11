# Quick Setup Guide

## 🚀 Getting Started

### 1. Environment Setup
```bash
# For development (recommended for local work)
./scripts/env-switch.sh dev

# For production (when deploying)
./scripts/env-switch.sh prod

# Check current environment
./scripts/env-switch.sh current
```

**Environment Files:**
- `.env` - Development environment (local)
- `.env.prod` - Production environment (deployment)
- `env.example` - Template (safe to commit)

### 2. Install Dependencies
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Application
```bash
# Development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the built-in runner
python app/main.py
```

### 4. Test the API
- Visit: http://localhost:8000/api/v1/docs
- Try the contact endpoint with the interactive docs

## 📁 Project Structure

```
ai_receptionist/
├── app/                    # Main application code
│   ├── main.py            # FastAPI app entry point
│   ├── config.py          # Configuration settings
│   ├── database.py        # Placeholder (not used)
│   ├── api/               # API routes
│   │   └── v1/            # API version 1
│   │       ├── router.py  # Main router
│   │       └── contact.py # Contact form endpoint
│   └── schemas/           # Pydantic schemas
│       └── contact.py     # Contact form schemas
│   └── supabase_schema/   # Database schema files
│       └── supabase_schema.sql # Supabase table definitions
├── requirements.txt       # Python dependencies
├── env.example           # Environment variables template
└── README.md             # Full documentation
```

## 🔧 Adding New Endpoints

### 1. Create Schema
Create a new file in `app/schemas/` (e.g., `app/schemas/product.py`):
```python
from pydantic import BaseModel
from typing import Optional

class ProductRequest(BaseModel):
    name: str
    price: float
    description: Optional[str] = None
```

### 2. Create Endpoint
Create a new file in `app/api/v1/` (e.g., `app/api/v1/products.py`):
```python
from fastapi import APIRouter
from app.schemas.product import ProductRequest

router = APIRouter()

@router.post("/")
async def create_product(product: ProductRequest):
    print(f"New product: {product.name} - ${product.price}")
    return {"detail": "Product created"}
```

### 3. Add to Router
Update `app/api/v1/router.py`:
```python
from app.api.v1 import products

api_router.include_router(products.router, prefix="/products", tags=["products"])
```

## 📚 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## 🧪 Testing the Contact API

### Using curl:
```bash
curl -X POST "http://localhost:8000/api/v1/contact/" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "John Doe",
       "email": "john@example.com",
       "company": "Acme Corp",
       "subject": "General Inquiry",
       "message": "Hello, I would like to learn more about your services."
     }'
```

### Using Python requests:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/contact/",
    json={
        "name": "John Doe",
        "email": "john@example.com",
        "company": "Acme Corp",
        "subject": "General Inquiry",
        "message": "Hello, I would like to learn more about your services."
    }
)
print(response.json())
```

## 🚨 Common Issues

### Import Errors
- Make sure you're in the virtual environment
- Check that all dependencies are installed

### Port Already in Use
- Change the port in the command: `--port 8001`
- Or kill the process using port 8000

## 📞 Support

For issues or questions:
1. Check the logs in the terminal
2. Review the API documentation
3. Make sure all dependencies are installed 