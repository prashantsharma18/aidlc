# Trusted-CI policy for GitHub Actions workflows (ADR 0001; guide 9.7, 13.8): read-only tokens,
# actions pinned to full commit SHAs, no pull_request_target, no untrusted text inside run:.
package aidlc.workflows

# YAML 1.1 parsers read the key `on` as the boolean true; accept both spellings.
on_value := object.get(input, "on", object.get(input, "true", {}))

jobs := object.get(input, "jobs", {})

triggers contains on_value if {
	is_string(on_value)
}

triggers contains name if {
	is_array(on_value)
	some name in on_value
}

triggers contains name if {
	is_object(on_value)
	some name, _ in on_value
}

deny contains "workflows must not run on pull_request_target: it runs with secrets on untrusted code" if {
	"pull_request_target" in triggers
}

deny contains "set top-level permissions explicitly (contents: read)" if {
	not input.permissions
}

deny contains msg if {
	is_string(input.permissions)
	input.permissions != "read-all"
	msg := sprintf("top-level permissions '%s' is not read-only", [input.permissions])
}

deny contains msg if {
	is_object(input.permissions)
	some scope, level in input.permissions
	level == "write"
	msg := sprintf("top-level permission %s: write; grant write per job, never workflow-wide", [scope])
}

deny contains msg if {
	some job_id, job in jobs
	perms := object.get(job, "permissions", {})
	is_string(perms)
	perms == "write-all"
	msg := sprintf("job %s grants write-all", [job_id])
}

deny contains msg if {
	some job_id, job in jobs
	perms := object.get(job, "permissions", {})
	is_object(perms)
	some scope, level in perms
	level == "write"
	msg := sprintf("job %s grants %s: write; the verify workflow needs read only", [job_id, scope])
}

deny contains msg if {
	some job_id, job in jobs
	some step in object.get(job, "steps", [])
	uses := step.uses
	not startswith(uses, "./")
	not regex.match(`^[^@\s]+@[0-9a-f]{40}$`, uses)
	msg := sprintf("job %s: '%s' is not pinned to a full commit SHA", [job_id, uses])
}

deny contains msg if {
	some job_id, job in jobs
	some step in object.get(job, "steps", [])
	regex.match(`\$\{\{\s*github\.(head_ref|event\.)`, step.run)
	msg := sprintf("job %s: untrusted pull request text is expanded inside run:; pass it through env", [job_id])
}
