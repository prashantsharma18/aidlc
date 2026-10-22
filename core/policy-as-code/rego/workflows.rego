# Trusted-CI policy for GitHub Actions workflows (ADR 0001; guide 9.7, 13.8): read-only tokens, except
# one narrow, approved pull-requests: write for the AI review job (ADR 0004); actions pinned to full
# commit SHAs; no pull_request_target; no untrusted text inside run:.
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

deny contains "workflows must not run on workflow_run: it runs with secrets on the output of untrusted code" if {
	"workflow_run" in triggers
}

# Top-level permissions: an object, or the string read-all. Missing, null, a list or any other string is denied.
valid_permissions if {
	is_object(input.permissions)
}

valid_permissions if {
	input.permissions == "read-all"
}

deny contains "set top-level permissions explicitly (contents: read)" if {
	not valid_permissions
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
	not allowed_write(job, scope)
	msg := sprintf("job %s grants %s: write; the verify workflow needs read only", [job_id, scope])
}

# The one write a job may hold (ADR 0004): pull-requests: write, for the AI review job, so it can post
# inline comments. That job runs in the ai-gates environment (a person approves each run), uses only
# actions/checkout and anthropics/claude-code-action (pinned by the next rule), and runs no shell
# step except two fixed setup commands for the sandbox that scrubs the key from subprocesses, with
# no env or shell override. Its token cannot push (contents stays read) and cannot approve
# (repository setting).
review_actions := {"actions/checkout", "anthropics/claude-code-action"}

review_setup := {
	"sudo apt-get update -q && sudo apt-get install -y -q bubblewrap socat",
	"sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0 || true",
}

review_step(step) if {
	object.get(step, "run", null) == null
	split(object.get(step, "uses", ""), "@")[0] == "actions/checkout"
}

# The review action keeps its key scrubbing, takes no settings or extra users, and grants no gh api
# or open shell (live review finding, 2026-10-22).
review_step(step) if {
	object.get(step, "run", null) == null
	split(object.get(step, "uses", ""), "@")[0] == "anthropics/claude-code-action"
	object.get(object.get(step, "env", {}), "CLAUDE_CODE_SUBPROCESS_ENV_SCRUB", "") == "1"
	inputs := object.get(step, "with", {})
	not inputs.settings
	not inputs.allowed_non_write_users
	not inputs.allowed_bots
	args := object.get(inputs, "claude_args", "")
	not contains(args, "gh api")
	not regex.match(`"Bash"|Bash\(\*|Bash\(gh`, args)
}

review_step(step) if {
	object.get(step, "uses", null) == null
	step.run in review_setup
	{key | some key, _ in step} - {"name", "run"} == set()
}

job_environment(job) := job.environment if is_string(job.environment)

job_environment(job) := job.environment.name if is_object(job.environment)

review_job(job) if {
	job_environment(job) == "ai-gates"
	# No job-level override can change how its steps run (live review finding, 2026-10-22).
	not job.env
	not job.defaults
	not job.container
	not job.services
	steps := object.get(job, "steps", [])
	count(steps) > 0
	every step in steps {
		review_step(step)
	}
}

allowed_write(job, "pull-requests") if review_job(job)

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

# A reusable workflow called by a job is code too: pin it like an action. A local path is allowed.
deny contains msg if {
	some job_id, job in jobs
	uses := job.uses
	not startswith(uses, "./")
	not regex.match(`^[^@\s]+@[0-9a-f]{40}$`, uses)
	msg := sprintf("job %s: '%s' is not pinned to a full commit SHA", [job_id, uses])
}

# Expressions are expanded into the script before the shell sees it. Only values the change cannot
# choose may appear in run: or a script; everything else goes through env: and "$VAR".
safe_expression := `^(secrets\.[a-z0-9_]+|matrix\.[a-z0-9_.-]+|runner\.[a-z_]+|github\.(sha|run_id|run_number|run_attempt|repository|workspace|event_name|job|action))$`

input_file := data.aidlc.input_file if {
	is_string(data.aidlc.input_file)
} else := "<file>"

script_texts contains text if {
	some job in jobs
	some step in object.get(job, "steps", [])
	text := step.run
	is_string(text)
}

script_texts contains text if {
	some job in jobs
	some step in object.get(job, "steps", [])
	text := step.with.script
	is_string(text)
}

deny contains msg if {
	some text in script_texts
	some match in regex.find_n(`(?s)\$\{\{(.*?)\}\}`, text, -1)
	expr := trim_space(trim_suffix(trim_prefix(match, "${{"), "}}"))
	not regex.match(safe_expression, lower(expr))
	msg := sprintf("workflow %s: expression '${{ %s }}' in run/script; pass it through env: and use \"$VAR\"", [input_file, expr])
}
