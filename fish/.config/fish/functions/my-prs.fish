function my-prs --description "List open PRs awaiting or completed review"
    argparse 'a/all' -- $argv
    or return 2

    set -l user (gh api user --jq '.login' 2>/dev/null)
    test -z "$user"; and set user wihli

    set -l review_filter --review-requested=$user
    if set -q _flag_all
        set review_filter review-requested:$user OR reviewed-by:$user
    end

    set -l lines (gh search prs $review_filter --state=open --limit 1000 \
        --json number,title,repository,url,createdAt,isDraft \
        --template '{{range .}}{{timeago .createdAt}}{{"\t"}}{{.repository.nameWithOwner}}{{"\t"}}{{.number}}{{"\t"}}{{if .isDraft}}draft{{else}}ready{{end}}{{"\t"}}{{.url}}{{"\t"}}{{.title}}{{"\n"}}{{end}}')
    or return

    if test (count $lines) -eq 0
        if set -q _flag_all
            echo "No open PRs found"
        else
            echo "No PRs awaiting review"
        end
        return
    end

    for line in $lines
        test -z "$line"; and continue
        set -l fields (string split \t $line)
        set -l age $fields[1]
        set -l repo $fields[2]
        set -l num $fields[3]
        set -l state $fields[4]
        set -l url $fields[5]
        set -l title $fields[6]

        if set -q _flag_all
            echo "$age [$state] $url $title"
            continue
        end

        set -l direct (gh api "repos/$repo/pulls/$num/requested_reviewers" \
            --jq "[.users[] | select(.login == \"$user\")] | length" 2>/dev/null)
        set -l who team
        if test -n "$direct" -a "$direct" != "0"
            set who me
        end

        echo "$age [$who] [$state] $url $title"
    end
end
