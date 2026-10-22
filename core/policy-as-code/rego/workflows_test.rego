package aidlc.workflows_test

import data.aidlc.workflows

checkout := "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"

good := {
	"on": {"pull_request": {"branches": ["main"]}},
	"permissions": {"contents": "read"},
	"jobs": {"check": {
		"runs-on": "ubuntu-24.04",
		"steps": [
			{"uses": checkout},
			{"uses": "./.github/actions/local"},
			{"run": "aidlc/bin/aidlc ci --branch \"$HEAD_REF\"", "env": {"HEAD_REF": "${{ github.head_ref }}"}},
		],
	}},
}

denials(doc) := d if {
	d := workflows.deny with input as doc with data.aidlc.input_file as ".github/workflows/v.yml"
}

test_good_workflow_passes if {
	count(denials(good)) == 0
}

test_unpinned_action_is_denied if {
	bad := json.patch(good, [{"op": "replace", "path": "/jobs/check/steps/0/uses", "value": "actions/checkout@v7"}])
	"job check: 'actions/checkout@v7' is not pinned to a full commit SHA" in denials(bad)
}

test_pull_request_target_is_denied if {
	bad := object.union(good, {"on": {"pull_request_target": {}}})
	some msg in denials(bad)
	startswith(msg, "workflows must not run on pull_request_target")
}

test_pull_request_target_under_yaml11_true_key_is_denied if {
	bad := object.union(object.remove(good, ["on"]), {"true": ["pull_request_target"]})
	some msg in denials(bad)
	startswith(msg, "workflows must not run on pull_request_target")
}

test_missing_permissions_is_denied if {
	"set top-level permissions explicitly (contents: read)" in denials(object.remove(good, ["permissions"]))
}

test_top_level_write_is_denied if {
	bad := object.union(good, {"permissions": {"contents": "write"}})
	"top-level permission contents: write; grant write per job, never workflow-wide" in denials(bad)
}

test_job_write_is_denied if {
	bad := json.patch(good, [{"op": "add", "path": "/jobs/check/permissions", "value": {"pull-requests": "write"}}])
	"job check grants pull-requests: write; the verify workflow needs read only" in denials(bad)
}

test_untrusted_text_in_run_is_denied if {
	every text in ["echo ${{ github.head_ref }}", "echo ${{ github.event.pull_request.head.label }}",
	               "echo ${{ github.event.comment.body }}", "echo ${{github.event.issue.title}}"] {
		bad := json.patch(good, [{"op": "add", "path": "/jobs/check/steps/-", "value": {"run": text}}])
		"job check: untrusted pull request text is expanded inside run:; pass it through env" in denials(bad)
	}
}

add_step(run_text) := json.patch(good, [{"op": "add", "path": "/jobs/check/steps/-", "value": {"run": run_text}}])

test_unsafe_expressions_in_run_are_denied if {
	every text in [
		"echo ${{ format('{0}', github.head_ref) }}",
		"echo ${{ toJSON(github.event) }}",
		"echo ${{ (github.head_ref) }}",
		"echo ${{ github.event['comment']['body'] }}",
		"echo ${{ inputs.x }}",
		"echo ${{ env.T }}",
		"echo ${{ GITHUB.EVENT.comment.body }}",
		"echo ${{github.ref_name}}",
	] {
		some msg in denials(add_step(text))
		startswith(msg, "workflow .github/workflows/v.yml: expression '${{ ")
		endswith(msg, "}}' in run/script; pass it through env: and use \"$VAR\"")
	}
}

test_expression_message_is_exact if {
	"workflow .github/workflows/v.yml: expression '${{ inputs.x }}' in run/script; pass it through env: and use \"$VAR\"" in denials(add_step("echo ${{ inputs.x }}"))
}

test_expression_in_github_script_is_denied if {
	bad := json.patch(good, [{"op": "add", "path": "/jobs/check/steps/-", "value": {
		"uses": "actions/github-script@3d3c42e5aac5ba805825da76410c181273ba90b1",
		"with": {"script": "core.info(`${{ github.event.issue.title }}`)"},
	}}])
	some msg in denials(bad)
	contains(msg, "expression '${{ github.event.issue.title }}' in run/script")
}

test_allow_listed_expressions_pass if {
	ok := add_step("echo ${{ secrets.TOKEN }} ${{ matrix.os }} ${{ github.sha }} ${{ runner.os }} ${{ github.run_id }}")
	count(denials(ok)) == 0
}

test_workflow_run_is_denied if {
	every on in [{"workflow_run": {"workflows": ["x"]}}, ["push", "workflow_run"], "workflow_run"] {
		bad := object.union(good, {"on": on})
		some msg in denials(bad)
		startswith(msg, "workflows must not run on workflow_run")
	}
}

test_workflow_run_under_yaml11_true_key_is_denied if {
	bad := object.union(object.remove(good, ["on"]), {"true": {"workflow_run": {}}})
	some msg in denials(bad)
	startswith(msg, "workflows must not run on workflow_run")
}

test_unpinned_reusable_workflow_is_denied if {
	bad := json.patch(good, [{"op": "add", "path": "/jobs/reuse", "value": {"uses": "x/y/.github/workflows/w.yml@main"}}])
	"job reuse: 'x/y/.github/workflows/w.yml@main' is not pinned to a full commit SHA" in denials(bad)
}

test_pinned_and_local_reusable_workflows_pass if {
	ok := json.patch(good, [
		{"op": "add", "path": "/jobs/pinned", "value": {"uses": "x/y/.github/workflows/w.yml@3d3c42e5aac5ba805825da76410c181273ba90b1"}},
		{"op": "add", "path": "/jobs/local", "value": {"uses": "./.github/workflows/w.yml"}},
	])
	count(denials(ok)) == 0
}

test_non_object_permissions_are_denied if {
	every value in [null, [], "write-all", "read", ["contents"], 7] {
		bad := json.patch(good, [{"op": "replace", "path": "/permissions", "value": value}])
		"set top-level permissions explicitly (contents: read)" in denials(bad)
	}
}

test_read_all_permissions_pass if {
	count(denials(json.patch(good, [{"op": "replace", "path": "/permissions", "value": "read-all"}]))) == 0
}

review_action := "anthropics/claude-code-action@6fed3ca145920b639991cb756090506e1bcaf515"

review := {
	"on": {"pull_request": {}},
	"permissions": {"contents": "read"},
	"jobs": {"ai-review": {
		"runs-on": "ubuntu-24.04",
		"environment": "ai-gates",
		"permissions": {"contents": "read", "pull-requests": "write"},
		"steps": [
			{"uses": checkout, "with": {"persist-credentials": false}},
			{"uses": review_action, "with": {"prompt": "review"}},
		],
	}},
}

test_review_job_may_comment if {
	count(denials(review)) == 0
}

test_review_job_environment_as_object_may_comment if {
	ok := json.patch(review, [{"op": "replace", "path": "/jobs/ai-review/environment", "value": {"name": "ai-gates"}}])
	count(denials(ok)) == 0
}

test_review_write_outside_ai_gates_is_denied if {
	bad := json.patch(review, [{"op": "replace", "path": "/jobs/ai-review/environment", "value": "production"}])
	"job ai-review grants pull-requests: write; the verify workflow needs read only" in denials(bad)
}

test_review_write_without_environment_is_denied if {
	bad := json.patch(review, [{"op": "remove", "path": "/jobs/ai-review/environment"}])
	"job ai-review grants pull-requests: write; the verify workflow needs read only" in denials(bad)
}

test_review_job_with_a_shell_step_is_denied if {
	bad := json.patch(review, [{"op": "add", "path": "/jobs/ai-review/steps/-", "value": {"run": "gh pr review --approve"}}])
	"job ai-review grants pull-requests: write; the verify workflow needs read only" in denials(bad)
}

test_review_job_with_another_action_is_denied if {
	other := "someone/else@0123456789012345678901234567890123456789"
	bad := json.patch(review, [{"op": "add", "path": "/jobs/ai-review/steps/-", "value": {"uses": other}}])
	"job ai-review grants pull-requests: write; the verify workflow needs read only" in denials(bad)
}

test_review_job_cannot_also_write_contents if {
	bad := json.patch(review, [{"op": "replace", "path": "/jobs/ai-review/permissions/contents", "value": "write"}])
	"job ai-review grants contents: write; the verify workflow needs read only" in denials(bad)
}

test_id_token_write_stays_denied_in_the_review_job if {
	bad := json.patch(review, [{"op": "add", "path": "/jobs/ai-review/permissions/id-token", "value": "write"}])
	"job ai-review grants id-token: write; the verify workflow needs read only" in denials(bad)
}

test_empty_review_job_is_denied if {
	bad := json.patch(review, [{"op": "replace", "path": "/jobs/ai-review/steps", "value": []}])
	"job ai-review grants pull-requests: write; the verify workflow needs read only" in denials(bad)
}

sandbox_setup := [
	{"name": "bubblewrap", "run": "sudo apt-get update -q && sudo apt-get install -y -q bubblewrap"},
	{"name": "userns", "run": "sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0 || true"},
]

test_review_job_may_install_the_sandbox if {
	ok := json.patch(review, [
		{"op": "add", "path": "/jobs/ai-review/steps/1", "value": sandbox_setup[0]},
		{"op": "add", "path": "/jobs/ai-review/steps/2", "value": sandbox_setup[1]},
	])
	count(denials(ok)) == 0
}

test_review_setup_step_with_env_is_denied if {
	step := object.union(sandbox_setup[0], {"env": {"BASH_ENV": "./evil.sh"}})
	bad := json.patch(review, [{"op": "add", "path": "/jobs/ai-review/steps/1", "value": step}])
	"job ai-review grants pull-requests: write; the verify workflow needs read only" in denials(bad)
}

test_review_setup_step_with_another_shell_is_denied if {
	step := object.union(sandbox_setup[0], {"shell": "python {0}"})
	bad := json.patch(review, [{"op": "add", "path": "/jobs/ai-review/steps/1", "value": step}])
	"job ai-review grants pull-requests: write; the verify workflow needs read only" in denials(bad)
}

test_review_setup_command_with_more_is_denied if {
	step := {"run": "sudo apt-get update -q && sudo apt-get install -y -q bubblewrap && curl x"}
	bad := json.patch(review, [{"op": "add", "path": "/jobs/ai-review/steps/1", "value": step}])
	"job ai-review grants pull-requests: write; the verify workflow needs read only" in denials(bad)
}
