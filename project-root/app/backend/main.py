from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncpg
import os
import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:password@postgres:5432/tasktracker"
)

class TaskBase(BaseModel):
    title: str

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int
    
    class Config:
        from_attributes = True

pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    global pool
    
    try:
        pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        logger.info("Database connection pool created successfully")
        
        await create_tables()
        
    except Exception as e:
        logger.error(f"Failed to create database connection pool: {e}")
        raise
    
    yield
    
    if pool:
        await pool.close()
        logger.info("Database connection pool closed")

app = FastAPI(
    title="Task Tracker API",
    description="A simple task management API with PostgreSQL backend",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_db():
    """Get database connection from pool"""
    if pool is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    async with pool.acquire() as connection:
        yield connection

async def create_tables():
    """Create necessary database tables"""
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("Database tables created/verified")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Task Tracker API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes liveness probe"""
    try:
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint for Kubernetes readiness probe"""
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT COUNT(*) FROM tasks")
        return {"status": "ready", "tasks_count": result}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")

@app.get("/api/tasks", response_model=List[Task])
async def get_tasks(db: asyncpg.Connection = Depends(get_db)):
    """Get all tasks"""
    try:
        rows = await db.fetch("SELECT id, title FROM tasks ORDER BY id")
        return [Task(id=row['id'], title=row['title']) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tasks")

@app.post("/api/tasks", response_model=Task, status_code=201)
async def create_task(task: TaskCreate, db: asyncpg.Connection = Depends(get_db)):
    """Create a new task"""
    try:
        if not task.title or not task.title.strip():
            raise HTTPException(status_code=400, detail="Task title cannot be empty")
        
        row = await db.fetchrow(
            "INSERT INTO tasks (title) VALUES ($1) RETURNING id, title",
            task.title.strip()
        )
        
        return Task(id=row['id'], title=row['title'])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail="Failed to create task")

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int, db: asyncpg.Connection = Depends(get_db)):
    """Delete a task by ID"""
    try:
        result = await db.execute("DELETE FROM tasks WHERE id = $1", task_id)
        
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {"message": "Task deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete task")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )