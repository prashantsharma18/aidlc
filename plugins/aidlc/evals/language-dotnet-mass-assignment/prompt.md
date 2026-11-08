---
tags: [language]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

```csharp
public class User
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
    public string Email { get; set; } = "";
    public bool IsAdmin { get; set; }
}

[ApiController]
[Route("api/users")]
public class UsersController : ControllerBase
{
    private readonly AppDbContext _db;
    public UsersController(AppDbContext db) => _db = db;

    [HttpPut("{id}")]
    public IActionResult Update(int id, [FromBody] User user)
    {
        _db.Users.Update(user);
        _db.SaveChanges();
        return Ok();
    }
}
```

Anything wrong with this endpoint?
