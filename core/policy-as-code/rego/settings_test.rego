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

test_disable_all_hooks_is_denied if {
	"disableAllHooks must not be true: no hook would run" in denials(object.union(good, {"disableAllHooks": true}))
}

test_disable_all_hooks_false_passes if {
	count(denials(object.union(good, {"disableAllHooks": false}))) == 0
}

test_event_with_empty_inner_hook_list_is_denied if {
	bad := object.union(good, {"hooks": {"PostToolUse": [{"hooks": []}]}})
	"hooks.PostToolUse has no entry" in denials(bad)
}

test_event_with_entries_but_no_inner_hook_is_denied if {
	bad := object.union(good, {"hooks": {"PreToolUse": [{"matcher": "X"}, {"hooks": []}]}})
	"hooks.PreToolUse has no entry" in denials(bad)
}

test_wildcard_argument_allows_are_bare_tool_rules if {
	every rule in ["Bash(*)", "Bash(:*)", "Edit(**)", "WebFetch(*)"] {
		some msg in denials(object.union(good, {"permissions": {"allow": ["Read", rule]}}))
		contains(msg, sprintf("bare tool rule '%s'", [rule]))
	}
}

test_specific_argument_allow_is_not_bare if {
	count(denials(object.union(good, {"permissions": {"allow": ["Read", "Bash(git status:*)"]}}))) == 0
}

test_enabled_plugin_from_unknown_marketplace_is_denied if {
	bad := json.patch(good, [{"op": "add", "path": "/enabledPlugins", "value": {"evil@somewhere": true}}])
	"enabledPlugins: 'evil@somewhere' is not from an approved marketplace" in denials(bad)
}

test_unknown_marketplace_registration_is_denied if {
	bad := json.patch(good, [{"op": "add", "path": "/extraKnownMarketplaces",
		"value": {"somewhere": {"source": {"source": "github", "repo": "evil/x"}}}}])
	"extraKnownMarketplaces: 'somewhere' is not an approved marketplace, or its source differs" in denials(bad)
}

test_a_disabled_plugin_from_anywhere_is_allowed if {
	ok := json.patch(good, [{"op": "add", "path": "/enabledPlugins", "value": {"any@where": false}}])
	count(denials(ok)) == 0
}
