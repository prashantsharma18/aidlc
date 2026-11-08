---
tags: [routing]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

```python
@app.post('/login')
def login():
    name = request.form['name']
    password = request.form['password']
    row = db.execute("SELECT * FROM users WHERE name='" + name + "'").fetchone()
    if row and row['password'] == password:
        session['user'] = name
        return redirect('/')
    return 'no', 401
```

Is this safe?
