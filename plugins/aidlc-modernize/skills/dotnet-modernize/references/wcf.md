# WCF services

.NET does not host WCF services. Three ways forward, chosen in `aidlc-design`:

| Option | Keeps | Changes for consumers | When |
|---|---|---|---|
| CoreWCF (community WCF server for .NET) | the SOAP contract and most service code | nothing, if bindings are supported | many external consumers you cannot move |
| gRPC | strong contracts, performance | a new contract: every consumer moves | internal consumers you control |
| HTTP APIs (OpenAPI) | simplicity | a new contract: every consumer moves | public or web consumers |

A new contract is a contract change: version it, keep the old endpoint until runtime evidence shows its consumers
have moved, and give each consumer's owner a schedule (a coordination plan when they live in other repositories).
WCF clients run on .NET through the WCF client packages (`System.ServiceModel.*`), so a consumer can move separately.
