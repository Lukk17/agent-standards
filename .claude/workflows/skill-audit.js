export const meta = {
  name: 'skill-audit',
  description: 'Read-only audit of every skill in .agents/skills, each finding checked by a second agent',
  whenToUse: 'Periodic quality check of the skills in .agents/skills',
  phases: [
    { title: 'List', detail: 'find every skill folder' },
    { title: 'Find', detail: 'one reader per batch of skills' },
    { title: 'Verify', detail: 'one skeptic per batch tries to refute each finding' },
  ],
}

const RULES = `The current working directory is the repository. Skills live in .agents/skills/<name>/SKILL.md with optional references/*.md. This is a READ-ONLY task: never edit, create or delete any file, and never run a script. Read files and use grep and glob only.
What a good skill looks like: front matter carries name (equal to the folder name) and description, and at most license, compatibility and metadata besides; the description is in trigger form: what the skill covers, then the phrases a user would actually say, then what it is not for and which skill owns that instead; the manifest is short and depth sits in references/; every file a SKILL.md links to exists.`

const SKILL_LIST = {
  type: 'object',
  properties: {
    skills: { type: 'array', items: { type: 'string' } },
  },
  required: ['skills'],
}

let skills = Array.isArray(args) && args.length ? args : []
if (!skills.length) {
  const listed = await agent(`${RULES}

List the folder names directly under .agents/skills that contain a SKILL.md file. Return the bare folder names, not paths, and do not descend into references/ folders.`, { label: 'list', phase: 'List', schema: SKILL_LIST })
  skills = (listed && listed.skills) || []
}
if (!skills.length) throw new Error('No skill folders found under .agents/skills')

const BATCHES = 5
const size = Math.ceil(skills.length / Math.min(BATCHES, skills.length))
const batches = []
for (let i = 0; i < skills.length; i += size) batches.push(skills.slice(i, i + size))

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          skill: { type: 'string' },
          file: { type: 'string', description: 'repo-relative path' },
          line: { type: 'integer' },
          category: { type: 'string', enum: ['trigger', 'front-matter', 'stale-fact', 'contradiction', 'broken-reference', 'overlap', 'unclear-instruction'] },
          problem: { type: 'string', description: 'one plain sentence' },
          evidence: { type: 'string', description: 'short quote from the file or the command output that proves it' },
          fix: { type: 'string', description: 'the concrete change proposed' },
        },
        required: ['skill', 'file', 'category', 'problem', 'evidence', 'fix'],
      },
    },
  },
  required: ['findings'],
}

const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          index: { type: 'integer' },
          real: { type: 'boolean' },
          reason: { type: 'string' },
        },
        required: ['index', 'real', 'reason'],
      },
    },
  },
  required: ['verdicts'],
}

const results = await pipeline(
  batches,
  (batch, _item, i) => agent(`${RULES}

Audit these skills: ${batch.join(', ')}.
For each one read SKILL.md and every file under its references/ folder. Report only real defects of these kinds:
- trigger: the description would fail to make an agent load the skill for a request it clearly owns, or would wrongly pull it in for another skill's work, or lacks the "not for, use X instead" part.
- front-matter: name does not match the folder, a key outside the allowed set, description over 1024 characters, or unquoted description containing a colon.
- stale-fact: a version, command, flag, tool name, URL or product fact that is wrong today. Only report it if you can show why it is wrong (for example a contradiction with another file in this repository, or a tool name that no agent here uses). Do not guess from memory.
- contradiction: the skill says the opposite of another skill, of AGENTS.md, or of itself.
- broken-reference: a linked or named file inside the repository that does not exist.
- overlap: two skills own the same job with no rule for which wins.
- unclear-instruction: an instruction an agent could not follow as written.
Skip style nits, wording taste and anything you cannot prove with a quote. An empty list is a good answer.`, { label: `find:batch-${i + 1}`, phase: 'Find', schema: FINDINGS }),
  (found, batch, i) => {
    if (!found) return null
    const list = found.findings || []
    if (!list.length) return { batch, confirmed: [], rejected: [] }
    return agent(`${RULES}

Another agent reported the defects below in the skills ${batch.join(', ')}. Your job is to try to REFUTE each one. Open the file, check the quote, check whether the problem is real and whether the proposed fix is correct. If it is a style preference, not provable, or already handled elsewhere, mark real=false. When unsure, mark real=false.

${list.map((f, n) => `[${n}] ${f.skill} | ${f.file}${f.line ? ':' + f.line : ''} | ${f.category}
problem: ${f.problem}
evidence: ${f.evidence}
fix: ${f.fix}`).join('\n\n')}`, { label: `verify:batch-${i + 1}`, phase: 'Verify', schema: VERDICTS })
      .then(v => {
        if (!v) return { batch, failed: true, findings: list }
        const verdicts = v.verdicts || []
        const byIndex = new Map(verdicts.map(x => [x.index, x]))
        const confirmed = [], rejected = []
        list.forEach((f, n) => {
          const verdict = byIndex.get(n)
          if (verdict && verdict.real) confirmed.push({ ...f, check: verdict.reason })
          else rejected.push({ ...f, check: verdict ? verdict.reason : 'no verdict returned' })
        })
        return { batch, confirmed, rejected }
      })
  },
)

const returned = results.filter(Boolean)
const failed = returned.filter(r => r.failed)
const done = returned.filter(r => !r.failed)
const missing = batches.length - returned.length
if (missing) log(`${missing} batch(es) returned nothing and were not audited`)
if (failed.length) log(`${failed.length} batch(es) returned findings that no checker verified: ${failed.map(r => r.batch.join(', ')).join(' | ')}`)
return {
  skillsAudited: done.flatMap(r => r.batch).length,
  confirmed: done.flatMap(r => r.confirmed),
  rejected: done.flatMap(r => r.rejected),
  unverified: failed.flatMap(r => r.findings),
}
