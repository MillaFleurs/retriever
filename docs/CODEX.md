# Using Retriever with Codex

Retriever is a Codex plugin bundle. It packages Retriever skills and a local Python runtime; it is not a standalone macOS application or a browser extension. The supported product path for this release is the ChatGPT desktop app on macOS, in **Codex** or **Work mode**. Plugins are not available in Chat mode, the IDE extension, or mobile.
Reference: [OpenAI Plugins documentation](https://learn.chatgpt.com/docs/plugins).

## What You Need

- A macOS machine for this first Retriever release.
- The ChatGPT desktop app with Codex available.
- The separate Chrome plugin installed and enabled only when you want Retriever to inspect live company career sites. It is not needed to begin onboarding, review local reports, or manage archived jobs.

The Chrome plugin runs against the selected Chrome profile. Retriever uses the normal Chrome browser identity and does not set or modify a User-Agent string.
Reference: [OpenAI Chrome extension documentation](https://learn.chatgpt.com/docs/chrome-extension).

## Install from GitHub

From a terminal, add Retriever's GitHub marketplace and install the plugin:

```bash
codex plugin marketplace add MillaFleurs/retriever
codex plugin add retriever@retriever
```

`codex plugin marketplace add` supports GitHub shorthand such as `owner/repo`; `codex plugin add` installs a plugin from a configured marketplace. To inspect the configured source or installed plugin, use:

```bash
codex plugin marketplace list
codex plugin list
```

Reference: [Build plugins: marketplace sources](https://learn.chatgpt.com/docs/build-plugins#add-a-marketplace-from-the-cli), [Codex developer commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli).

## Install from a Local Clone

For development or offline iteration, run these commands from the repository root:

```bash
codex plugin marketplace add .
codex plugin add retriever@retriever
```

The repository marketplace is `.agents/plugins/marketplace.json`; its Retriever entry points to `./plugins/retriever`. For a local marketplace, restart the ChatGPT desktop app after changing the plugin files so it reloads the source.
Reference: [Build plugins: local marketplace setup](https://learn.chatgpt.com/docs/build-plugins#install-a-local-plugin-manually).

## Start Retriever in the Codex App

After installation, start a **new** Codex chat. Bundled skills become available to new chats after a plugin is installed. If Codex shows **Try it now**, select it; otherwise send:

```text
Start my job search
```

Retriever begins with career-coach intake only when there is no valid local profile. It asks for a resume or experience summary, roles, locations, industries, companies, and cadence; it never fills missing search criteria from guesses or prior chat context.

Once onboarding saves and verifies the profile, Retriever reports the active-company count and asks whether to run the first search. Its estimate is roughly three minutes per active company. It does not open Chrome, start a retrieval run, or create a schedule until the user explicitly agrees.

You can then use natural prompts such as:

```text
Check my target companies for new jobs.
Show my full Retriever job report.
Open my Retriever job dashboard.
Uninstall Retriever and delete its schedules.
```

Reference: [OpenAI Plugins documentation](https://learn.chatgpt.com/docs/plugins), [Retriever onboarding instructions](../plugins/retriever/skills/retriever-onboard/SKILL.md).

## Updates

Refresh the configured GitHub marketplace, inspect the installed version, then start a new Codex chat before testing updated skills:

```bash
codex plugin marketplace upgrade retriever
codex plugin list
```

For a local clone, update the files that the marketplace entry references, restart the ChatGPT desktop app, and use a new chat.
Reference: [Build plugins: marketplace sources](https://learn.chatgpt.com/docs/build-plugins#add-a-marketplace-from-the-cli), [OpenAI Plugins documentation](https://learn.chatgpt.com/docs/plugins).

## Scheduled Retrieval

Retriever creates recurring checks through Codex **Scheduled** only after the user chooses a cadence and explicitly authorizes retrieval. Installation and onboarding never create a background job on their own. Scheduled checks must rerun Retriever's local preflight before opening Chrome; if the profile or database is incomplete, they skip the scan and direct the user back to onboarding.

Use the Retriever conversation to request a schedule, or open the Scheduled create flow in the desktop app. Local job checks depend on Codex, Chrome, and the user's machine/session being available at run time.
Reference: [OpenAI Scheduled tasks documentation](https://learn.chatgpt.com/docs/automations), [Retriever automation guide](AUTOMATION.md).

## Uninstall and Local Data

Before using the Plugins UI to uninstall, tell Retriever:

```text
Uninstall Retriever and delete its schedules.
```

Retriever shows and removes only its own schedules after confirmation. Uninstalling the plugin does not delete `~/.retriever`; use Retriever's explicit reset or deletion workflow when you want to remove local profile data, job findings, or reports.
Reference: [OpenAI Plugins documentation](https://learn.chatgpt.com/docs/plugins), [Retriever security and data guide](SECURITY.md).

## Developer Runtime

Normal users do not need to run `retriever.py` directly. The commands in the root [README](../README.md#runtime-commands-for-development) are for local development, deterministic demos, and tests. Use a temporary `--state-dir` for demos so test data never mixes with a real `~/.retriever` profile.
