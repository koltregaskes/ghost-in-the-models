// Called only by actions/github-script with its read-only GitHub client.
// The manifest is a claim; GitHub merge/review/content metadata is the evidence.
const fs = require('node:fs');
const cp = require('node:child_process');
const crypto = require('node:crypto');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const BASELINE = 'a478d8c79dfe335b27e1faed3fe68166989640e5';
module.exports = async ({github, context, mode, output}) => {
  const repo = context.repo;
  const owner = repo.owner;
  if (owner !== 'koltregaskes') throw Error('Unexpected repository owner');
  const receipts = {};
  const paths = mode === 'queue'
    ? fs.readdirSync('publish-queue').filter(n => n.endsWith('.html')).map(n => `publish-queue/${n}`)
    : cp.execFileSync('git', ['diff', '--name-only', BASELINE, 'HEAD', '--', 'posts/'], {encoding:'utf8'}).trim().split('\n').filter(p => p && fs.existsSync(p));
  for (const article of paths) {
    const manifest = `approvals/${article.split('/').pop().replace(/\.html$/, '.json')}`;
    const bytes = fs.readFileSync(article);
    const raw = fs.readFileSync(manifest);
    const record = JSON.parse(raw);
    if (record.article !== `publish-queue/${article.split('/').pop()}` || record.approver !== owner || record.sha256 !== hash(bytes)) {
      throw Error(`Approval mismatch: ${article}`);
    }
    const commit = cp.execFileSync('git', ['log', '-1', '--format=%H', '--', manifest], {encoding:'utf8'}).trim();
    const prs = await github.paginate(github.rest.repos.listPullRequestsAssociatedWithCommit, {...repo, commit_sha:commit, per_page:100});
    let verified = false;
    for (const candidate of prs) {
      const {data:pr} = await github.rest.pulls.get({...repo, pull_number:candidate.number});
      if (!pr.merged || pr.base.ref !== 'main' || pr.base.repo.full_name !== `${owner}/${repo.repo}` || pr.merged_by?.login !== owner) continue;
      const reviews = await github.paginate(github.rest.pulls.listReviews, {...repo, pull_number:pr.number, per_page:100});
      // Use each reviewer's last state, so a later dismissal/request supersedes approval.
      const latest = new Map();
      for (const review of reviews) if (review.state !== 'COMMENTED') latest.set(review.user.login, review);
      if (![...latest.values()].some(r => r.state === 'APPROVED' && r.commit_id === pr.head.sha && r.user.type === 'User')) continue;
      const files = await github.paginate(github.rest.pulls.listFiles, {...repo, pull_number:pr.number, per_page:100});
      if (!files.some(f => f.filename === manifest) || !files.some(f => f.filename === record.article)) continue;
      async function mergedBytes(path) {
        const {data} = await github.rest.repos.getContent({...repo, path, ref:pr.merge_commit_sha});
        if (data.encoding !== 'base64' || typeof data.content !== 'string') throw Error(`No verifiable content: ${path}`);
        return Buffer.from(data.content, 'base64');
      }
      if (!raw.equals(await mergedBytes(manifest)) || !bytes.equals(await mergedBytes(record.article))) continue;
      verified = true;
      console.log(`Verified ${article}: reviewed PR #${pr.number}, merged by ${owner}`);
      break;
    }
    if (!verified) throw Error(`No reviewed PR merged by ${owner} for ${article}`);
    receipts[manifest] = hash(raw);
  }
  fs.writeFileSync(output, JSON.stringify(receipts) + '\n');
  console.log(`Verified ${paths.length} ${mode} article approval(s). Legacy unchanged articles are not retrospectively approved.`);
};
