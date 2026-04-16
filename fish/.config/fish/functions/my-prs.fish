function my-prs --description "List open PRs requesting my review (direct + team)"
    set -l user (gh api user --jq '.login' 2>/dev/null)
    test -z "$user"; and set user wihli

    set -l lines (gh search prs --review-requested=$user --state=open \
        --json number,title,repository,url,createdAt,isDraft \
        --template '{{range .}}{{timeago .createdAt}}{{"\t"}}{{.repository.nameWithOwner}}{{"\t"}}{{.number}}{{"\t"}}{{if .isDraft}}draft{{else}}ready{{end}}{{"\t"}}{{.url}}{{"\t"}}{{.title}}{{"\n"}}{{end}}')

    if test (count $lines) -eq 0
        echo "No PRs awaiting review"
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

        set -l direct (gh api "repos/$repo/pulls/$num/requested_reviewers" \
            --jq "[.users[] | select(.login == \"$user\")] | length" 2>/dev/null)

        set -l who team
        if test -n "$direct" -a "$direct" != "0"
            set who me
        end

        echo "$age [$who] [$state] $url $title"
    end
end
