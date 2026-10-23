# Trusted-CI policy for a rendered .claude/settings.json (ADR 0001; design §7).
# Input: the settings file. Data: data.aidlc.effective, the repository's effective permissions
# (core/policy/permissions.yaml narrowed by .aidlc/permissions.yaml), supplied by `aidlc`.
package aidlc.settings

# Helper rules must not be named deny_*, violation_* or warn_*: Conftest runs those as policy rules
# and reports every member as a failure.

hook_events := ["PreToolUse", "PostToolUse", "PostToolUseFailure"]

permissions := object.get(input, "permissions", {})

sandbox := object.get(input, "sandbox", {})

hook_config := object.get(input, "hooks", {})

denied_rules := object.get(permissions, "deny", [])

denied_reads := object.get(object.get(sandbox, "filesystem", {}), "denyRead", [])

deny contains "policy data missing: run through `aidlc policy conftest`" if {
	not data.aidlc.effective.secret_paths
}

deny contains "sandbox.enabled must be true" if {
	not sandbox.enabled == true
}

deny contains "sandbox.failIfUnavailable must be true" if {
	not sandbox.failIfUnavailable == true
}

deny contains "sandbox.allowUnsandboxedCommands must be false" if {
	not sandbox.allowUnsandboxedCommands == false
}

deny contains "permissions.disableBypassPermissionsMode must be 'disable'" if {
	not permissions.disableBypassPermissionsMode == "disable"
}

deny contains msg if {
	some path in data.aidlc.effective.secret_paths
	not sprintf("Read(%s)", [path]) in denied_rules
	msg := sprintf("secret path %s has no Read() deny rule", [path])
}

deny contains msg if {
	some entry in data.aidlc.sandbox_deny_read
	not entry in denied_reads
	msg := sprintf("sandbox.filesystem.denyRead lacks %s: commands could read a secret", [entry])
}

deny contains msg if {
	some path in data.aidlc.effective.protected_paths
	not sprintf("Edit(%s)", [path]) in denied_rules
	msg := sprintf("protected path %s has no Edit() deny rule", [path])
}

# Hooks that can actually run for an event: the inner hooks, not the outer matcher entries.
inner_hooks(event) := [hook |
	some entry in object.get(hook_config, event, [])
	some hook in object.get(entry, "hooks", [])
]

deny contains "disableAllHooks must not be true: no hook would run" if {
	input.disableAllHooks == true
}

deny contains msg if {
	some event in hook_events
	count(inner_hooks(event)) == 0
	msg := sprintf("hooks.%s has no entry", [event])
}

deny contains msg if {
	some event in hook_events
	some entry in object.get(hook_config, event, [])
	some hook in object.get(entry, "hooks", [])
	not hook.onFailure == "block"
	msg := sprintf("a hooks.%s hook does not set onFailure: block", [event])
}

deny contains msg if {
	some rule in object.get(permissions, "allow", [])
	not contains(rule, "(")
	rule != "Read"
	not startswith(rule, "mcp__") # a mapped MCP tool name is a specific tool, not a whole class
	msg := sprintf("permissions.allow has the bare tool rule '%s': it allows every use of the tool", [rule])
}

deny contains msg if {
	some rule in object.get(permissions, "allow", [])
	regex.match(`^\s*[A-Za-z_][A-Za-z0-9_]*\s*\(\s*(\*|:\*|\*\*)\s*\)\s*$`, rule)
	msg := sprintf("permissions.allow has the bare tool rule '%s': it allows every use of the tool", [rule])
}

# Plugins per repository (ADR 0008): only from marketplaces approved in core/policy/plugins.yaml.
default approved_marketplaces := {}

approved_marketplaces := data.aidlc.plugin_marketplaces

deny contains msg if {
	some id, on in object.get(input, "enabledPlugins", {})
	on == true
	not approved_marketplaces[split(id, "@")[1]]
	msg := sprintf("enabledPlugins: '%s' is not from an approved marketplace", [id])
}

deny contains msg if {
	some name, entry in object.get(input, "extraKnownMarketplaces", {})
	not object.get(approved_marketplaces, name, null) == object.get(entry, "source", null)
	msg := sprintf("extraKnownMarketplaces: '%s' is not an approved marketplace, or its source differs", [name])
}
