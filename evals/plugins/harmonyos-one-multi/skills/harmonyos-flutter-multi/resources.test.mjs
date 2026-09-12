import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {test} from 'node:test';
import {resourceLinks} from '../../lib/resource-links.mjs';
const root=path.resolve(import.meta.dirname,'../../../../../plugins/harmonyos-one-multi/skills/harmonyos-flutter-multi');
test('Flutter independent package entry and every resource link resolve',()=>{
 assert.match(fs.readFileSync(path.join(root,'SKILL.md'),'utf8'),/^name: harmonyos-flutter-multi$/m);
 assert.deepEqual(resourceLinks(root),[]);
});
test('both route examples are concrete Dart resources accessible without sibling plugins',()=>{
 for(const route of ['flutter-native','hadss']){
  const directory=path.join(root,'examples',route);
  const examples=fs.readdirSync(directory).filter(name=>name.endsWith('.dart'));
  assert.ok(examples.length>0);
  for(const example of examples)assert.match(fs.readFileSync(path.join(directory,example),'utf8'),/class |Widget |void /);
 }
});
