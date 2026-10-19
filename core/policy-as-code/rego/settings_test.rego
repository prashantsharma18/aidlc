package aidlc.settings_test

import data.aidlc.settings

effective := {"secret_paths": [".env"], "protected_paths": ["AGENTS.md"]}

expected_deny_read := ["./.env", "./**/.env"]

good := {
	"permissions": {
		"allow": ["Read", "Bash(git status)"],
		"deny": ["Read(.env)", "Edit(AGENTS.md)"],
		"disableBypassPermissionsMode": "disable",
	},
	"sandbox": {
		"enabled": true, "failIfUnavailable": true, "allowUnsandboxedCommands": false,
		"filesystem": {"denyRead": ["./.env", "./**/.env"]},
	},
	"hooks": {
		"PreToolUse": [{"hooks": [{"onFailure": "block"}]}],
		"PostToolUse": [{"hooks": [{"onFailure": "block"}]}],
		"PostToolUseFailure": [{"hooks": [{"onFailure": "block"}]}],
	},
}

denials(doc) := d if {
	d := settings.deny with input as doc with data.aidlc.effective as effective
		with data.aidlc.sandbox_deny_read as expected_deny_read
}

test_rendered_settings_pass if {
	count(denials(good)) == 0
}

test_sandbox_disabled_is_denied if {
	"sandbox.enabled must be true" in denials(object.union(good, {"sandbox": {"enabled": false}}))
}

test_missing_sandbox_is_denied if {
	"sandbox.failIfUnavailable must be true" in denials(object.remove(good, ["sandbox"]))
}

test_unsandboxed_fallback_is_denied if {
	"sandbox.allowUnsandboxedCommands must be false" in denials(object.union(good, {"sandbox": {"allowUnsandboxedCommands": true}}))
}

test_bypass_mode_is_denied if {
	"permissions.disableBypassPermissionsMode must be 'disable'" in denials(object.union(good, {"permissions": {"disableBypassPermissionsMode": "allow"}}))
}

test_missing_secret_rule_is_denied if {
	"secret path .env has no Read() deny rule" in denials(object.union(good, {"permissions": {"deny": ["Edit(AGENTS.md)"]}}))
}

test_missing_protected_rule_is_denied if {
	"protected path AGENTS.md has no Edit() deny rule" in denials(object.union(good, {"permissions": {"deny": ["Read(.env)"]}}))
}

test_missing_failure_hook_is_denied if {
	"hooks.PostToolUseFailure has no entry" in denials(json.remove(good, ["hooks/PostToolUseFailure"]))
}

test_hook_without_block_is_denied if {
	bad := object.union(good, {"hooks": {"PreToolUse": [{"hooks": [{"onFailure": "continue"}]}]}})
	"a hooks.PreToolUse hook does not set onFailure: block" in denials(bad)
}

test_bare_tool_allow_is_denied if {
	some msg in denials(object.union(good, {"permissions": {"allow": ["Read", "Bash"]}}))
	contains(msg, "bare tool rule 'Bash'")
}

test_missing_policy_data_is_denied if {
	d := settings.deny with input as good with data.aidlc.effective as {}
		with data.aidlc.sandbox_deny_read as expected_deny_read
	"policy data missing: run through `aidlc policy conftest`" in d
}

test_missing_sandbox_deny_read_is_denied if {
	bad := object.union(good, {"sandbox": {"filesystem": {"denyRead": ["./.env"]}}})
	"sandbox.filesystem.denyRead lacks ./**/.env: commands could read a secret" in denials(bad)
}

test_mcp_tool_allow_is_not_a_bare_class if {
	count(denials(object.union(good, {"permissions": {"allow": ["Read", "mcp__lab-jira__getjiraissue"]}}))) == 0
}
