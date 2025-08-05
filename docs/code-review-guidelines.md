## Code Review Guidelines (Developer-to-Developer)

### Overview

All code changes must go through a structured review process to ensure quality, maintainability, and team alignment. The workflow is:

1. Developer opens a Pull Request (PR)
2. Developer resolves Gemini auto-review suggestions
3. Developer requests a peer review (rotation-based)
4. Peer review must be completed and approved
5. A designated senior reviewer or code owner performs the final review and merge

> [!IMPORTANT] 
> The **PR author is responsible for testing and running the code**. Reviewers do **not** need to run the code locally.

---

## Review Objectives

> Code reviews are not expected to catch every bug or re-architect the code. Focus on clarity, correctness, structure, and alignment with team standards.

### 1. **Correctness**

* Does the code appear to match the purpose described in the PR title/description?
* Are there any obvious logical errors, typos, or copy-paste mistakes?
* Are validations and guards in place?

> Reviewers are not expected to deeply test or trace logic. Just sanity check the flow and flag anything that looks off.

### 2. **Clarity & Style**

* Is the code easy to read and follow?
* Are naming conventions followed (e.g., clear variable/function names)?
* Is the code consistent with our style guides?

### 3. **Structure & Modularity**

* Do files conform to our **project folder structure** (e.g., `models/`, `routers/`, `shared_utils/`, etc.)?
* Are there any **unnecessary files** accidentally committed?
  *(e.g., debug output, `.DS_Store`, `.env`, local cache, logs)*
* Is duplicated logic minimized via reusable functions/utilities?

### 4. **Security & Robustness**

* Is error handling safe and informative?
* Are there obvious potential security risks or exposures?
* Are client and server side logging conforming to our standards?

### 5. **Performance (if applicable)**

* Any clear inefficiencies?
* Any potential scalability issues introduced?

---

## Review Etiquette

### As a Reviewer:

* **Be timely** — Review within a reasonable window (e.g., within 24 hours).
* **Be constructive** — Focus on the code, not the coder.
* Use comment labels:

  * `nit:` for style issues or tiny fixes
  * `suggest:` for improvements, not mandatory
  * `blocking:` for issues that must be resolved
* Leave **inline comments** where applicable for better context.

> **Reviewers should avoid making code changes directly in a PR unless**:
>
> * The change is trivial (e.g., typo, formatting)
> * It has been discussed and agreed upon with the PR author
> * The change is urgent and the PR author is unavailable

In all cases, changes should be explained and ideally paired with a comment.

---

### As a PR Author:

* Ensure the code is **tested and functional** before requesting review.
* **Respond to all reviewer comments**, even if it's just to acknowledge.
* Avoid force-pushing once review has started unless necessary (e.g., to address a critical bug or merge conflict). If done, notify your reviewer.
* After resolving Gemini and peer feedback, **tag the reviewer again** for confirmation.

---

## Final Review & Merge

Once:

* Gemini suggestions are addressed
* A peer reviewer has approved
* All comments are resolved

A **designated senior reviewer** (e.g., **Code Owner**, **Architect**, or **Senior Developer**) will perform the **final review** to:

* Ensure alignment with architectural standards
* Confirm code quality and maintainability
* Validate readiness for integration

They will then proceed to **merge the PR**.

> This role is not fixed to a "tech lead," but should be someone with the responsibility and authority to safeguard overall codebase integrity.
