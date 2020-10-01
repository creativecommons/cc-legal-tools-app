import git


def setup_local_branch(repo: git.Repo, branch_name: str, parent_branch_name: str):
    """
    Ensure we have a local branch named 'branch_name'.
    Pull from upstream ('origin'), or create as a branch from parent_branch_name.
    If there's an upstream one, pull from it to make sure we're up to date.
    Check it out.
    """
    # is there already a branch?
    origin = repo.remotes.origin
    origin.fetch()
    if not hasattr(repo.branches, branch_name):
        # Not locally, maybe upstream
        if hasattr(origin.refs, branch_name):
            repo.create_head(branch_name, f"origin/{branch_name}")
        else:
            # Nope, need to create from scratch
            print("create from scratch")
            parent_branch = getattr(origin.refs, parent_branch_name)
            repo.create_head(branch_name, parent_branch)
    else:
        print("local already exists")
    branch = getattr(repo.heads, branch_name)
    branch.checkout()
    # Make sure local branch is up to date if there's an upstream branch
    if hasattr(origin.refs, branch_name):
        origin.pull(f"{branch_name}:{branch_name}")


def commit_and_push_changes(repo: git.Repo, commit_msg: str):
    """Commit new translation changes to current branch, and push upstream"""
    index = repo.index
    index.commit(commit_msg)
    current_branch = repo.head.reference
    branch_name = current_branch.name
    results = repo.remotes.origin.push(f"{branch_name}:{branch_name}")
    if len(results) == 0:
        raise Exception("PUSH FAILED COMPLETELY - add more info to this message")
    for result in results:
        if git.PushInfo.ERROR & result.flags:
            raise Exception(f"PUSH FAILED {result.summary}")
