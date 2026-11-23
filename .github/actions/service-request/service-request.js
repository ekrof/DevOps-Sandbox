// Shared logic for MLOps service request issues.
// Run by the service-request composite action via actions/github-script.
'use strict';

const NO_RESPONSE = '_No response_';

const WORKSPACES_REPO = { owner: 'AkerBP', repo: 'dig-mlops-workspaces' };

// Labels the triage workflow creates on demand: name -> [color, description].
const LABELS = {
  'service-request': ['0e8a16', 'Request to the MLOps team'],
  'request:workspace': ['c5def5', 'New private workspace'],
  'request:access': ['c5def5', 'Workspace, GitHub Actions or workload access'],
  'request:compute-quota-network': ['c5def5', 'Compute, quota or network change'],
  'request:other': ['c5def5', 'Other request or question'],
  'request:add-model': ['c5def5', 'Add a model or version to the catalog'],
  'request:catalog-access': ['c5def5', 'Internal model catalog access'],
  'request:catalog-endpoint': ['c5def5', 'Online endpoint for a catalog model'],
  'env:dev': ['fbca04', 'Development environment'],
  'env:test': ['fbca04', 'Test environment'],
  'env:prod': ['d93f0b', 'Production environment'],
  'scope:catalog': ['bfdadc', 'Internal model catalog (mlw-datasciencews)'],
  'scope:private': ['bfdadc', 'Private use case workspace'],
  'needs-info': ['e99695', 'Waiting for the requester'],
};

const ADMIN_EMAIL = /^admin\.[a-z0-9.-]+@akerbp\.com$/i;
const REPO = /^(?:https:\/\/github\.com\/)?([\w.-]+)\/([\w.-]+?)(?:\.git)?\/?$/;

// User input shown inside inline code in bot comments.
const code = (v) => '`' + String(v).replace(/`/g, "'").replace(/\n/g, ' ') + '`';

// Issue forms render each field as "### Label\n\nvalue".
function parseForm(body) {
  const fields = {};
  const parts = (body || '').split(/^### /m).slice(1);
  for (const part of parts) {
    const nl = part.indexOf('\n');
    const label = (nl === -1 ? part : part.slice(0, nl)).trim();
    const value = (nl === -1 ? '' : part.slice(nl + 1)).trim();
    fields[label] = value === NO_RESPONSE ? '' : value;
  }
  return fields;
}

function parseRepo(value) {
  const m = (value || '').trim().match(REPO);
  return m ? { owner: m[1], repo: m[2] } : null;
}

function dynamicLabels(fields) {
  const labels = [];
  const env = (fields['Environment'] || '').toLowerCase();
  if (['dev', 'test', 'prod'].includes(env)) labels.push(`env:${env}`);
  const ws = (fields['Workspace'] || '').toLowerCase();
  if (ws.includes('datasciencews')) labels.push('scope:catalog');
  else if (ws) labels.push('scope:private');
  return labels;
}

// Field checks that need no API calls. Returns a list of problems.
function validateFields(fields) {
  const errors = [];
  const user = fields['User'];
  if (user !== undefined && user && !ADMIN_EMAIL.test(user)) {
    errors.push(`**User** must be an admin account, e.g. \`admin.john.doe@akerbp.com\` (got ${code(user)}).`);
  }
  const repo = fields['Repository'];
  if (repo !== undefined && repo && !parseRepo(repo)) {
    errors.push(`**Repository** must be \`owner/name\` or a GitHub link (got ${code(repo)}).`);
  }
  // Access Request form: one form, fields required per access type.
  const type = fields['Access type'] || '';
  const missing = (f) => !fields[f];
  if (type.startsWith('Workspace access') && missing('User')) errors.push('**User** is required for workspace access.');
  if (type.startsWith('GitHub Actions')) {
    if (missing('Repository')) errors.push('**Repository** is required for GitHub Actions access.');
    if (fields['Change'] !== 'Remove' && !checkedOptions(fields['Roles']).length) errors.push('**Roles**: tick at least one for GitHub Actions access.');
  }
  if (type.startsWith('Workload') && missing('Details')) errors.push('**Details** is required for workload access.');
  return errors;
}

async function exists(fn) {
  try {
    await fn();
    return true;
  } catch (e) {
    if (e.status === 404) return false;
    throw e;
  }
}

// Workspace check against dig-mlops-workspaces. `reader` may be null when no
// token can read that repository; the check is then skipped.
async function validateRemote(reader, fields) {
  const errors = [];
  const ws = fields['Workspace'];
  if (ws && !/^[a-z0-9-]+$/.test(ws)) {
    errors.push(`**Workspace** must be a workspace folder name, e.g. \`dig-aml-anomdet-sc\` (got ${code(ws)}).`);
  } else if (ws && reader && !(await exists(() => reader.rest.repos.getContent({ ...WORKSPACES_REPO, path: `workspaces/${ws}` })))) {
    errors.push(`**Workspace** ${code(ws)} does not exist in [dig-mlops-workspaces/workspaces](https://github.com/AkerBP/dig-mlops-workspaces/tree/main/workspaces).`);
  }
  return errors;
}

// Checkbox fields render as "- [X] option" lines.
function checkedOptions(value) {
  return (value || '')
    .split('\n')
    .map((l) => l.match(/^- \[[xX]\] (.+)$/))
    .filter(Boolean)
    .map((m) => m[1].trim());
}

const MARKER = '<!-- mlops-service-request-triage -->';
const DOCS = 'https://github.com/AkerBP/dig-mlops-workspaces/blob/main/docs/roadmap/platform-service-requests.md';

// Label, validate and acknowledge the issue in the triggering event.
async function triage({ github, context, reader }) {
  const { owner, repo } = context.repo;
  const issue = context.payload.issue;
  const issue_number = issue.number;

  for (const [name, [color, description]] of Object.entries(LABELS)) {
    try { await github.rest.issues.createLabel({ owner, repo, name, color, description }); }
    catch (e) { if (e.status !== 422) throw e; }
  }

  const fields = parseForm(issue.body);
  const labels = dynamicLabels(fields);
  for (const { name } of issue.labels) {
    if ((name.startsWith('env:') || name.startsWith('scope:')) && !labels.includes(name)) {
      await github.rest.issues.removeLabel({ owner, repo, issue_number, name });
    }
  }
  if (labels.length) await github.rest.issues.addLabels({ owner, repo, issue_number, labels });

  const errors = [...validateFields(fields), ...(await validateRemote(reader, fields))];
  if (errors.length) {
    await github.rest.issues.addLabels({ owner, repo, issue_number, labels: ['needs-info'] });
  } else if (issue.labels.some((l) => l.name === 'needs-info')) {
    await github.rest.issues.removeLabel({ owner, repo, issue_number, name: 'needs-info' });
  }

  const body = errors.length
    ? [MARKER, '### ⚠️ More information needed', '', ...errors.map((e) => `- ${e}`), '',
       'Edit the issue description to fix these; this check runs again on every edit.',
       `Requests without a reply are closed after 14 days. See [service requests](${DOCS}).`].join('\n')
    : [MARKER, '### ✅ Request received', '',
       'The MLOps team reviews new requests and replies here.',
       '- `needs-info` — we are waiting for you.',
       '', `See [service requests](${DOCS}).`].join('\n');

  const comments = await github.paginate(github.rest.issues.listComments, { owner, repo, issue_number });
  const mine = comments.find((c) => c.body && c.body.startsWith(MARKER));
  if (mine) await github.rest.issues.updateComment({ owner, repo, comment_id: mine.id, body });
  else await github.rest.issues.createComment({ owner, repo, issue_number, body });
}

module.exports = {
  LABELS,
  WORKSPACES_REPO,
  parseForm,
  parseRepo,
  dynamicLabels,
  validateFields,
  validateRemote,
  triage,
};
