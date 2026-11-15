const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const crypto = require('node:crypto');
const source = fs.readFileSync(__dirname + '/verify-approvals.cjs', 'utf8');
const hash = x => crypto.createHash('sha256').update(x).digest('hex');
async function run(change = {}) {
  const article = Buffer.from('<p>Reviewed</p>\n');
  const raw = Buffer.from(JSON.stringify({article:'publish-queue/test.html', approver:'koltregaskes', sha256:hash(article)}));
  const paths = {'publish-queue/test.html':article, 'approvals/test.json':raw};
  const pr = {number:7, merged:true, base:{ref:'main',repo:{full_name:'koltregaskes/ghost-in-the-models'}}, merged_by:{login:'koltregaskes'}, head:{sha:'head'}, merge_commit_sha:'merge', ...change.pr};
  const rest = {repos:{listPullRequestsAssociatedWithCommit:'prs',getContent:async ({path}) => ({data:{encoding:'base64', content:Buffer.from(change.content || paths[path]).toString('base64')}})}, pulls:{get:async()=>({data:pr}),listReviews:'reviews',listFiles:'files'}};
  const github = {rest,paginate:async name => ({prs:[{number:7}], reviews: change.reviews || [{state:'APPROVED',commit_id:'head',user:{login:'reviewer',type:'User'}}],files:[{filename:'approvals/test.json'},{filename:'publish-queue/test.html'}]})[name]};
  let receipt;
  const fakeFs = {readdirSync:()=>['test.html'],readFileSync:p=>paths[p], writeFileSync:(_,data)=>{receipt=JSON.parse(data);}};
  const sandbox = {module:{exports:{}},Buffer,console:{log(){}},require:n=> n==='node:fs' ? fakeFs : n==='node:child_process' ? {execFileSync:()=> 'commit\n'} : require(n)};
  vm.runInNewContext(source,sandbox);
  await sandbox.module.exports({github,context:{repo:{owner:'koltregaskes',repo:'ghost-in-the-models'}},mode:'queue',output:'/runner/receipt'});
  return receipt;
}
test('valid reviewed owner merge yields bound receipt',async()=>assert.equal((await run())['approvals/test.json'].length,64));
test('non-owner merge rejected',async()=>assert.rejects(run({pr:{merged_by:{login:'agent'}}})));
test('unmerged PR rejected',async()=>assert.rejects(run({pr:{merged:false}})));
test('approval of older head rejected',async()=>assert.rejects(run({reviews:[{state:'APPROVED',commit_id:'old',user:{login:'reviewer',type:'User'}}]})));
test('bot review rejected',async()=>assert.rejects(run({reviews:[{state:'APPROVED',commit_id:'head',user:{login:'bot',type:'Bot'}}]})));
test('dismissed review rejected',async()=>assert.rejects(run({reviews:[{state:'APPROVED',commit_id:'head',user:{login:'r',type:'User'}},{state:'DISMISSED',commit_id:'head',user:{login:'r',type:'User'}}]})));
test('merged content mismatch rejected',async()=>assert.rejects(run({content:'forged'})));
