# Trusted-CI policy for a repository's .aidlc/permissions.yaml (ADR 0001): a repository narrows
# the baseline; it never re-allows a baseline deny, and every loosening has a reason and an owner.
# Data: data.aidlc.baseline.deny (core/policy/permissions.yaml) and data.aidlc.refused_writes.
package aidlc.narrowing

loosening_keys := ["allow_add", "network_allow_add", "sandbox_allow_write_add"]

baseline_deny := data.aidlc.baseline.deny

deny contains "policy data missing: run through `aidlc policy conftest`" if {
	not data.aidlc.baseline.deny
}

deny contains msg if {
	some entry in object.get(input, "allow_add", [])
	entry.pattern in object.get(baseline_deny, entry.kind, [])
	msg := sprintf("allow_add re-allows the baseline deny '%s' (%s)", [entry.pattern, entry.kind])
}

deny contains msg if {
	some key in loosening_keys
	some entry in object.get(input, key, [])
	trim_space(object.get(entry, "reason", "")) == ""
	msg := sprintf("a %s entry has no reason", [key])
}

deny contains msg if {
	some key in loosening_keys
	some entry in object.get(input, key, [])
	trim_space(object.get(entry, "owner", "")) == ""
	msg := sprintf("a %s entry has no owner", [key])
}

deny contains msg if {
	some entry in object.get(input, "network_allow_add", [])
	contains(entry.value, "*")
	msg := sprintf("network_allow_add '%s' uses a wildcard host", [entry.value])
}

deny contains msg if {
	some entry in object.get(input, "sandbox_allow_write_add", [])
	refused_write(entry.value)
	msg := sprintf("sandbox_allow_write_add '%s' is a refused location", [entry.value])
}

refused_write(value) if {
	value in {"/", "~", "~/"}
}

refused_write(value) if {
	some prefix in data.aidlc.refused_writes
	startswith(value, prefix)
}
