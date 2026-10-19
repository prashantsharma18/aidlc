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
	d := workflows.deny with input as doc
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
