### AI PowerShell Development Standards

---

### Core Execution Directives

- Treat all LLM generated scripts, cmdlets, and object pipelines as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every script generation task.
- Append a Zero-Trust directive demanding mandatory web searches for current PowerShell module documentation.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every cmdlet parameter and error handling structure provided.
- Mandate direct, working links to the official documentation used to ground the code.

---

### Strict Mode and Error Handling

- Alter the default error behavior to stop execution on the first error rather than silently continuing. [Confidence: 100%]
- Require the agent to set the global error action preference at the beginning of every script:

```powershell
$ErrorActionPreference = 'Stop'
```

- Enforce termination for native command failures like git or robocopy in modern PowerShell versions 7.3 and newer. [Confidence: 100%]
  - Link: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables
  - Quote: "of"
- Require the agent to declare this preference variable:

```powershell
$PSNativeCommandUseErrorActionPreference = $true
```

---

### Defensive Scripting Practices

- Mandate the use of try, catch, and finally blocks for all operations that interact with the filesystem, network, or external APIs to gracefully handle terminating errors. [Confidence: 100%]
- Avoid implicit data type conversions. Explicitly cast variables (e.g., [int], [string]) in PowerShell to prevent runtime type mismatch errors. [Confidence: 100%]