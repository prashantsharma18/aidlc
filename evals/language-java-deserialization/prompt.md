---
tags: [language]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

```java
@WebServlet("/orders/import")
public class ImportOrderServlet extends HttpServlet {
    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        try (ObjectInputStream in = new ObjectInputStream(req.getInputStream())) {
            Order order = (Order) in.readObject();
            orderService.save(order);
            resp.setStatus(HttpServletResponse.SC_CREATED);
        } catch (ClassNotFoundException e) {
            resp.sendError(HttpServletResponse.SC_BAD_REQUEST);
        }
    }
}
```

Review this endpoint for security problems.
