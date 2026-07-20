# Contributing to Koan

## Commit messages

Koan follows [Conventional Commits](https://www.conventionalcommits.org/). Every
commit message must be structured as:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

This is enforced on pull requests by the `commitlint` workflow.

### Types

| Type       | Purpose                                              | Release impact |
|------------|-------------------------------------------------------|-----------------|
| `feat`     | A new feature                                          | minor           |
| `fix`      | A bug fix                                              | patch           |
| `docs`     | Documentation only changes                             | none            |
| `style`    | Formatting, whitespace, etc. (no code meaning change)  | none            |
| `refactor` | Code change that neither fixes a bug nor adds a feature| none            |
| `perf`     | A code change that improves performance                | patch           |
| `test`     | Adding or correcting tests                             | none            |
| `build`    | Changes to the build system or dependencies            | none            |
| `ci`       | Changes to CI configuration/scripts                    | none            |
| `chore`    | Other changes that don't modify src or test files      | none            |

### Breaking changes

Append `!` after the type/scope, or add a `BREAKING CHANGE:` footer, to trigger a
major version bump:

```
feat!: drop support for Python 3.8

BREAKING CHANGE: Koan now requires Python 3.9 or newer.
```

### Releases

Merges to `main` are released automatically by
[semantic-release](https://github.com/semantic-release/semantic-release) based on
these commit messages — the version, git tag, GitHub release, and `CHANGELOG.md`
entry are all generated from them, so there is no manual version bump step.
