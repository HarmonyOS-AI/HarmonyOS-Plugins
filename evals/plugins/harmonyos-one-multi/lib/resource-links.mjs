import fs from 'node:fs';
import path from 'node:path';

export function resourceLinks(root) {
  root=path.resolve(root);
  const broken=[];
  function visit(directory) {
    for (const entry of fs.readdirSync(directory,{withFileTypes:true})) {
      const file=path.join(directory,entry.name);
      if(entry.isSymbolicLink()||['node_modules','__pycache__'].includes(entry.name))continue;
      if(entry.isDirectory()){visit(file);continue;}
      if(!file.endsWith('.md'))continue;
      const source=fs.readFileSync(file,'utf8');
      const targets=[...source.matchAll(/!?\[[^\]\n]*\]\(([^)\n]+)\)/g)].map(m=>m[1]);
      let skillRoot=path.dirname(file);
      while(skillRoot!==path.parse(skillRoot).root&&!fs.existsSync(path.join(skillRoot,'SKILL.md')))skillRoot=path.dirname(skillRoot);
      if(fs.existsSync(path.join(skillRoot,'SKILL.md'))){
        const prose=source.replace(/<!--[^]*?-->/g,'').replace(/!?\[[^\]\n]*\]\([^)\n]+\)/g,'');
        for(const match of prose.matchAll(/`((?:\$OM\/)?(?:references|assets|examples|scripts)\/[A-Za-z0-9_./-]+\.(?:md|py|mjs|dart|ets|html|css|png))`/g)){
          if(!fs.existsSync(path.join(skillRoot,match[1].replace('$OM/',''))))broken.push({file:path.relative(root,file),target:match[1],kind:'literal-resource'});
        }
      }
      for(let target of targets){
        target=target.trim().replace(/^<([^>]+)>.*$/,'$1').replace(/\s+["'].*$/,'');
        if(/^(?:[a-z][a-z\d+.-]*:|#)/i.test(target))continue;
        target=decodeURIComponent(target.split('#')[0]);
        if(target&&!fs.existsSync(path.resolve(path.dirname(file),target)))broken.push({file:path.relative(root,file),target});
      }
    }
  }
  visit(root);return broken;
}
