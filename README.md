# Connectors

OpenAPI descriptions that [Holon](https://holonlabs.ai/docs/) turns into apps for
services without an MCP server of their own.

In the Holon console, choose **Add app** and paste this URL to add Outlook Mail,
Outlook Calendar, Teams, OneDrive or Excel:

```text
https://holon-sh.github.io/connectors/v1/microsoft.json
```

## How it is built

Nothing generated is checked in. `./build` fetches each vendor's own description
at a pinned commit, cuts or corrects it, and writes the result under `site/v1/`.
A merge to `main` publishes `site/` to GitHub Pages.

- `microsoft/apps.yaml` lists the Microsoft Graph operations each app keeps, with
  the name and summary its tool gets. `microsoft/build.rb` cuts them out of
  Microsoft's description.
- `intercom/build.py` corrects Intercom's description where its API answers
  differently.

`./build` needs Ruby 3.1 or newer, Python 3 and curl.

## Versions

Files under `v1/` keep their names, and a tool there keeps its name and meaning.
A change that breaks either goes under `v2/`.

## Licenses

This repository is MIT licensed. The published descriptions derive from
[Microsoft Graph's](https://github.com/microsoftgraph/msgraph-metadata) and
[Intercom's](https://github.com/intercom/Intercom-OpenAPI) MIT-licensed
documents, whose licenses are in [`licenses/`](licenses).
