import React, { useState, useEffect } from 'react'
import './App.css'

const API_BASE_URL = process.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [tasks, setTasks] = useState([])
  const [newTask, setNewTask] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Fetch tasks from backend
  const fetchTasks = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE_URL}/api/tasks`)
      if (!response.ok) throw new Error('Failed to fetch tasks')
      const data = await response.json()
      setTasks(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Add a new task
  const addTask = async (e) => {
    e.preventDefault()
    if (!newTask.trim()) return

    try {
      setLoading(true)
      const response = await fetch(`${API_BASE_URL}/api/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTask.trim() })
      })
      
      if (!response.ok) throw new Error('Failed to add task')
      
      setNewTask('')
      fetchTasks() // Refresh list
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Delete a task
  const deleteTask = async (id) => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE_URL}/api/tasks/${id}`, {
        method: 'DELETE'
      })
      
      if (!response.ok) throw new Error('Failed to delete task')
      fetchTasks() // Refresh list
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTasks()
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <h1>Task Tracker</h1>
        <p>Simple task management application</p>
      </header>

      <main className="app-main">
        {error && (
          <div className="error-message">
            Error: {error}
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        <form onSubmit={addTask} className="task-form">
          <input
            type="text"
            value={newTask}
            onChange={(e) => setNewTask(e.target.value)}
            placeholder="Add a new task..."
            disabled={loading}
          />
          <button type="submit" disabled={loading || !newTask.trim()}>
            {loading ? 'Adding...' : 'Add Task'}
          </button>
        </form>

        <div className="tasks-list">
          {loading && tasks.length === 0 ? (
            <div className="loading">Loading tasks...</div>
          ) : tasks.length === 0 ? (
            <div className="empty-state">No tasks yet. Add one above!</div>
          ) : (
            tasks.map((task) => (
              <div key={task.id} className="task-item">
                <span className="task-title">{task.title}</span>
                <button
                  onClick={() => deleteTask(task.id)}
                  disabled={loading}
                  className="delete-btn"
                >
                  Delete
                </button>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  )
}

export default App