# ASP.NET to ASP.NET Core, incrementally

An ASP.NET (System.Web) application is not retargeted in place: it is replaced route by route behind a strangler fig.

1. Put a new ASP.NET Core application in front. It forwards every request it does not handle yet to the old
   application with YARP (a reverse proxy library).
2. Share code between the two with the System.Web adapters, so a library can run in both while callers move.
3. Move one route, or one group of routes, at a time; each move is its own story, characterised and shadow-run.
   Session state and authentication are shared between the two apps during the move, decided up front.
4. When no route is forwarded any more, the old application is decommissioned (`modernize-cutover`).

Plan it as a programme lane with `modernize-wave-plan`: the routing layer is the seam, each wave a set of routes.
