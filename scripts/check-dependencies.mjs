import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
if (!process.env.npm_execpath) throw new Error('Run through npm run audit:dependencies.');
let raw;
try {
  raw = execFileSync(process.execPath, [process.env.npm_execpath, 'audit', '--json'], {encoding:'utf8',timeout:120000});
} catch (error) {
  if (!error.stdout) throw new Error('npm audit failed without a report.');
  raw = String(error.stdout);
}
const report = JSON.parse(raw);
if (report.error || !report.metadata?.vulnerabilities) throw new Error('npm audit did not produce a complete vulnerability report.');
const counts = report.metadata.vulnerabilities;
const lockHash = createHash('sha256').update(execFileSync('git',['show','HEAD:package-lock.json'])).digest('hex');
const lockCommit = execFileSync('git',['log','-1','--format=%H','--','package-lock.json'],{encoding:'utf8'}).trim();
console.log(JSON.stringify({checkedAt:new Date().toISOString(),lockCommit,lockSha256:lockHash,vulnerabilities:counts},null,2));
if (counts.total !== 0) process.exitCode=1;