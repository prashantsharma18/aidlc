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
