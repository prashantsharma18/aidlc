package aidlc.narrowing_test

import data.aidlc.narrowing

aidlc_data := {
	"baseline": {"deny": {"shell": ["git push*"], "edit": ["AGENTS.md"], "read": [".env"], "tools": []}},
	"refused_writes": ["~/.claude", "~/.aidlc", "/usr"],
}

# Mock the leaves, never data.aidlc itself: that is a prefix of this policy's own package
# (data.aidlc.narrowing), and a `with` on a prefix hides the rules being tested.
denials(doc) := d if {
	d := narrowing.deny with input as doc
		with data.aidlc.baseline as aidlc_data.baseline
		with data.aidlc.refused_writes as aidlc_data.refused_writes
}

good := {
	"deny_add": {"shell": ["terraform apply*"]},
	"allow_add": [{"kind": "shell", "pattern": "docker build*", "reason": "images", "owner": "@team"}],
	"network_allow_add": [{"value": "registry.example.com", "reason": "mirror", "owner": "@team"}],
	"sandbox_allow_write_add": [{"value": "~/.cache/build", "reason": "cache", "owner": "@team"}],
}

test_narrowing_passes if {
	count(denials(good)) == 0
}

test_empty_file_passes if {
	count(denials({})) == 0
}

test_reallowing_a_baseline_deny_is_denied if {
	bad := object.union(good, {"allow_add": [{"kind": "shell", "pattern": "git push*", "reason": "x", "owner": "@t"}]})
	"allow_add re-allows the baseline deny 'git push*' (shell)" in denials(bad)
}

test_loosening_without_reason_is_denied if {
	bad := object.union(good, {"network_allow_add": [{"value": "x.example.com", "reason": " ", "owner": "@t"}]})
	"a network_allow_add entry has no reason" in denials(bad)
}

test_loosening_without_owner_is_denied if {
	bad := object.union(good, {"sandbox_allow_write_add": [{"value": "~/.cache/x", "reason": "r"}]})
	"a sandbox_allow_write_add entry has no owner" in denials(bad)
}

test_wildcard_host_is_denied if {
	bad := object.union(good, {"network_allow_add": [{"value": "*.example.com", "reason": "r", "owner": "@t"}]})
	"network_allow_add '*.example.com' uses a wildcard host" in denials(bad)
}

test_refused_write_locations_are_denied if {
	every value in ["~", "/", "~/.claude/settings.json", "/usr/local/bin"] {
		bad := object.union(good, {"sandbox_allow_write_add": [{"value": value, "reason": "r", "owner": "@t"}]})
		sprintf("sandbox_allow_write_add '%s' is a refused location", [value]) in denials(bad)
	}
}

test_missing_policy_data_is_denied if {
	d := narrowing.deny with input as good with data.aidlc.baseline as {}
		with data.aidlc.refused_writes as aidlc_data.refused_writes
	"policy data missing: run through `aidlc policy conftest`" in d
}
